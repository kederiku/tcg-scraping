"""Mapping contracts for the Scryfall all_cards bulk format."""

import pytest

from tcg_scraper.item_magic import ItemMagic
from tcg_scraper.scryfall_cards import parse_card

SCRAPED_AT = "2026-11-19T12:00:00+00:00"
BASE_CARD = {"object": "card", "id": "printing-id", "lang": "en", "set": "tst"}


def test_preserves_printing_identity_and_finishes():
    item = parse_card(
        {
            **BASE_CARD,
            "oracle_id": "oracle-id",
            "name": "Test Creature",
            "scryfall_uri": "https://scryfall.com/card/tst/007★/test-creature",
            "set_id": "expansion-id",
            "set_name": "Test Set",
            "set_type": "expansion",
            "collector_number": "007★",
            "released_at": "2024-05-31",
            "rarity": "rare",
            "finishes": ["nonfoil", "foil", "etched"],
            "frame": "2015",
            "full_art": False,
            "variation": True,
            "variation_of": "another-printing-id",
            "games": ["paper", "arena", "mtgo"],
            "arena_id": 12,
            "mtgo_id": 27,
            "mtgo_foil_id": 28,
            "multiverse_ids": [45, 46],
            "artist": "A & B",
            "image_uris": {"normal": "https://cards.scryfall.io/example.jpg"},
        },
        SCRAPED_AT,
    )

    assert isinstance(item, ItemMagic)
    assert item["card_id"] == "printing-id"
    assert item["oracle_id"] == "oracle-id"
    assert item["name"] == item["oracle_name"] == "Test Creature"
    assert item["language"] == "en"
    assert item["source_name"] == "scryfall.com"
    assert item["source_url"] == "https://scryfall.com/card/tst/007★/test-creature"
    assert item["scraped_at"] == SCRAPED_AT
    assert item["set"] == {
        "code": "tst",
        "id": "expansion-id",
        "name": "Test Set",
        "type": "expansion",
    }
    assert item["number"] == "007★"
    assert "printed_number" not in item
    assert item["release_date"] == "2024-05-31"
    assert item["rarity"] == "rare"
    assert item["printing"] == {
        "available_finishes": ["nonfoil", "foil", "etched"],
        "frame": "2015",
        "is_full_art": False,
        "is_variation": True,
        "variation_of": "another-printing-id",
    }
    assert item["games"] == ["paper", "arena", "mtgo"]
    assert item["external_ids"] == {
        "scryfall": "printing-id",
        "arena": 12,
        "mtgo": 27,
        "mtgo_foil": 28,
        "gatherer": [45, 46],
    }
    assert item["illustrators"] == ["A & B"]
    assert item["images"] == {"normal": "https://cards.scryfall.io/example.jpg"}


def test_keeps_printed_fields_distinct_from_oracle_rules():
    item = parse_card(
        {
            **BASE_CARD,
            "lang": "fr",
            "name": "Test Creature",
            "printed_name": "Créature témoin",
            "type_line": "Artifact Creature — Insect",
            "printed_type_line": "Créature-artefact : insecte",
            "oracle_text": "Flying\n{T}: Add {C}.",
            "printed_text": "Vol\n{T} : Ajoutez {C}.",
            "flavor_text": "Une créature étrange.",
            "mana_cost": "",
            "cmc": 0,
            "colors": [],
            "color_identity": [],
            "produced_mana": ["C"],
            "power": "*",
            "toughness": "1+*",
            "keywords": ["Flying"],
            "reserved": False,
            "legalities": {"legacy": "legal"},
        },
        SCRAPED_AT,
    )

    assert item["name"] == "Créature témoin"
    assert item["oracle_name"] == "Test Creature"
    assert item["printed_type_line"] == "Créature-artefact : insecte"
    assert item["type_line"] == "Artifact Creature — Insect"
    assert item["printed_text"] == "Vol\n{T} : Ajoutez {C}."
    assert item["oracle_text"] == "Flying\n{T}: Add {C}."
    assert item["flavor_text"] == "Une créature étrange."
    assert item["mana_cost"] == ""
    assert item["mana_value"] == 0
    assert "printed_mana_cost" not in item
    assert "printed_power" not in item
    assert item["colors"] == item["color_identity"] == []
    assert item["produced_mana"] == ["C"]
    assert item["power"] == "*"
    assert item["toughness"] == "1+*"
    assert item["keywords"] == ["Flying"]
    assert item["is_reserved"] is False
    assert item["legalities"] == {"legacy": "legal"}


@pytest.mark.parametrize("language", ["en", "ja"])
def test_missing_printed_data_is_omitted(language):
    item = parse_card(
        {
            **BASE_CARD,
            "lang": language,
            "name": "Test Creature",
            "oracle_text": "Flying",
            "type_line": "Creature",
        },
        SCRAPED_AT,
    )

    assert "printed_text" not in item
    assert "printed_type_line" not in item
    assert item["oracle_name"] == "Test Creature"
    assert item.get("name") == ("Test Creature" if language == "en" else None)


