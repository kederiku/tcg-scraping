"""Les instantanés Scryfall doivent être identifiés et complets avant lecture."""

import gzip
import json

import pytest

from tcg_scraper.spiders.magic_scryfall import bulk_location, read_records


def test_all_cards_metadata_points_to_the_multilingual_snapshot():
    metadata = {
        "object": "bulk_data",
        "type": "all_cards",
        "jsonl_download_uri": "https://data.scryfall.io/all-cards/example.jsonl.gz",
        "compressed_size": 420,
    }
    assert bulk_location(metadata, "all_cards", "https://api.scryfall.com/bulk-data") == (
        metadata["jsonl_download_uri"],
        420,
    )
    for override in (
        {"type": "default_cards"},
        {"compressed_size": 0},
        {"jsonl_download_uri": "https://example.org/example.jsonl.gz"},
    ):
        with pytest.raises(ValueError):
            bulk_location(metadata | override, "all_cards", "https://api.scryfall.com/bulk-data")


def test_jsonl_reader_checks_the_trailer_even_after_a_complete_record(tmp_path):
    file = tmp_path / "truncated.gz"
    record = {"name": "Île"}
    file.write_bytes(gzip.compress(json.dumps(record).encode() + b"\n")[:-8])
    with pytest.raises((OSError, EOFError)):
        list(read_records(file))
