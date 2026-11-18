"""Contracts for the public catalogue, using synthetic HTML with its observed layout."""

import asyncio
import json
from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy import Request
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse, TextResponse

from tcg_scraper.item_pokemon import ItemPokemon
from tcg_scraper.spiders import pokemon_jp

BASE = "https://www.pokemon-card.com"


def detail_html(content, *, name="テストカード", number="001 / 099", dex=""):
    return f"""<html><body><header>Navigation</header><section class="Section">
    <h1 class="Heading1">{name}</h1><div class="Box"><div class="LeftBox">
    <img class="fit" src="/assets/images/card_images/large/TEST/card.jpg">
    <div class="subtext"><img class="img-regulation" src="/set.gif" alt="TEST">{number}</div>
    {dex}<div class="author"><h4>イラストレーター</h4>
    <a>Artist One</a><a>Artist Two</a></div></div>
    <div class="RightBox"><div class="RightBox-inner">{content}</div></div></div></section>
    <section class="SubSection"><a class="Link" href="/products/test.html">テストセット</a>
    </section>
    <footer>Website copyright, not card copyright</footer></body></html>"""


POKEMON = detail_html(
    """<div class="TopInfo"><span class="type">1 進化</span><span class="hp-num">120</span>
    <span class="icon-water icon"></span><span class="icon-steel icon"></span></div>
    <h2>特性</h2><h4>テスト特性</h4><p>特性の説明。</p>
    <h2>ワザ</h2><h4><span class="icon-water icon"></span><span class="icon-water icon"></span>
    テスト技<span class="f_right Text-fjalla">30×</span></h4><p>技の説明。</p>
    <h4><span class="icon-void icon"></span>無料の技</h4><p>ダメージなし。</p>
    <h2>特別なルール</h2><p></p><p>特別なルールの説明。</p>
    <table><tr><th>弱点</th><th>抵抗力</th><th>にげる</th></tr><tr>
    <td><span class="icon-electric icon"></span>×2</td>
    <td><span class="icon-fighting icon"></span>-30</td>
    <td class="escape"><span class="icon-none icon"></span></td></tr></table>
    <h2>進化</h2><div class="evolution"><a>Navigation évolution</a></div>""",
    dex='<div class="card"><h4>No.158 おおあごポケモン</h4>'
    "<p>高さ：0.6 m 重さ：9.5 kg</p><hr><p>ポケモンの説明。</p></div>",
)
TRAINER = detail_html('<div class="TopInfo"></div><h2>グッズ</h2><p>効果。</p><p>使用ルール。</p>')
ENERGY = detail_html(
    '<div class="TopInfo"></div><h2>特殊エネルギー</h2>'
    '<p><span class="icon-dragon icon"></span>ポケモンにつける。</p>',
    number="XY-P",
)


def detail_response(body=POKEMON):
    return HtmlResponse(
        BASE + "/card-search/details.php/card/123/regu/all", body=body.encode(), encoding="utf-8"
    )


def listing_response(page=1, max_page=2, ids=("123", "124"), **updates):
    payload = {
        "result": 1,
        "thisPage": page,
        "maxPage": max_page,
        "hitCnt": 3,
        "regulation": "all",
        "cardList": [{"cardID": value} for value in ids],
    }
    payload.update(updates)
    return TextResponse(BASE + "/card-search/resultAPI.php", body=json.dumps(payload).encode())


def test_spider_is_available():
    assert hasattr(pokemon_jp, "PokemonJpSpider")


