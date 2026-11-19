"""Contrats d'export JSONL pour les impressions Magic, anciennes et modernes."""

import json
from io import BytesIO

import pytest
from scrapy.exporters import JsonLinesItemExporter

from tcg_scraper.item_magic import ItemMagic


def export_records(*items):
    stream = BytesIO()
    exporter = JsonLinesItemExporter(stream, encoding="utf-8", ensure_ascii=False)
    exporter.start_exporting()
    for item in items:
        exporter.export_item(item)
    exporter.finish_exporting()
    return [json.loads(line) for line in stream.getvalue().splitlines()]


@pytest.mark.parametrize(
    "fields",
    [
        {
            "name": "Black Lotus",
            "language": "en",
            "set": {"code": "LEA"},
            "number": "232",
            "printed_type_line": "Mono Artifact",
            "type_line": "Artifact",
            "mana_cost": "{0}",
            "mana_value": 0,
            "colors": [],
            "color_identity": [],
        },
        {
            "layout": "transform",
            "faces": [
                {
                    "name": "Gardienne",
                    "side": "front",
                    "mana_cost": "{X}{W/U}",
                    "power": "*",
                    "toughness": "1+*",
                    "printed_text": "Texte du recto.",
                    "oracle_text": "Front face rules.",
                    "images": {"normal": "https://example.org/a.jpg"},
                },
                {
                    "name": "Éveil",
                    "side": "back",
                    "loyalty": "X",
                    "images": {"normal": "https://example.org/b.jpg"},
                },
            ],
            "color_identity": ["W", "U"],
            "related_cards": [{"component": "token", "external_ids": {"catalogue": "T01"}}],
        },
        {
            "layout": "vanguard",
            "life_modifier": "+0",
            "hand_modifier": "−1",
            "raw_text": "☞\n★",
            "additional_attributes": {"catalogue": {"symbole": "★", "valeurs": [0, False]}},
        },
        {
            "types": ["Battle"],
            "subtypes": ["Siege"],
            "defense": "7",
            "legalities": {"vintage": "legal"},
            "rulings": [{"date": "2023-04-14", "text": "Précision de test."}],
        },
    ],
    ids=["alpha-sans-numero-imprime", "double-face", "vanguard", "bataille"],
)
def test_export_preserves_observed_fields_and_omits_unknowns(fields):
    assert export_records(ItemMagic(**fields)) == [fields]


@pytest.mark.parametrize(
    "name, characteristics",
    [
        ("Orcish Oriflamme", {"printed_mana_cost": "{1}{R}", "mana_cost": "{3}{R}"}),
        ("Cyclopean Tomb", {"printed_mana_cost": "", "mana_cost": "{4}"}),
        (
            "Elvish Archers",
            {"printed_power": "1", "printed_toughness": "2", "power": "2", "toughness": "1"},
        ),
    ],
)
def test_alpha_misprints_keep_original_and_oracle_values(name, characteristics):
    fields = {"name": name, "set": {"code": "LEA"}, **characteristics}
    assert export_records(ItemMagic(**fields)) == [fields]


def test_same_oracle_card_keeps_distinct_printings_and_languages():
    shared = {"oracle_id": "test-oracle", "number": "007a", "set": {"code": "TST"}}
    french = ItemMagic(
        **shared,
        card_id="test-fr-foil",
        language="fr",
        printing={"finish": "foil"},
        printed_text="Texte imprimé.",
        oracle_text="Current rules.",
    )
    english = ItemMagic(
        **shared, card_id="test-en-nonfoil", language="en", printing={"finish": "nonfoil"}
    )
    first, second = export_records(french, english)
    assert first["oracle_id"] == second["oracle_id"] == "test-oracle"
    assert first["number"] == second["number"] == "007a"
    assert first["card_id"] != second["card_id"]
    assert first["printing"]["finish"] == "foil" and second["printing"]["finish"] == "nonfoil"
    assert first["printed_text"] == "Texte imprimé." and first["oracle_text"] == "Current rules."
    assert "printed_text" not in second
