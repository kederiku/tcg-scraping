"""Synthetic contracts based on the public Indonesian TCG Collector HTML/XML."""

import asyncio
import json

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse, XmlResponse

from tcg_scraper.item_pokemon import ItemPokemon
from tcg_scraper.spiders.pokemon_id import PokemonIdSpider

BASE = "https://www.tcgcollector.com"
STATIC = "https://static.tcgcollector.com"
INDEX = STATIC + "/sitemaps/sitemap.xml"
MAP1 = STATIC + "/sitemaps/sitemap-cards-id1.xml"
MAP2 = STATIC + "/sitemaps/sitemap-cards-id2.xml"


def icon(name):
    return f'<img class="energy-type-symbol" alt="{name}" src="/icons/{name}.png">'


def footer(label, value):
    return (
        '<div class="card-info-footer-item"><div class="card-info-footer-item-title">'
        f"{label}</div>{value}</div>"
    )


def detail_html(card_id="101", category="Pokémon-GX", body="", stats=True, region=4):
    state = {
        "tcgRegionDtos": [{"id": 4, "slug": "id"}],
        "cardIdToTcgRegionIdMap": {card_id: region},
        "cardIdToCardVariantTypeIdsMap": {card_id: [363, 364]},
        "idToCardVariantTypeDtoMap": {
            "363": {"id": 363, "name": "Normal"},
            "364": {"id": 364, "name": "Normal Holo"},
        },
        "pricing": {"price": 99},
    }
    metadata = footer(
        "Expansion",
        '<a href="/sets/100/test"><span id="card-info-footer-item-text-expansion-name">'
        'Test Set</span><span id="card-info-footer-item-text-expansion-code">T1</span></a>'
        '<img class="set-symbol" src="/set.svg">',
    )
    metadata += footer("Card number", '<span class="card-info-footer-item-text">001/070</span>')
    metadata += footer(
        "Rarity", '<img alt="UR"><a class="card-info-footer-item-text">Ultra Rare (UR)</a>'
    )
    metadata += footer(
        "Illustrators",
        '<span class="card-info-footer-item-text"><a>Artist One</a></span>'
        '<span class="card-info-footer-item-text"><a>Artist Two</a></span>',
    )
    metadata += footer("Regulation mark", '<a class="card-info-footer-item-text">J</a>')
    metadata += footer(
        "Additional card types", '<a class="card-info-footer-item-text">Full Art Pokémon</a>'
    )
    pokemon_header = ""
    if stats:
        pokemon_header = (
            '<span id="card-hit-points-value">230</span><a id="card-energy-types">'
            + icon("Water")
            + '</a><div id="card-evolution-status"><a href="/cards/intl?pokemonStages=5">'
            'Stage 2</a> — Evolves from <a href="/cards/intl?nameSearch=Test">Test</a></div>'
        )
        metadata += footer(
            "Weakness",
            '<div class="card-info-footer-item-entry">'
            + icon("Grass")
            + '<span class="card-info-footer-item-entry-text">×2</span></div>',
        )
        metadata += footer("Resistance", '<span class="card-info-footer-item-text">—</span>')
        metadata += footer("Retreat Cost", '<a class="card-info-footer-item-entries"></a>')
        metadata += footer("Pokédex", '<a href="/pokedex/658/greninja/intl">#0658</a>')
    return f"""<html lang="en"><body><nav>Navigation</nav>
    <div id="card-image-container"><img src="/front.webp"
    srcset="/small.webp 320w, /large.webp 868w, /medium.webp 640w"><div>Price $99</div></div>
    <div id="card-info"><div id="card-info-header"><h1 id="card-info-title">Test-GX</h1>
    <div id="card-type-containers"><span class="card-type-container">{category}</span></div>
    {pokemon_header}</div>
    <div id="card-info-body">{body}</div><div id="card-info-footer">{metadata}</div></div>
    <script>window.tcgcollector = {{appState: {json.dumps(state)}, extra: true}};</script>
    <footer>Website copyright</footer></body></html>"""