def test_pokemon_fields_keep_symbols_printed_numbers_and_artists():
    item = pokemon_jp.PokemonJpSpider().parse_detail(detail_response(), card_id="123")
    assert isinstance(item, ItemPokemon)
    assert item["card_id"] == "pokemon-card.com:123"
    assert item["language"] == "ja" and item["region"] == "JP"
    assert item["illustrators"] == ["Artist One", "Artist Two"]
    assert item["images"]["front"] == BASE + "/assets/images/card_images/large/TEST/card.jpg"
    assert item["number"] == "001" and item["printed_number"] == "001/099"
    assert item["set"] == {
        "code": "TEST",
        "symbol_url": BASE + "/set.gif",
        "printed_total": 99,
    }
    assert "regulation_mark" not in item and "copyright" not in item
    assert item["supertype"] == "Pokémon" and item["stage"] == "1 進化"
    assert item["hp"] == "120" and item["types"] == ["Water", "Metal"]
    assert item["attacks"][0] == {
        "name": "テスト技",
        "cost": ["Water", "Water"],
        "converted_energy_cost": 2,
        "damage": "30×",
        "text": "技の説明。",
    }
    assert item["attacks"][1]["cost"] == []
    assert item["attacks"][1]["converted_energy_cost"] == 0
    assert "damage" not in item["attacks"][1]
    assert item["abilities"] == [{"kind": "特性", "name": "テスト特性", "text": "特性の説明。"}]
    assert item["rules"] == ["特別なルールの説明。"]
    assert item["weaknesses"] == [{"type": "Lightning", "value": "×2"}]
    assert item["resistances"] == [{"type": "Fighting", "value": "-30"}]
    assert item["retreat_cost"] == ["Colorless"] and item["converted_retreat_cost"] == 1
    assert item["pokemon"][0]["national_pokedex_number"] == 158
    assert item["height"] == "0.6 m" and item["weight"] == "9.5 kg"
    assert item["flavor_text"] == "ポケモンの説明。"
    assert "Navigation" not in item["raw_text"] and "copyright" not in item["raw_text"]
    json.dumps(dict(item), ensure_ascii=False)


@pytest.mark.parametrize(
    ("html", "supertype", "field", "expected"),
    [
        (TRAINER, "Trainer", "trainer_text", "効果。\n使用ルール。"),
        (ENERGY, "Energy", "energy_text", "{Dragon}ポケモンにつける。"),
    ],
)
def test_non_pokemon_cards(html, supertype, field, expected):
    item = pokemon_jp.PokemonJpSpider().parse_detail(detail_response(html), card_id="123")
    assert item["supertype"] == supertype
    assert item[field] == expected
    assert "hp" not in item and "attacks" not in item
    if supertype == "Energy":
        assert item["energy_type"] == "特殊エネルギー"
        assert item["number"] == "XY-P"
        assert "provided_energy" not in item  # Conditions cannot be guessed from an icon.
    else:
        assert item["trainer_type"] == "グッズ"


def test_unknown_mechanics_and_ancient_traits_are_preserved():
    html = detail_html(
        "<h2>古代能力</h2><h4>古代の名</h4><p>説明1</p>"
        "<h2>新しい仕組み</h2><h4>未知の名</h4><p>説明2</p>"
    )
    item = pokemon_jp.PokemonJpSpider().parse_detail(detail_response(html), card_id="123")
    assert item["ancient_traits"][0]["name"] == "古代の名"
    assert item["effects"][0]["text"] == "説明2"
    assert any(block["text"] == "説明2" for block in item["text_blocks"])


def test_missing_optional_fields_stay_unknown():
    html = detail_html("<h2>基本エネルギー</h2>", number="").replace(
        "<a>Artist One</a><a>Artist Two</a>", ""
    )
    item = pokemon_jp.PokemonJpSpider().parse_detail(detail_response(html), card_id="123")
    assert item["supertype"] == "Energy"
    for field in ("number", "illustrators", "rarity", "retreat_cost", "energy_text"):
        assert field not in item


def test_start_and_pagination_preserve_filters_and_follow_detail_links():
    spider = pokemon_jp.PokemonJpSpider(
        start_url=BASE + "/card-search/index.php?"
        "keyword=%E3%83%94%E3%82%AB&regulation_sidebar_form=all"
    )

    async def first():
        return [request async for request in spider.start()]

    initial = asyncio.run(first())[0]
    assert parse_qs(urlsplit(initial.url).query)["page"] == ["1"]
    requests = list(spider.parse(listing_response(), page_number=1))
    assert all(isinstance(request, Request) for request in requests)
    details = [request for request in requests if "/details.php/" in request.url]
    assert [request.url for request in details] == [
        BASE + f"/card-search/details.php/card/{value}/regu/all" for value in ("123", "124")
    ]
    next_request = requests[-1]
    assert parse_qs(urlsplit(next_request.url).query) == {
        "keyword": ["ピカ"],
        "regulation_sidebar_form": ["all"],
        "page": ["2"],
    }
    last = list(spider.parse(listing_response(page=2, ids=("124", "125")), page_number=2))
    assert len(last) == 1 and "/125/" in last[0].url
    assert all(not request.meta.get("playwright") for request in requests)