def test_translated_face_names_are_joined_in_order_when_top_name_is_absent():
    item = parse_card(
        {
            **BASE_CARD,
            "lang": "fr",
            "name": "Siege // Rescue",
            "layout": "transform",
            "color_identity": ["R", "W"],
            "card_faces": [
                {
                    "object": "card_face",
                    "name": "Siege",
                    "printed_name": "Siège",
                    "oracle_text": "Front effect.",
                    "printed_text": "Effet du recto.",
                    "type_line": "Battle — Siege",
                    "mana_cost": "{2}{R}",
                    "defense": "4",
                    "image_uris": {"normal": "https://cards.scryfall.io/front.jpg"},
                },
                {
                    "object": "card_face",
                    "name": "Rescue",
                    "printed_name": "Sauvetage",
                    "oracle_text": "Back effect.",
                    "printed_text": "Effet du verso.",
                    "colors": ["W"],
                    "mana_cost": "",
                    "power": "3",
                    "toughness": "2",
                    "artist": "An Artist",
                    "illustration_id": "art-id",
                    "image_uris": {"normal": "https://cards.scryfall.io/back.jpg"},
                    "future_face_field": {"count": 0},
                },
            ],
        },
        SCRAPED_AT,
    )

    assert item["name"] == "Siège // Sauvetage"
    assert item["oracle_name"] == "Siege // Rescue"
    assert item["color_identity"] == ["R", "W"]
    assert "images" not in item
    assert item["faces"] == [
        {
            "side": "front",
            "name": "Siège",
            "oracle_name": "Siege",
            "oracle_text": "Front effect.",
            "printed_text": "Effet du recto.",
            "type_line": "Battle — Siege",
            "mana_cost": "{2}{R}",
            "defense": "4",
            "images": {"normal": "https://cards.scryfall.io/front.jpg"},
        },
        {
            "side": "back",
            "name": "Sauvetage",
            "oracle_name": "Rescue",
            "oracle_text": "Back effect.",
            "printed_text": "Effet du verso.",
            "colors": ["W"],
            "mana_cost": "",
            "power": "3",
            "toughness": "2",
            "illustrators": ["An Artist"],
            "printing": {"illustration_id": "art-id"},
            "images": {"normal": "https://cards.scryfall.io/back.jpg"},
            "additional_attributes": {"future_face_field": {"count": 0}},
        },
    ]


def test_partial_localization_does_not_join_names_in_different_languages():
    item = parse_card(
        {
            **BASE_CARD,
            "lang": "ja",
            "layout": "adventure",
            "name": "Knights // Quest",
            "card_faces": [
                {"object": "card_face", "name": "Knights", "printed_name": "騎士"},
                {"object": "card_face", "name": "Quest"},
            ],
            "image_uris": {"normal": "https://cards.scryfall.io/front.jpg"},
        },
        SCRAPED_AT,
    )

    assert "name" not in item
    assert item["faces"] == [
        {"side": "front", "name": "騎士", "oracle_name": "Knights"},
        {"side": "front", "oracle_name": "Quest"},
    ]
    assert item["images"] == {"normal": "https://cards.scryfall.io/front.jpg"}


def test_reversible_cards_keep_oracle_ids_of_the_individual_faces():
    item = parse_card(
        {
            **BASE_CARD,
            "layout": "reversible_card",
            "card_faces": [
                {"object": "card_face", "oracle_id": "oracle-1", "cmc": 1.5},
                {"object": "card_face", "oracle_id": "oracle-2", "cmc": 2},
            ],
        },
        SCRAPED_AT,
    )

    assert "oracle_id" not in item
    assert item["faces"] == [
        {"side": "front", "oracle_id": "oracle-1", "mana_value": 1.5},
        {"side": "back", "oracle_id": "oracle-2", "mana_value": 2},
    ]


def test_keeps_related_cards_and_new_fields_without_commercial_data():
    item = parse_card(
        {
            **BASE_CARD,
            "layout": "meld",
            "all_parts": [
                {
                    "object": "related_card",
                    "id": "meld-result-id",
                    "component": "meld_result",
                    "name": "Joined Creature",
                    "type_line": "Legendary Creature",
                    "uri": "https://api.scryfall.com/cards/meld-result-id",
                }
            ],
            "prices": {"eur": "12.00"},
            "purchase_uris": {"cardmarket": "https://example.org/shop"},
            "tcgplayer_id": 20,
            "tcgplayer_etched_id": 21,
            "cardmarket_id": 22,
            "related_uris": {
                "gatherer": "https://gatherer.wizards.com/",
                "tcgplayer_infinite_articles": "https://example.org/articles",
            },
            "future_print_field": [0, False, "★"],
        },
        SCRAPED_AT,
    )

    assert item["related_cards"] == [
        {
            "card_id": "meld-result-id",
            "external_ids": {"scryfall": "meld-result-id"},
            "component": "meld_result",
            "name": "Joined Creature",
            "type_line": "Legendary Creature",
            "url": "https://api.scryfall.com/cards/meld-result-id",
        }
    ]
    assert item["external_ids"] == {
        "scryfall": "printing-id",
        "tcgplayer": 20,
        "tcgplayer_etched": 21,
        "cardmarket": 22,
    }
    assert item["additional_attributes"] == {
        "future_print_field": [0, False, "★"],
        "related_uris": {
            "gatherer": "https://gatherer.wizards.com/",
            "tcgplayer_infinite_articles": "https://example.org/articles",
        },
    }


@pytest.mark.parametrize(
    "record, missing",
    [
        (None, "object"),
        ({**BASE_CARD, "object": "error"}, "object"),
        ({**BASE_CARD, "id": None}, "id"),
        ({**BASE_CARD, "lang": " "}, "lang"),
        ({**BASE_CARD, "set": []}, "set"),
    ],
)
def test_rejects_records_without_valid_card_identity(record, missing):
    with pytest.raises(ValueError, match=rf"\b{missing}\b"):
        parse_card(record, SCRAPED_AT)
