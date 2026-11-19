"""Exercise the Scryfall CLI and on-disk export against a local bulk API."""

import gzip
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORACLE_ID = "00000000-0000-4000-8000-000000000001"
ENGLISH_ID = "00000000-0000-4000-8000-000000000011"
FRENCH_ID = "00000000-0000-4000-8000-000000000012"
OTHER_ID = "00000000-0000-4000-8000-000000000013"
RULING = "This rule applies to every printing of Test Mage."
PREVIOUS_EXPORT = b'{"card_id":"previous"}\n'


def gzip_jsonl(*rows):
    lines = [
        row if isinstance(row, bytes) else json.dumps(row, ensure_ascii=False).encode("utf-8")
        for row in rows
    ]
    return gzip.compress(b"\n".join(lines) + b"\n")


def card(card_id, oracle_id, lang, name, finishes, **fields):
    return {
        "object": "card",
        "id": card_id,
        "oracle_id": oracle_id,
        "lang": lang,
        "name": name,
        "layout": "normal",
        "scryfall_uri": f"https://scryfall.com/card/tst/007a/{lang}/test-mage",
        "collector_number": "007a",
        "set": "tst",
        "set_name": "Test Set",
        "games": ["paper"],
        "finishes": finishes,
        "oracle_text": "Reference rules.",
        **fields,
    }


@pytest.fixture
def bulk_api():
    calls = []
    mode = {"value": "normal"}
    cards = (
        card(ENGLISH_ID, ORACLE_ID, "en", "Test Mage", ["nonfoil", "foil"]),
        card(
            FRENCH_ID,
            ORACLE_ID,
            "fr",
            "Test Mage",
            ["nonfoil"],
            printed_name="Mage d’essai",
            printed_text="Règles imprimées.",
        ),
        card(
            OTHER_ID,
            "00000000-0000-4000-8000-000000000002",
            "en",
            "Other Mage",
            ["nonfoil"],
        ),
    )
    rulings = gzip_jsonl(
        {
            "object": "ruling",
            "oracle_id": ORACLE_ID,
            "source": "wotc",
            "published_at": "2025-01-24",
            "comment": RULING,
        }
    )
    full_cards = gzip_jsonl(*cards)

    class Handler(BaseHTTPRequestHandler):
        def respond(self, body, content_type, *, encoding=None, length=None, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body) if length is None else length))
            if encoding:
                self.send_header("Content-Encoding", encoding)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            calls.append((self.path, self.headers.get("Accept-Encoding")))
            card_payload = full_cards
            if mode["value"] == "malformed_row":
                card_payload = gzip_jsonl(cards[0], b'{"object":')
            if mode["value"] == "truncated_gzip":
                card_payload = full_cards[:-8]
            downloads = {"rulings": rulings, "all-cards": card_payload}

            if self.path == "/robots.txt":
                self.respond(b"User-agent: *\nAllow: /\n", "text/plain")
            elif self.path.startswith("/bulk-data/"):
                kind = self.path.rsplit("/", 1)[-1]
                compressed_size = len(downloads[kind])
                if kind == "all-cards" and mode["value"] == "wrong_compressed_size":
                    compressed_size += 1
                metadata = {
                    "object": "bulk_data",
                    "type": kind.replace("-", "_"),
                    "updated_at": "2025-01-24T00:00:00.000+00:00",
                    "compressed_size": compressed_size,
                    "jsonl_download_uri": f"{base}/download/{kind}.jsonl.gz",
                }
                self.respond(json.dumps(metadata).encode("utf-8"), "application/json")
            elif self.path.startswith("/download/"):
                kind = self.path.removeprefix("/download/").removesuffix(".jsonl.gz")
                payload = downloads[kind]
                size = len(payload)
                if kind == "all-cards" and mode["value"] == "truncated_transfer":
                    payload = payload[:-8]
                self.respond(payload, "application/x-ndjson", encoding="gzip", length=size)
            else:
                self.respond(b"Missing", "text/plain", status=404)

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        base = f"http://127.0.0.1:{server.server_port}"
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        thread.start()
        try:
            yield base, calls, mode
        finally:
            server.shutdown()
            thread.join()


