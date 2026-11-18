"""The future spiders' data must survive a real Scrapy JSONL export."""

import json
from io import BytesIO

import pytest
from scrapy.exporters import JsonLinesItemExporter

from tcg_scraper.item_pokemon import ItemPokemon


def export_record(**values):
    stream = BytesIO()
    exporter = JsonLinesItemExporter(stream, encoding="utf-8", ensure_ascii=False)
    exporter.start_exporting()
    exporter.export_item(ItemPokemon(**values))
    exporter.finish_exporting()
    return json.loads(stream.getvalue())


def test_old_and_unusual_printed_values_survive_export():
    record = export_record(
        name="Pokémon de test δ ★",
        supertype="Pokémon",
        language="fr",
        number="TG01",
        printed_number="TG01/TG30",
        level="X",
        hp="?",
        types=["Feu", "Métal"],
        illustrators=["Illustrateur A", "Illustrateur B"],
        images={
            "front": "https://example.org/card-front.png",
            "back": "https://example.org/card-back.png",
        },
        attacks=[
            {"name": "Attaque A", "cost": ["Feu", "Feu", "Incolore"], "damage": "30+"},
            {"name": "Attaque B", "damage": "20×", "text": "Texte synthétique."},
        ],
        abilities=[
            {"kind": "Poké-Power", "name": "Pouvoir A"},
            {"kind": "Poké-Body", "name": "Pouvoir B"},
        ],
        ancient_traits=[{"name": "Trait de test", "text": "Effet synthétique."}],
        weaknesses=[{"type": "Eau", "value": "×2"}],
        resistances=[{"type": "Combat", "value": "−30"}],
        printing={"edition": "1st Edition", "stamps": ["PROMO"], "finish": "holo"},
    )
    assert record["name"] == "Pokémon de test δ ★"
    assert record["number"] == "TG01"
    assert record["printed_number"] == "TG01/TG30"
    assert record["level"] == "X" and record["hp"] == "?"
    assert record["types"] == ["Feu", "Métal"]
    assert record["illustrators"] == ["Illustrateur A", "Illustrateur B"]
    assert record["images"]["front"] == "https://example.org/card-front.png"
    assert record["images"]["back"] == "https://example.org/card-back.png"
    assert record["attacks"][0]["cost"] == ["Feu", "Feu", "Incolore"]
    assert [attack["damage"] for attack in record["attacks"]] == ["30+", "20×"]
    assert [ability["kind"] for ability in record["abilities"]] == ["Poké-Power", "Poké-Body"]
    assert record["weaknesses"][0]["value"] == "×2"
    assert record["resistances"][0]["value"] == "−30"
    assert record["printing"]["stamps"] == ["PROMO"]


@pytest.mark.parametrize(
    "category, values",
    [
        ("Trainer", {"trainer_type": "Stadium", "trainer_text": "Effet synthétique."}),
        (
            "Energy",
            {
                "energy_type": "Special",
                "energy_text": "Effet conditionnel.",
                "provided_energy": [{"types": ["Feu", "Eau"], "amount": "variable"}],
            },
        ),
    ],
)
def test_non_pokemon_cards_do_not_invent_pokemon_statistics(category, values):
    record = export_record(name="Carte de test", supertype=category, **values)
    assert record["supertype"] == category
    assert "hp" not in record
    assert "retreat_cost" not in record
    if category == "Energy":
        assert record["provided_energy"][0]["amount"] == "variable"
    else:
        assert record["trainer_text"] == "Effet synthétique."


@pytest.mark.parametrize("mechanic, part_count", [("LEGEND", 2), ("V-UNION", 4)])
def test_multipart_card_keeps_its_identity_and_partial_information(mechanic, part_count):
    record = export_record(
        name="Carte multipartie de test",
        subtypes=[mechanic],
        composition={
            "group_name": "Assemblage de test",
            "part_index": 1,
            "part_count": part_count,
            "part_name": "upper-left",
            "related_cards": [{"number": "002"}, {"number": "003"}],
        },
        pokemon=[{"name": "Pokémon A", "generation": 1}, {"name": "Pokémon B", "generation": 5}],
    )
    assert record["composition"]["part_count"] == part_count
    assert record["composition"]["related_cards"][0]["number"] == "002"
    assert [pokemon["generation"] for pokemon in record["pokemon"]] == [1, 5]
    assert "hp" not in record


def test_unknown_mechanics_and_printed_text_can_be_preserved():
    record = export_record(
        name="Carte future",
        subtypes=["Future mechanic"],
        text_blocks=[{"kind": "unknown", "title": "Nouveau symbole", "text": "Texte original"}],
        raw_text="Texte original\n★ 001/099",
        additional_attributes={"new_symbol": {"label": "★", "values": [0, None]}},
        retreat_cost=[],
        converted_retreat_cost=0,
    )
    assert record["subtypes"] == ["Future mechanic"]
    assert record["additional_attributes"]["new_symbol"]["values"] == [0, None]
    assert record["raw_text"] == "Texte original\n★ 001/099"
    assert record["retreat_cost"] == []
    assert record["converted_retreat_cost"] == 0