def test_request_limits_and_start_page():
    spider = pokemon_jp.PokemonJpSpider(max_pages=1, start_page=2)
    assert len(list(spider.parse(listing_response(page=2, max_page=3), page_number=2))) == 2
    spider = pokemon_jp.PokemonJpSpider(max_cards=1)
    requests = list(spider.parse(listing_response(), page_number=1))
    assert len(requests) == 1 and "/123/" in requests[0].url


@pytest.mark.parametrize(
    "updates",
    [
        {"result": 0},
        {"thisPage": 1},
        {"maxPage": 1},
        {"cardList": []},
        {"cardList": [{"cardID": "../bad"}]},
        {"cardList": "invalid"},
    ],
)
def test_invalid_or_repeated_pagination_stops(updates):
    spider = pokemon_jp.PokemonJpSpider()
    with pytest.raises(CloseSpider) as error:
        list(spider.parse(listing_response(page=2, max_page=3, **updates), page_number=2))
    assert error.value.reason == "invalid_catalogue"


def test_empty_search_is_a_valid_completion():
    assert (
        list(
            pokemon_jp.PokemonJpSpider().parse(
                listing_response(max_page=0, ids=(), hitCnt=0), page_number=1
            )
        )
        == []
    )


def test_invalid_detail_does_not_export_an_empty_item():
    with pytest.raises(CloseSpider) as error:
        pokemon_jp.PokemonJpSpider().parse_detail(
            detail_response("<h1>Captcha</h1>"), card_id="123"
        )
    assert error.value.reason == "invalid_card_detail"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_pages": -1},
        {"max_cards": "oops"},
        {"start_page": 0},
        {"start_url": "file:///tmp/x"},
    ],
)
def test_invalid_arguments(kwargs):
    with pytest.raises(ValueError):
        pokemon_jp.PokemonJpSpider(**kwargs)


@pytest.mark.parametrize("last_ids,total", [(("123", "124"), 3), (("125",), 4)])
def test_repeated_or_truncated_last_page_cannot_report_completion(last_ids, total):
    spider = pokemon_jp.PokemonJpSpider()
    list(spider.parse(listing_response(hitCnt=total), page_number=1))
    with pytest.raises(CloseSpider) as error:
        list(spider.parse(listing_response(page=2, ids=last_ids, hitCnt=total), page_number=2))
    assert error.value.reason == "invalid_catalogue"


def test_server_range_must_match_returned_cards():
    with pytest.raises(CloseSpider) as error:
        list(
            pokemon_jp.PokemonJpSpider().parse(
                listing_response(cardStart=1, cardEnd=3), page_number=1
            )
        )
    assert error.value.reason == "invalid_catalogue"


def test_job_state_keeps_card_budget_across_resume():
    first = pokemon_jp.PokemonJpSpider(max_cards=3)
    list(first.parse(listing_response(hitCnt=4), page_number=1))
    resumed = pokemon_jp.PokemonJpSpider(max_cards=3)
    resumed.state = first.state
    requests = list(
        resumed.parse(listing_response(page=2, ids=("125", "126"), hitCnt=4), page_number=2)
    )
    assert len(requests) == 1 and "/125/" in requests[0].url


def test_job_state_keeps_coverage_and_deduplication_across_resume():
    first = pokemon_jp.PokemonJpSpider()
    list(first.parse(listing_response(), page_number=1))
    resumed = pokemon_jp.PokemonJpSpider()
    resumed.state = first.state
    requests = list(resumed.parse(listing_response(page=2, ids=("124", "125")), page_number=2))
    assert len(requests) == 1 and "/125/" in requests[0].url


def test_promotion_source_is_not_an_extension_name():
    html = ENERGY.replace("/products/test.html", "/card-search/index.php?promotion=event")
    item = pokemon_jp.PokemonJpSpider().parse_detail(detail_response(html), card_id="123")
    assert "name" not in item["set"]
    assert item["additional_attributes"]["related_links"][0]["name"] == "テストセット"


def test_html_comments_never_lose_a_card_or_leak_into_its_text():
    html = TRAINER.replace("効果。", "効果<!-- editorial -->の説明。")
    item = pokemon_jp.PokemonJpSpider().parse_detail(detail_response(html), card_id="123")
    assert item["trainer_text"] == "効果の説明。\n使用ルール。"
    assert "editorial" not in item["raw_text"]