def crawl(base, output, *args, cli_overwrite=False):
    destination = ["-O", str(output)] if cli_overwrite else ["-a", f"output={output}"]
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "crawl",
            "magic_scryfall",
            *destination,
            "-s",
            f"SCRYFALL_BULK_API={base}/bulk-data",
            "-s",
            "DOWNLOAD_DELAY=0",
            "-s",
            "AUTOTHROTTLE_ENABLED=False",
            *args,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )


def read_export(output):
    return [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]


def test_bulk_export_joins_rulings_to_each_printing_and_preserves_finishes(bulk_api, tmp_path):
    base, calls, _ = bulk_api
    output = tmp_path / "magic.jsonl"
    output.write_bytes(PREVIOUS_EXPORT)

    result = crawl(base, output)

    assert result.returncode == 0, result.stdout + result.stderr
    rows = read_export(output)
    by_id = {row["card_id"]: row for row in rows}
    assert len(rows) == 3
    assert by_id.keys() == {ENGLISH_ID, FRENCH_ID, OTHER_ID}
    english, french = by_id[ENGLISH_ID], by_id[FRENCH_ID]
    assert english["language"] == "en"
    assert english["printing"]["available_finishes"] == ["nonfoil", "foil"]
    assert french["language"] == "fr"
    assert french["name"] == "Mage d’essai"
    assert french["printed_text"] == "Règles imprimées."
    for row in (english, french):
        assert row["oracle_id"] == ORACLE_ID
        assert row["rulings"] == [{"date": "2025-01-24", "source": "wotc", "text": RULING}]
    assert not by_id[OTHER_ID].get("rulings")
    assert calls[0][0] == "/robots.txt"
    assert [path for path, _ in calls[1:]] == [
        "/bulk-data/rulings",
        "/download/rulings.jsonl.gz",
        "/bulk-data/all-cards",
        "/download/all-cards.jsonl.gz",
    ]
    assert [encoding for path, encoding in calls if path.startswith("/download/")] == [
        "identity",
        "identity",
    ]


def test_sample_limit_counts_exported_printings(bulk_api, tmp_path):
    base, _, _ = bulk_api
    output = tmp_path / "magic-sample.jsonl"

    result = crawl(base, output, "-a", "max_cards=1")

    assert result.returncode == 0, result.stdout + result.stderr
    (row,) = read_export(output)
    assert row["card_id"] == ENGLISH_ID
    assert row["rulings"][0]["text"] == RULING


@pytest.mark.parametrize(
    "failure", ["truncated_transfer", "wrong_compressed_size", "truncated_gzip", "malformed_row"]
)
def test_invalid_bulk_keeps_previous_export(bulk_api, tmp_path, failure):
    base, calls, mode = bulk_api
    mode["value"] = failure
    output = tmp_path / "magic.jsonl"
    output.write_bytes(PREVIOUS_EXPORT)

    result = crawl(base, output)

    assert result.returncode != 0, result.stdout + result.stderr
    assert any(path == "/download/all-cards.jsonl.gz" for path, _ in calls), result.stderr
    assert output.read_bytes() == PREVIOUS_EXPORT
    assert set(tmp_path.iterdir()) == {output}


def test_local_overwrite_publishes_only_a_successful_crawl(bulk_api, tmp_path):
    base, _, mode = bulk_api
    output = tmp_path / "my cards.jsonl"
    output.write_bytes(PREVIOUS_EXPORT)
    mode["value"] = "malformed_row"
    assert crawl(base, output, cli_overwrite=True).returncode != 0
    assert output.read_bytes() == PREVIOUS_EXPORT
    mode["value"] = "ok"
    result = crawl(base, output, cli_overwrite=True)
    assert result.returncode == 0, result.stderr
    assert len(read_export(output)) == 3
