"""Map Scryfall bulk card records to ItemMagic without network requests."""

from tcg_scraper.item_magic import ItemMagic

_CONTENT_FIELDS = {
    key: key
    for key in (
        "oracle_id",
        "flavor_name",
        "layout",
        "mana_cost",
        "colors",
        "color_identity",
        "color_indicator",
        "produced_mana",
        "type_line",
        "printed_type_line",
        "power",
        "toughness",
        "loyalty",
        "defense",
        "hand_modifier",
        "life_modifier",
        "attraction_lights",
        "keywords",
        "printed_text",
        "oracle_text",
        "flavor_text",
    )
}
_CONTENT_FIELDS.update(
    name="oracle_name", cmc="mana_value", image_uris="images", reserved="is_reserved"
)
_CARD_FIELDS = {
    "id": "card_id",
    "lang": "language",
    "scryfall_uri": "source_url",
    "collector_number": "number",
    "released_at": "release_date",
    "rarity": "rarity",
    "games": "games",
    "legalities": "legalities",
}
_SET_FIELDS = {
    "set": "code",
    "set_id": "id",
    "set_name": "name",
    "set_type": "type",
    "set_uri": "api_url",
    "scryfall_set_uri": "url",
    "set_search_uri": "search_url",
}
_PRINTING_FIELDS = {
    "finishes": "available_finishes",
    "foil": "foil",
    "nonfoil": "nonfoil",
    "frame": "frame",
    "frame_effects": "frame_effects",
    "border_color": "border_color",
    "watermark": "watermark",
    "security_stamp": "security_stamp",
    "promo_types": "promo_types",
    "illustration_id": "illustration_id",
    "artist_id": "artist_id",
    "artist_ids": "artist_ids",
    "card_back_id": "card_back_id",
    "image_status": "image_status",
    "highres_image": "has_highres_image",
    "full_art": "is_full_art",
    "textless": "is_textless",
    "reprint": "is_reprint",
    "oversized": "is_oversized",
    "digital": "is_digital",
    "promo": "is_promo",
    "booster": "in_boosters",
    "story_spotlight": "is_story_spotlight",
    "variation": "is_variation",
    "variation_of": "variation_of",
}
_EXTERNAL_IDS = {
    "id": "scryfall",
    "multiverse_ids": "gatherer",
    "arena_id": "arena",
    "mtgo_id": "mtgo",
    "mtgo_foil_id": "mtgo_foil",
    "tcgplayer_id": "tcgplayer",
    "tcgplayer_etched_id": "tcgplayer_etched",
    "cardmarket_id": "cardmarket",
}
_PART_FIELDS = {
    "id": "card_id",
    "component": "component",
    "name": "name",
    "type_line": "type_line",
    "uri": "url",
}
_DOUBLE_SIDED = {"transform", "modal_dfc", "double_faced_token", "reversible_card", "art_series"}
_SHARED_FRONT = {"split", "flip", "adventure"}
_COMMERCE_FIELDS = {"prices", "purchase_uris"}
_CONTENT_CONSUMED = _CONTENT_FIELDS.keys() | _PRINTING_FIELDS.keys() | {"printed_name", "artist"}
_CARD_CONSUMED = (
    _CONTENT_CONSUMED
    | _CARD_FIELDS.keys()
    | _SET_FIELDS.keys()
    | _EXTERNAL_IDS.keys()
    | {"card_faces", "all_parts"}
)


def _fields(record, mapping):
    return {
        target: record[source]
        for source, target in mapping.items()
        if record.get(source) is not None
    }


def _additional_attributes(record, consumed):
    attributes = {
        key: value
        for key, value in record.items()
        if key not in consumed and key not in _COMMERCE_FIELDS and key != "object"
    }
    if attributes:
        return {"additional_attributes": attributes}
    return {}


def _content(record, language):
    data = _fields(record, _CONTENT_FIELDS)
    if name := record.get("printed_name") or (record.get("name") if language == "en" else None):
        data["name"] = name
    if artist := record.get("artist"):
        data["illustrators"] = [artist]
    if printing := _fields(record, _PRINTING_FIELDS):
        data["printing"] = printing
    return data


def _members(record, key):
    members = record.get(key)
    if members is not None and (
        not isinstance(members, list) or any(not isinstance(member, dict) for member in members)
    ):
        raise ValueError(f"Scryfall card field {key} must be a list of objects")
    return members


def _faces(card_faces, language, layout):
    sides = ()
    if layout in _DOUBLE_SIDED:
        sides = ("front", "back")
    elif layout in _SHARED_FRONT:
        sides = ("front",) * len(card_faces)

    result = []
    for index, face in enumerate(card_faces):
        data = _content(face, language)
        if index < len(sides):
            data["side"] = sides[index]
        data.update(_additional_attributes(face, _CONTENT_CONSUMED))
        result.append(data)
    return result


def _related_part(part):
    data = _fields(part, _PART_FIELDS)
    if part_id := data.get("card_id"):
        data["external_ids"] = {"scryfall": part_id}
    data.update(_additional_attributes(part, _PART_FIELDS.keys()))
    return data


def parse_card(card: dict, scraped_at: str) -> ItemMagic:
    """Map one printing; Scryfall may group several finishes under the same ID."""
    if not isinstance(card, dict) or card.get("object") != "card":
        raise ValueError("Expected a Scryfall object of type card")
    for key in ("id", "lang", "set"):
        value = card.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing or invalid Scryfall card field {key}")

    language = card["lang"]
    data = _content(card, language)
    data.update(_fields(card, _CARD_FIELDS))
    data["source_name"] = "scryfall.com"
    data["scraped_at"] = scraped_at
    data["set"] = _fields(card, _SET_FIELDS)
    data["external_ids"] = _fields(card, _EXTERNAL_IDS)

    if (card_faces := _members(card, "card_faces")) is not None:
        faces = _faces(card_faces, language, card.get("layout"))
        data["faces"] = faces
        names = [face.get("name") for face in faces]
        if "name" not in data and names and all(names):
            data["name"] = " // ".join(names)
    if (parts := _members(card, "all_parts")) is not None:
        data["related_cards"] = [_related_part(part) for part in parts]

    data.update(_additional_attributes(card, _CARD_CONSUMED))
    return ItemMagic(data)