POKEMON_BODY = (
    '<div class="card-effect"><a class="card-effect-badge">Ability</a>'
    '<div class="card-effect-name">Test ability</div>'
    '<p class="card-effect-description">Ability text.</p></div>'
    '<div class="card-attack"><div class="card-attack-energies">'
    + icon("Water")
    + icon("Colorless")
    + icon("Colorless")
    + '</div><div class="card-attack-name">Attack</div><div class="card-attack-damage">30×</div>'
    '<p class="card-attack-description">Discard '
    + icon("Water")
    + ' Energy.</p></div><div id="card-rules"><div class="card-rule">'
    '<div class="card-rule-badge">Card rule</div>'
    '<p class="card-rule-description">Take 2 Prize cards.</p></div></div>'
)


def detail(body=None, card_id="101"):
    return HtmlResponse(
        BASE + f"/cards/{card_id}/test",
        body=(body or detail_html(body=POKEMON_BODY)).encode(),
        encoding="utf-8",
    )


def sitemap(urls, *, index=False, url=MAP1):
    root, child = ("sitemapindex", "sitemap") if index else ("urlset", "url")
    body = (
        f'<{root} xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<{child}><loc>{u}</loc></{child}>" for u in urls)
        + f"</{root}>"
    )
    return XmlResponse(url, body=body.encode(), encoding="utf-8")


def test_discovers_only_indonesian_card_sitemaps_in_numeric_order():
    spider = PokemonIdSpider()

    async def start():
        return [r async for r in spider.start()]

    assert asyncio.run(start())[0].url == INDEX
    requests = list(
        spider.parse_index(
            sitemap(
                [
                    MAP2,
                    STATIC + "/sitemaps/sitemap-cards-jp1.xml",
                    MAP1,
                    STATIC + "/sitemaps/sitemap-set-card-list-id1.xml",
                    MAP1,
                ],
                index=True,
                url=INDEX,
            )
        )
    )
    assert len(requests) == 1 and requests[0].url == MAP1
    assert requests[0].cb_kwargs == {"remaining": [MAP2]}


def test_sitemaps_deduplicate_cards_and_limit_network_budget_across_resume():
    spider = PokemonIdSpider(max_cards="2")
    reqs = list(
        spider.parse_sitemap(
            sitemap([BASE + "/cards/101/test", BASE + "/cards/101/alternate"]), remaining=[MAP2]
        )
    )
    assert [r.url for r in reqs] == [BASE + "/cards/101/test", MAP2]
    resumed = PokemonIdSpider(max_cards="2")
    resumed.state = spider.state
    reqs = list(
        resumed.parse_sitemap(
            sitemap(
                [BASE + "/cards/101/test", BASE + "/cards/102/test", BASE + "/cards/103/test"],
                url=MAP2,
            ),
            remaining=[],
        )
    )
    assert [r.cb_kwargs for r in reqs] == [{"card_id": "102"}]


def test_max_sitemaps_truncates_the_index():
    req = list(PokemonIdSpider(max_sitemaps="1").parse_index(sitemap([MAP1, MAP2], index=True)))[0]
    assert req.cb_kwargs["remaining"] == []


@pytest.mark.parametrize(
    "url",
    [
        BASE + "/cards/id?page=2",
        BASE + "/api/cards",
        "https://example.org/cards/101/test",
        BASE + "/cards/101/test?page=2",
        BASE + "/cards/101/test#fragment",
    ],
)
def test_unexpected_sitemap_links_fail_before_scheduling(url):
    with pytest.raises(CloseSpider) as error:
        list(
            PokemonIdSpider().parse_sitemap(sitemap([BASE + "/cards/101/test", url]), remaining=[])
        )
    assert error.value.reason == "invalid_catalogue"


