"""Real Scrapy HTTP, sitemap chaining and JOBDIR on a local-only catalogue."""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from test_pokemon_id import POKEMON_BODY, detail_html, sitemap

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def catalogue():
    requests = []
    mode = {"value": "normal"}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            status = 200
            if self.path == "/robots.txt":
                body = "User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /*?page=\n"
            elif self.path == "/sitemaps/sitemap.xml":
                body = sitemap(
                    [
                        base + "/sitemaps/sitemap-cards-id1.xml",
                        base + "/sitemaps/sitemap-cards-jp1.xml",
                        base + "/sitemaps/sitemap-cards-id2.xml",
                    ],
                    index=True,
                ).text
            elif self.path.startswith("/sitemaps/sitemap-cards-id"):
                ids = [101, 102] if self.path.endswith("id1.xml") else [102, 103, 104, 105]
                body = sitemap([base + f"/cards/{number}/test" for number in ids]).text
                if mode["value"] == "bad-xml":
                    body = "<html>Unexpected response</html>"
            elif self.path.startswith("/cards/"):
                card_id = self.path.split("/")[2]
                category = {"101": "Pokémon", "102": "Item", "103": "Basic Energy"}.get(
                    card_id, "Pokémon"
                )
                body = detail_html(
                    card_id,
                    category=category,
                    body=POKEMON_BODY
                    if category == "Pokémon"
                    else '<p id="card-description">Effect.</p>',
                    stats=category == "Pokémon",
                    region=2 if mode["value"] == "wrong-region" else 4,
                )
                if mode["value"] == "blocked":
                    body, status = "Slow down", 429
            else:
                body, status = "Unexpected URL", 404
            self.send_response(status)
            kind = "application/xml" if self.path.endswith(".xml") else "text/html"
            self.send_header("Content-Type", kind + "; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    base = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield base, requests, mode
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def crawl(tmp_path, base, *args, append=False):
    output = tmp_path / "indonesian.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "crawl",
            "pokemon_id",
            "-a",
            f"start_url={base}/sitemaps/sitemap.xml",
            "-a",
            f"card_base_url={base}",
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


def test_full_catalogue_uses_only_indonesian_sitemaps_and_unique_details(catalogue, tmp_path):
    base, requests, _ = catalogue
    items, logs = crawl(tmp_path, base)
    assert len(items) == 5, logs
    assert {item["supertype"] for item in items} == {"Pokémon", "Trainer", "Energy"}
    assert requests.count("/cards/102/test") == 1
    assert set(requests) == {
        "/robots.txt",
        "/sitemaps/sitemap.xml",
        "/sitemaps/sitemap-cards-id1.xml",
        "/sitemaps/sitemap-cards-id2.xml",
        *(f"/cards/{n}/test" for n in range(101, 106)),
    }
    assert "'finish_reason': 'finished'" in logs


@pytest.mark.parametrize("argument,count", [("max_cards=1", 1), ("max_sitemaps=1", 2)])
def test_limits_prevent_extra_network_requests(catalogue, tmp_path, argument, count):
    base, requests, _ = catalogue
    items, logs = crawl(tmp_path, base, "-a", argument)
    assert len(items) == count, logs
    assert "/sitemaps/sitemap-cards-id2.xml" not in requests
    assert sum(path.startswith("/cards/") for path in requests) == count


@pytest.mark.parametrize("max_cards,count", [(0, 5), (3, 3)])
def test_resume_keeps_budget_and_pending_sitemaps(catalogue, tmp_path, max_cards, count):
    base, requests, _ = catalogue
    args = ("-a", f"max_cards={max_cards}", "-s", f"JOBDIR={tmp_path / 'job'}")
    first, logs = crawl(tmp_path, base, *args, "-s", "CLOSESPIDER_ITEMCOUNT=1")
    assert first and "'finish_reason': 'closespider_itemcount'" in logs
    items, logs = crawl(tmp_path, base, *args, append=True)
    assert len(items) == len({item["card_id"] for item in items}) == count, logs
    assert requests.count("/cards/101/test") == 1
    assert "'finish_reason': 'finished'" in logs


@pytest.mark.parametrize(
    "mode_name,reason",
    [
        ("bad-xml", "invalid_catalogue"),
        ("blocked", "blocked_429"),
        ("wrong-region", "invalid_card_detail"),
    ],
)
def test_invalid_responses_and_blocks_stop_explicitly(catalogue, tmp_path, mode_name, reason):
    base, _, mode = catalogue
    mode["value"] = mode_name
    items, logs = crawl(tmp_path, base)
    assert not items
    assert f"'finish_reason': '{reason}'" in logs
