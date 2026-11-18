"""Real Scrapy scheduling/export/robots integration, with no external requests."""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from test_pokemon_jp import ENERGY, POKEMON, TRAINER

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def catalogue():
    requests = []
    mode = {"value": "normal"}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            url = urlsplit(self.path)
            status, content_type = 200, "text/html; charset=utf-8"
            if url.path == "/robots.txt":
                body = "User-agent: *\nDisallow: /private\n"
            elif url.path.endswith("resultAPI.php"):
                page = int(parse_qs(url.query)["page"][0])
                ids = ("1", "2") if page == 1 else ("2", "3")
                if mode["value"] == "many":
                    ids = ("1", "2") if page == 1 else ("3", "4", "5")
                body = json.dumps(
                    {
                        "result": 1,
                        "thisPage": page,
                        "maxPage": 2,
                        "hitCnt": 5 if mode["value"] == "many" else 3,
                        "regulation": "all",
                        "cardList": [{"cardID": cid} for cid in ids],
                    }
                )
                content_type = "application/json"
                if mode["value"] == "bad-json":
                    body = "<html>Maintenance</html>"
            elif "/details.php/" in url.path:
                cid = url.path.split("/card/")[1].split("/")[0]
                body = {"1": POKEMON, "2": TRAINER, "3": ENERGY, "4": TRAINER, "5": POKEMON}[cid]
                if mode["value"] == "blocked":
                    status, body = 429, "Slow down"
            else:
                status, body = 404, "Not found"
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body.encode())

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


def run_spider(tmp_path, base, *arguments, append=False, crash=False):
    output = tmp_path / "pokemon.jsonl"
    command = [sys.executable, "-m", "scrapy"]
    if crash:
        command = [
            sys.executable,
            "-c",
            (
                "from tcg_scraper.spiders.pokemon_jp import PokemonJpSpider\n"
                "def broken(self, response, card_id):\n"
                "    raise RuntimeError('simulated unexpected parser failure')\n"
                "PokemonJpSpider.parse_detail = broken\n"
                "from scrapy.cmdline import execute\nexecute()\n"
            ),
        ]
    result = subprocess.run(
        command
        + [
            "crawl",
            "pokemon_jp",
            "-a",
            f"start_url={base}/card-search/index.php?regulation_sidebar_form=all",
            "-o" if append else "-O",
            str(output),
            "-s",
            "DOWNLOAD_DELAY=0",
            "-s",
            "AUTOTHROTTLE_ENABLED=False",
            "-s",
            "HTTPCACHE_ENABLED=False",
            *arguments,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    # Scrapy 2.20 returns a nonzero status for the injected, unexpected callback error.
    assert result.returncode == (1 if crash else 0), result.stderr
    return [
        json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()
    ], result.stderr


def test_all_pages_details_deduplication_and_export(catalogue, tmp_path):
    base, requests, _ = catalogue
    items, logs = run_spider(tmp_path, base)
    assert len(items) == 3, logs
    assert {item["supertype"] for item in items} == {"Pokémon", "Trainer", "Energy"}
    assert {item["card_id"] for item in items} == {f"pokemon-card.com:{i}" for i in (1, 2, 3)}
    assert requests.count("/card-search/details.php/card/2/regu/all") == 1
    assert len([url for url in requests if "resultAPI.php" in url]) == 2
    assert "/robots.txt" in requests and "'finish_reason': 'finished'" in logs
    assert all(item["images"]["front"].startswith(base) for item in items)
    assert not any(".jpg" in url or "/products/" in url for url in requests)


def test_card_limit_bounds_network_requests(catalogue, tmp_path):
    base, requests, _ = catalogue
    items, logs = run_spider(tmp_path, base, "-a", "max_cards=1")
    assert len(items) == 1, logs
    assert len([url for url in requests if "/details.php/" in url]) == 1
    assert not any("page=2" in url for url in requests)


@pytest.mark.parametrize(
    ("mode_name", "reason"),
    [
        ("bad-json", "invalid_catalogue"),
        ("blocked", "blocked_429"),
    ],
)
def test_errors_close_with_visible_reason(catalogue, tmp_path, mode_name, reason):
    base, requests, mode = catalogue
    mode["value"] = mode_name
    items, logs = run_spider(tmp_path, base)
    assert items == []
    assert f"'finish_reason': '{reason}'" in logs
    assert not any("page=2" in url for url in requests)


@pytest.mark.parametrize("max_cards", [0, 3])
def test_jobdir_resumes_without_overwriting_or_resetting_budget(catalogue, tmp_path, max_cards):
    base, requests, mode = catalogue
    if max_cards:
        mode["value"] = "many"
    args = ("-a", f"max_cards={max_cards}", "-s", f"JOBDIR={tmp_path / 'job'}")
    partial, logs = run_spider(tmp_path, base, *args, "-s", "CLOSESPIDER_ITEMCOUNT=1")
    assert partial and "'finish_reason': 'closespider_itemcount'" in logs
    items, logs = run_spider(tmp_path, base, *args, append=True)
    assert len(items) == 3, logs
    assert len({item["card_id"] for item in items}) == 3
    assert "'finish_reason': 'finished'" in logs
    assert requests.count("/card-search/details.php/card/1/regu/all") == 1


def test_unexpected_parser_failure_cannot_report_finished(catalogue, tmp_path):
    base, _, _ = catalogue
    items, logs = run_spider(tmp_path, base, crash=True)
    assert items == []
    assert "'finish_reason': 'closespider_errorcount'" in logs
