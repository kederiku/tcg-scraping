"""POST pagination, terminal batch, exports and resume against a local server."""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from test_pokemon_kr import ENERGY, POKEMON, TRAINER

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def catalogue():
    requests = []
    mode = {"value": "normal"}

    class Handler(BaseHTTPRequestHandler):
        def respond(self, body, status=200):
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())

        def do_POST(self):
            fields = parse_qs(
                self.rfile.read(int(self.headers["Content-Length"])).decode(),
                keep_blank_values=True,
            )
            requests.append(("POST", self.path, fields))
            if (
                self.path != "/v2/ajax2_dev2"
                or self.headers.get("X-Requested-With") != "XMLHttpRequest"
                or fields.get("action") != ["search_text_cards"]
                or fields.get("search_params") != ["cardname"]
                or fields.get("search_text") != ["테스트"]
            ):
                self.respond("Wrong AJAX request", 400)
                return
            cursor = int(fields["limit"][0])
            ids = {0: ["KR001", "KR002"], 1: ["KR002", "KR003"]}.get(cursor, [])
            if mode["value"] == "many":
                ids = {0: ["KR001", "KR002"], 1: ["KR003", "KR004", "KR005"]}.get(cursor, [])
            data = {
                "status": mode["value"] != "failed",
                "count": len(ids),
                "limit": cursor + 1,
                "result": {str(i): {"CardNum": card_id} for i, card_id in enumerate(ids, 1)}
                if ids
                else [],
            }
            self.respond("접근불가" if mode["value"] == "bad-json" else json.dumps(data))

        def do_GET(self):
            requests.append(("GET", self.path, {}))
            if self.path == "/robots.txt":
                self.respond("User-agent: *\nAllow: /\n")
            elif urlsplit(self.path).path.startswith("/cards/detail/"):
                if mode["value"] == "blocked":
                    self.respond("Slow down", 429)
                    return
                card_id = self.path.rsplit("/", 1)[1]
                self.respond(
                    {
                        "KR001": POKEMON,
                        "KR002": TRAINER,
                        "KR003": ENERGY,
                        "KR004": TRAINER,
                        "KR005": POKEMON,
                    }[card_id]
                )
            else:
                self.respond("Not found", 404)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests, mode
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def crawl(tmp_path, base, *args, append=False):
    output = tmp_path / "korean.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "crawl",
            "pokemon_kr",
            "-a",
            f"start_url={base}/cards",
            "-a",
            "search_text=테스트",
            "-a",
            "search_params=cardname",
            "-o" if append else "-O",
            str(output),
            "-s",
            "DOWNLOAD_DELAY=0",
            "-s",
            "AUTOTHROTTLE_ENABLED=False",
            "-s",
            "HTTPCACHE_ENABLED=False",
            *args,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return [
        json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()
    ], result.stderr


def test_loads_all_batches_until_empty_and_visits_each_detail_once(catalogue, tmp_path):
    base, requests, _ = catalogue
    items, logs = crawl(tmp_path, base)
    assert {item["supertype"] for item in items} == {"Pokémon", "Trainer", "Energy"}
    assert len(items) == 3, logs
    assert [fields["limit"] for method, _, fields in requests if method == "POST"] == [
        ["0"],
        ["1"],
        ["2"],
    ]
    assert sum(path.endswith("/KR002") for _, path, _ in requests) == 1
    assert any(path == "/robots.txt" for _, path, _ in requests)
    assert not any(".webp" in path for _, path, _ in requests)
    assert "'finish_reason': 'finished'" in logs


@pytest.mark.parametrize("argument,count", [("max_cards=1", 1), ("max_pages=1", 2)])
def test_limits_bound_real_network_requests(catalogue, tmp_path, argument, count):
    base, requests, _ = catalogue
    items, logs = crawl(tmp_path, base, "-a", argument)
    assert len(items) == count, logs
    assert sum(method == "POST" for method, _, _ in requests) == 1
    assert sum("/cards/detail/" in path for _, path, _ in requests) == count


@pytest.mark.parametrize(
    "mode_name,reason",
    [
        ("bad-json", "invalid_catalogue"),
        ("failed", "invalid_catalogue"),
        ("blocked", "blocked_429"),
    ],
)
def test_failed_requests_cannot_look_like_an_empty_catalogue(
    catalogue, tmp_path, mode_name, reason
):
    base, _, mode = catalogue
    mode["value"] = mode_name
    items, logs = crawl(tmp_path, base)
    assert items == []
    assert f"'finish_reason': '{reason}'" in logs


@pytest.mark.parametrize("max_cards", [0, 3])
def test_resume_keeps_post_pagination_budget_and_export(catalogue, tmp_path, max_cards):
    base, requests, mode = catalogue
    if max_cards:
        mode["value"] = "many"
    args = ("-a", f"max_cards={max_cards}", "-s", f"JOBDIR={tmp_path / 'job'}")
    first, logs = crawl(tmp_path, base, *args, "-s", "CLOSESPIDER_ITEMCOUNT=1")
    assert first and "'finish_reason': 'closespider_itemcount'" in logs
    items, logs = crawl(tmp_path, base, *args, append=True)
    assert len(items) == 3, logs
    assert len({item["card_id"] for item in items}) == 3
    assert "'finish_reason': 'finished'" in logs
    assert sum(path.endswith("/KR001") for _, path, _ in requests) == 1
