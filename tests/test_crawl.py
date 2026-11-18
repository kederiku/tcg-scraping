"""End-to-end contracts against our own server, never a merchant."""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def website():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            status = 200
            if self.path == "/robots.txt":
                body = "User-agent: *\nDisallow: /private\n"
            elif self.path.startswith("/blocked/"):
                status = int(self.path.rsplit("/", 1)[1])
                body = "Access blocked"
            else:
                second = "page/2" in self.path
                quote = (
                    '<div class="quote"><span class="text">'
                    + ("Second quote" if second else "First quote")
                    + '</span><small class="author">Ada</small>'
                    '<div class="tags"><a class="tag">testing</a></div></div>'
                )
                next_path = "/js/page/2" if self.path.startswith("/js") else "/page/2"
                next_link = f'<li class="next"><a href="{next_path}">Next</a></li>'
                content = quote + ("" if second else next_link)
                if self.path.startswith("/js"):
                    body = (
                        '<html><body><main id="content"></main><script>'
                        "setTimeout(() => {document.querySelector('#content').innerHTML = "
                        + json.dumps(content)
                        + ";}, 50);</script></body></html>"
                    )
                else:
                    body = f"<html><body>{content}</body></html>"
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            if status == 429:
                self.send_header("Retry-After", "120")
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def crawl(tmp_path, url, *, javascript=False, max_pages=3):
    output = tmp_path / "items.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "crawl",
            "quotes",
            "-a",
            f"start_url={url}",
            "-a",
            f"javascript={str(javascript).lower()}",
            "-a",
            f"max_pages={max_pages}",
            "-O",
            str(output),
            "-s",
            "DOWNLOAD_DELAY=0",
            "-s",
            "AUTOTHROTTLE_ENABLED=False",
            "-s",
            "HTTPCACHE_ENABLED=False",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    items = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    return items, result.stderr


@pytest.mark.parametrize("javascript", [False, True])
def test_extracts_and_follows_pagination(website, tmp_path, javascript):
    base, requests = website
    items, logs = crawl(tmp_path, base + ("/js" if javascript else "/"), javascript=javascript)
    assert [item["text"] for item in items] == ["First quote", "Second quote"], logs
    assert items[0]["author"] == "Ada"
    assert items[0]["tags"] == ["testing"]
    assert items[0]["source_url"].startswith(base)
    assert "/robots.txt" in requests


@pytest.mark.parametrize("javascript", [False, True])
def test_page_limit_prevents_second_request(website, tmp_path, javascript):
    base, requests = website
    items, logs = crawl(
        tmp_path, base + ("/js" if javascript else "/"), javascript=javascript, max_pages=1
    )
    assert len(items) == 1, logs
    assert not any("page/2" in path for path in requests)


@pytest.mark.parametrize("javascript", [False, True])
def test_robots_disallow_is_not_fetched(website, tmp_path, javascript):
    base, requests = website
    items, _ = crawl(tmp_path, base + "/private", javascript=javascript)
    assert items == []
    assert "/private" not in requests


@pytest.mark.parametrize("status", [403, 429])
@pytest.mark.parametrize("javascript", [False, True])
def test_blocked_response_stops_without_retry(website, tmp_path, status, javascript):
    base, requests = website
    items, logs = crawl(tmp_path, f"{base}/blocked/{status}", javascript=javascript)
    assert items == []
    assert requests.count(f"/blocked/{status}") == 1
    assert f"blocked_{status}" in logs
    if status == 429:
        assert "120" in logs


@pytest.mark.parametrize("max_pages", ["0", "-1", "nope"])
def test_invalid_page_limit_is_rejected(website, tmp_path, max_pages):
    base, requests = website
    with pytest.raises(AssertionError, match="max_pages must be a positive integer"):
        crawl(tmp_path, base, max_pages=max_pages)
    assert requests == []