@pytest.mark.parametrize("body", ["<html>Challenge</html>", "<urlset><url>", "<urlset/>"])
def test_broken_sitemaps_fail_closed(body):
    with pytest.raises(CloseSpider) as error:
        list(PokemonIdSpider().parse_sitemap(XmlResponse(MAP1, body=body.encode()), remaining=[]))
    assert error.value.reason == "invalid_catalogue"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_cards": "-1"},
        {"max_sitemaps": "2.5"},
        {"max_pages": "1"},
        {"start_url": "file:///x"},
        {"card_base_url": "https://user:pass@example.org"},
    ],
)
def test_bad_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        PokemonIdSpider(**kwargs)


def test_pokemon_fields_include_artists_real_images_symbols_and_provenance():
    item = PokemonIdSpider().parse_detail(detail(), card_id="101")
    assert isinstance(item, ItemPokemon)
    assert item["card_id"] == "tcgcollector.com:101"
    assert (item["language"], item["region"]) == ("id", "ID")
    assert item["additional_attributes"]["text_language"] == "en"
    assert item["images"] == {"front": BASE + "/front.webp", "large": BASE + "/large.webp"}
    assert item["illustrators"] == ["Artist One", "Artist Two"]
    assert item["set"] == {
        "id": "100",
        "name": "Test Set",
        "code": "T1",
        "symbol_url": BASE + "/set.svg",
        "printed_total": 70,
    }
    assert item["number"] == "001" and item["printed_number"] == "001/070"
    assert item["rarity"] == "Ultra Rare (UR)" and item["regulation_mark"] == "J"
    assert item["supertype"] == "Pokémon"
    assert item["subtypes"] == ["Pokémon-GX", "Full Art Pokémon"]
    assert item["hp"] == "230" and item["types"] == ["Water"]
    assert item["stage"] == "Stage 2" and item["evolves_from"] == "Test"
    assert item["attacks"] == [
        {
            "name": "Attack",
            "cost": ["Water", "Colorless", "Colorless"],
            "converted_energy_cost": 3,
            "damage": "30×",
            "text": "Discard {Water} Energy.",
        }
    ]
    assert item["abilities"] == [
        {"kind": "Ability", "name": "Test ability", "text": "Ability text."}
    ]
    assert item["rules"] == ["Take 2 Prize cards."]
    assert item["weaknesses"] == [{"type": "Grass", "value": "×2"}]
    assert item["resistances"] == []
    assert item["retreat_cost"] == [] and item["converted_retreat_cost"] == 0
    assert item["pokemon"] == [{"national_pokedex_number": 658}]
    assert item["additional_attributes"]["available_variants"] == [
        {"id": "363", "name": "Normal"},
        {"id": "364", "name": "Normal Holo"},
    ]
    assert "printing" not in item and "flavor_text" not in item
    for unwanted in ("Navigation", "Website copyright", "Price", "pricing", "appState"):
        assert unwanted not in item["raw_text"]
    json.dumps(dict(item))


@pytest.mark.parametrize(
    "category,field", [("Item", "trainer_text"), ("Special Energy", "energy_text")]
)
def test_non_pokemon_effects_and_rules(category, field):
    body = (
        '<p id="card-description">Apply this effect.</p><div class="card-rule">'
        '<p class="card-rule-description">Special rule.</p></div>'
    )
    item = PokemonIdSpider().parse_detail(
        detail(detail_html(category=category, body=body, stats=False)), card_id="101"
    )
    assert item[field] == "Apply this effect.\nSpecial rule."
    assert item["trainer_type" if field == "trainer_text" else "energy_type"] == category
    assert "hp" not in item and "retreat_cost" not in item and "flavor_text" not in item


def test_placeholder_back_is_never_exported_as_front_or_large():
    body = (
        detail_html()
        .replace("/front.webp", "/build/images/default-card-image-640x892.abc.png")
        .replace("/large.webp", "/build/images/default-card-image-868x1200.def.png")
    )
    # A placeholder src means the entire picture is unavailable, including srcset.
    item = PokemonIdSpider().parse_detail(detail(body), card_id="101")
    assert "images" not in item
    assert item["additional_attributes"]["image_status"] == "missing"


