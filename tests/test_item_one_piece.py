"""Contrats d'export JSONL pour des impressions One Piece synthétiques."""

import json
from io import BytesIO

import pytest
from scrapy.exporters import JsonLinesItemExporter

from tcg_scraper.item_one_piece import ItemOnePiece


def export_records(*items):
    stream = BytesIO()
    exporter = JsonLinesItemExporter(stream, encoding="utf-8", ensure_ascii=False)
    exporter.start_exporting()
    for item in items:
        exporter.export_item(item)
    exporter.finish_exporting()
    return [json.loads(line) for line in stream.getvalue().splitlines()]


@pytest.mark.parametrize(
    "values",
    [
        {
            "card_type": "LEADER",
            "life": "4",
            "power": "5000",
            "colors": ["Rouge", "Vert"],
            "attributes": ["Slash"],
            "types": ["Supernovas", "Straw Hat Crew"],
        },
        {
            "card_type": "CHARACTER",
            "cost": "1",
            "power": "0",
            "counter": "+2000",
            "keywords": ["Blocker"],
            "effects": [
                {"labels": ["DON!! ×1", "When Attacking"], "text": "Premier effet de test."},
                {"labels": ["On K.O."], "text": "Deuxième effet de test."},
            ],
        },
        {
            "card_type": "EVENT",
            "cost": "0",
            "effects": [{"labels": ["Counter"], "text": "Effet de contre de test."}],
            "trigger": "Activez l’effet de cette carte.",
        },
        {"card_type": "STAGE", "cost": "2", "types": ["海軍"]},
        {"card_type": "DON!!", "don_power_bonus": "+1000", "raw_text": "自分のターン +1000"},
    ],
    ids=["leader-bicolore", "personnage", "evenement", "stage", "don"],
)
def test_card_exports_only_the_observed_characteristics(values):
    assert export_records(ItemOnePiece(**values)) == [values]


def test_parallel_and_reprint_keep_their_identity_with_the_same_card_number():
    shared = {"number": "OP01-001", "rarity": "L", "language": "fr"}
    parallel = ItemOnePiece(
        **shared,
        card_id="fr-op01-parallel",
        set={"code": "OP-01"},
        printing={"variant": "Parallel", "finish": "foil"},
        images={"front": "https://example.org/parallel.png"},
    )
    reprint = ItemOnePiece(
        **shared,
        card_id="fr-prb01",
        set={"code": "PRB-01"},
        block_icon="X",
        external_ids={"catalogue": "00042"},
    )
    first, second = export_records(parallel, reprint)
    assert first["number"] == second["number"] == "OP01-001"
    assert first["card_id"] != second["card_id"]
    assert first["printing"]["variant"] == "Parallel"
    assert first["images"]["front"].endswith("/parallel.png")
    assert [first["set"]["code"], second["set"]["code"]] == ["OP-01", "PRB-01"]
    assert second["block_icon"] == "X"
    assert second["external_ids"]["catalogue"] == "00042"