def test_unknown_effects_and_free_attack_are_preserved():
    body = (
        '<div class="card-effect"><span class="card-effect-badge">Future mechanic</span>'
        '<div class="card-effect-name">Unusual</div>'
        '<p class="card-effect-description">Keep me.</p></div>'
        '<div class="card-attack"><div class="card-attack-energies">'
        + icon("No Energy")
        + '</div><div class="card-attack-name">Free attack</div></div>'
    )
    item = PokemonIdSpider().parse_detail(detail(detail_html(body=body)), card_id="101")
    assert item["effects"][0]["kind"] == "Future mechanic"
    assert "Keep me." in item["raw_text"]
    assert item["attacks"][0]["cost"] == [] and item["attacks"][0]["converted_energy_cost"] == 0


def test_provided_energy_uses_the_shared_item_schema():
    body = detail_html(category="Basic Energy", stats=False).replace(
        '<div id="card-info-footer">',
        '<div id="card-info-footer">' + footer("Provides", icon("Water")),
    )
    item = PokemonIdSpider().parse_detail(detail(body), card_id="101")
    assert item["provided_energy"] == [{"types": ["Water"]}]


def test_text_blocks_use_shared_titles_positions_and_stable_kinds():
    item = PokemonIdSpider().parse_detail(detail(), card_id="101")
    assert item["text_blocks"] == [
        {"kind": "effect", "title": "Test ability", "text": "Ability text.", "position": 0},
        {"kind": "attack", "title": "Attack", "text": "Discard {Water} Energy.", "position": 1},
        {"kind": "rule", "title": "Card rule", "text": "Take 2 Prize cards.", "position": 2},
    ]


def test_free_attack_has_header_but_no_energy_container_as_observed_on_79650():
    body = '<div class="card-attack"><div class="card-attack-header">'
    body += '<div class="card-attack-header-text"><div class="card-attack-name">'
    body += 'Call for the Boss</div></div></div><p class="card-attack-description">'
    body += "Search your deck.</p></div>"
    body += '<div class="card-attack"><div class="card-attack-energies">'
    body += icon("Colorless") + icon("Colorless")
    body += '</div><div class="card-attack-name">Gnaw</div>'
    body += '<div class="card-attack-damage">20</div></div>'
    item = PokemonIdSpider().parse_detail(detail(detail_html(body=body)), card_id="101")
    assert item["attacks"][0]["cost"] == []
    assert item["attacks"][0]["converted_energy_cost"] == 0
    assert item["attacks"][1]["cost"] == ["Colorless", "Colorless"]
    assert item["attacks"][1]["converted_energy_cost"] == 2


@pytest.mark.parametrize(
    "energy",
    [
        "",
        '<div class="card-attack-energies">'
        '<img class="energy-type-symbol" src="/unknown.png"></div>',
    ],
)
def test_unknown_attack_cost_is_not_reported_as_free(energy):
    body = (
        '<div class="card-attack">'
        + energy
        + '<div class="card-attack-name">Incomplete</div></div>'
    )
    item = PokemonIdSpider().parse_detail(detail(detail_html(body=body)), card_id="101")
    assert "cost" not in item["attacks"][0]
    assert "converted_energy_cost" not in item["attacks"][0]


@pytest.mark.parametrize(
    "body",
    [
        "<html>Challenge</html>",
        detail_html(region=2),
        detail_html(card_id="999"),
        detail_html().replace("appState:", "noState:"),
    ],
)
def test_bad_detail_or_wrong_region_is_not_mislabeled(body):
    with pytest.raises(CloseSpider) as error:
        PokemonIdSpider().parse_detail(detail(body), card_id="101")
    assert error.value.reason == "invalid_card_detail"
