"""Synthetic contracts matching the Korean site's observed HTML and AJAX response."""

import asyncio
import json
from urllib.parse import parse_qs

import pytest
from scrapy import Request
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse, TextResponse

from tcg_scraper.item_pokemon import ItemPokemon
from tcg_scraper.spiders import pokemon_kr

BASE = "https://pokemoncard.co.kr"


def icon(number):
    return f'<img class="type_b" src="/images/symbol/type{number}.png">'


def detail_html(category, blocks, *, hp="", number="001/099", extras=""):
    return f"""<html><body><header>Navigation</header><div id="heaer_top">
    <img class="feature_image" src="/public-assets/cards/front.webp?w=512">
    <div class="pre_info_wrap"><img src="/images/symbol/TEST.png">
    <img src="/images/symbol/J.png"><span class="p_num">{number}
    <span id="no_wrap_by_admin">RR</span></span></div>
    <p class="illustrator">일러스트<br>Artist One<br>Artist Two</p>
    <div class="detail_wrap"><div class="header"><span class="card-hp title">테스트 카드</span>
    <span class="card-hp level">LV.42</span>{hp}</div>
    <div class="pokemon-info">카드 종류 : {category}</div>
    <div class="pokemon-abilities">{blocks}</div>{extras}
    <div class="pokemon-detail"><a class="search_href" href="/cards?s=prize">행사 경품</a></div>
    </div></div><footer>Website copyright</footer></body></html>"""


POKEMON = detail_html(
    "2진화 포켓몬 | 포켓몬 ex",
    '<div class="ability"><div class="area-parent"><span id="skill_label">특성</span>'
    '<h4><span class="skil_name">테스트 특성</span></h4></div><p>특성 설명.</p></div>'
    '<div class="ability"><div class="area-parent">'
    + icon(5)
    + icon(5)
    + '<h4><span class="skil_name">테스트 기술</span><span class="plus">30×</span></h4></div>'
    "<p>기술<!-- editorial --> 설명 "
    + icon(9)
    + '<small class="small_type_sm">(무색)</small> 에너지.</p></div>'
    '<div class="ability"><div class="area-parent"><h4><span class="skil_name">ex 룰</span>'
    "</h4></div><p>프라이즈 규칙.</p></div>",
    hp='<span class="hp_num">HP360</span>' + icon(5),
    extras='<div class="pokemon-stats"><div class="stat"><h4>약점</h4>'
    + icon(7)
    + '<span>×2</span></div><div class="stat"><h4>저항력</h4>'
    + icon(6)
    + '<span>-30</span></div><div class="stat"><h4>후퇴</h4><div class="card-energies">'
    + icon(9)
    + icon(9)
    + '</div></div></div><div class="pokemon-detail">'
    '<div class="col-xs-5"><!--No. 492-->키 : 0.4 m<br>몸무게 : 5.2 kg</div>'
    '<div class="colsit"><p>포켓몬 설명.</p><a>Pokédex navigation</a></div></div>',
)
TRAINER = detail_html(
    "아이템",
    '<div class="ability"><h4> </h4><p>아이템 효과.</p></div>'
    '<div class="ability"><h4>아이템 룰</h4><p>아이템 규칙.</p></div>',
    number="087/M-P",
)
ENERGY = detail_html(
    "특수 에너지",
    '<div class="ability"><h4></h4><p>' + icon(10) + " 포켓몬에게 붙인다.</p></div>",
)


def detail_response(body=POKEMON):
    return HtmlResponse(BASE + "/cards/detail/TEST001", body=body.encode(), encoding="utf-8")


def listing(cursor=0, ids=("TEST001", "TEST002"), **updates):
    data = {
        "status": True,
        "count": len(ids),
        "limit": cursor + 1,
        "msg": "",
        "result": {str(i): {"CardNum": card_id} for i, card_id in enumerate(ids, 1)},
    }
    data.update(updates)
    return TextResponse(BASE + "/v2/ajax2_dev2", body=json.dumps(data).encode(), encoding="utf-8")


def test_spider_is_available():
    assert hasattr(pokemon_kr, "PokemonKrSpider")


def test_pokemon_extracts_artists_images_stats_and_symbols():
    item = pokemon_kr.PokemonKrSpider().parse_detail(detail_response(), card_id="TEST001")
    assert isinstance(item, ItemPokemon)
    assert item["card_id"] == "pokemoncard.co.kr:TEST001"
    assert (item["language"], item["region"]) == ("ko", "KR")
    assert item["illustrators"] == ["Artist One", "Artist Two"]
    assert item["images"]["front"] == BASE + "/public-assets/cards/front.webp?w=512"
    assert item["number"] == "001" and item["printed_number"] == "001/099"
    assert item["set"] == {
        "code": "TEST",
        "symbol_url": BASE + "/images/symbol/TEST.png",
        "printed_total": 99,
    }
    assert item["regulation_mark"] == "J" and item["rarity"] == "RR"
    assert item["supertype"] == "Pokémon" and item["stage"] == "2진화"
    assert item["subtypes"] == ["포켓몬 ex"]
    assert item["hp"] == "360" and item["types"] == ["Psychic"]
    assert item["level"] == "LV.42"
    assert item["attacks"] == [
        {
            "name": "테스트 기술",
            "cost": ["Psychic", "Psychic"],
            "converted_energy_cost": 2,
            "damage": "30×",
            "text": "기술 설명 {Colorless} 에너지.",
        }
    ]
    assert item["abilities"] == [{"kind": "특성", "name": "테스트 특성", "text": "특성 설명."}]
    assert item["rules"] == ["프라이즈 규칙."]
    assert item["weaknesses"] == [{"type": "Darkness", "value": "×2"}]
    assert item["resistances"] == [{"type": "Fighting", "value": "-30"}]
    assert item["retreat_cost"] == ["Colorless", "Colorless"]
    assert item["converted_retreat_cost"] == 2
    assert item["height"] == "0.4 m" and item["weight"] == "5.2 kg"
    assert item["pokemon"][0]["national_pokedex_number"] == 492
    assert item["flavor_text"] == "포켓몬 설명."
    assert item["additional_attributes"]["related_links"][0]["name"] == "행사 경품"
    for unwanted in ("Navigation", "navigation", "editorial", "copyright"):
        assert unwanted not in item["raw_text"]
    assert "copyright" not in item
    json.dumps(dict(item), ensure_ascii=False)


@pytest.mark.parametrize(
    "html,supertype,field,text",
    [
        (TRAINER, "Trainer", "trainer_text", "아이템 효과.\n아이템 규칙."),
        (ENERGY, "Energy", "energy_text", "{Dragon} 포켓몬에게 붙인다."),
    ],
)
def test_trainer_and_energy(html, supertype, field, text):
    item = pokemon_kr.PokemonKrSpider().parse_detail(detail_response(html), card_id="TEST001")
    assert item["supertype"] == supertype and item[field] == text
    assert "hp" not in item and "attacks" not in item and "provided_energy" not in item
    if supertype == "Trainer":
        assert item["number"] == "087" and item["printed_number"] == "087/M-P"
        assert "printed_total" not in item["set"]
        assert item["trainer_type"] == "아이템"
    else:
        assert item["energy_type"] == "특수 에너지"


def test_missing_fields_and_zero_retreat_are_distinct():
    body = detail_html(
        "기본 포켓몬",
        "",
        hp='<span class="hp_num">HP50</span>',
        number="",
        extras='<div class="pokemon-stats"><div class="stat">'
        '<h4>후퇴</h4><div class="card-energies"></div></div></div>',
    )
    body = body.replace('<p class="illustrator">일러스트<br>Artist One<br>Artist Two</p>', "")
    item = pokemon_kr.PokemonKrSpider().parse_detail(detail_response(body), card_id="TEST001")
    assert item["retreat_cost"] == [] and item["converted_retreat_cost"] == 0
    assert "illustrators" not in item and "number" not in item and "flavor_text" not in item


def test_unknown_labels_ancient_traits_and_free_attacks():
    blocks = (
        '<div class="ability"><span id="skill_label">고대능력</span>'
        '<h4><span class="skil_name">고대 이름</span></h4><p>고대 설명.</p></div>'
        '<div class="ability"><span id="skill_label">새로운 힘</span>'
        '<h4><span class="skil_name">미지</span></h4><p>미지 설명.</p></div>'
        '<div class="ability"><div class="area-parent">'
        '<h4><span class="skil_name">무료 기술</span></h4></div><p>효과.</p></div>'
    )
    item = pokemon_kr.PokemonKrSpider().parse_detail(
        detail_response(detail_html("기본 포켓몬", blocks, hp='<span class="hp_num">HP50</span>')),
        card_id="TEST001",
    )
    assert item["ancient_traits"][0]["name"] == "고대 이름"
    assert item["effects"][0]["kind"] == "새로운 힘"
    assert item["attacks"][0]["cost"] == []
    assert item["attacks"][0]["converted_energy_cost"] == 0
    assert "damage" not in item["attacks"][0]


def test_search_button_and_load_more_are_post_requests_with_persistent_query():
    spider = pokemon_kr.PokemonKrSpider(search_text="피카츄", search_params="cardname")

    async def first():
        return [request async for request in spider.start()]

    request = asyncio.run(first())[0]
    assert request.method == "POST" and request.url == BASE + "/v2/ajax2_dev2"
    assert request.headers["X-Requested-With"] == b"XMLHttpRequest"
    assert parse_qs(request.body.decode())["limit"] == ["0"]
    results = list(spider.parse(listing(), cursor=0))
    assert [r.url for r in results[:2]] == [
        BASE + "/cards/detail/TEST001",
        BASE + "/cards/detail/TEST002",
    ]
    next_request = results[-1]
    assert parse_qs(next_request.body.decode()) == {
        "action": ["search_text_cards"],
        "search_text": ["피카츄"],
        "search_params": ["cardname"],
        "limit": ["1"],
    }
    assert all(isinstance(r, Request) and not r.meta.get("playwright") for r in results)
    last = list(spider.parse(listing(cursor=1, ids=("TEST002", "TEST003")), cursor=1))
    assert len(last) == 2 and "/TEST003" in last[0].url
    assert list(spider.parse(listing(cursor=2, ids=(), result=[]), cursor=2)) == []


def test_array_results_and_limits():
    spider = pokemon_kr.PokemonKrSpider(max_pages=1, start_page=2)
    results = list(
        spider.parse(
            listing(cursor=1, result=[{"CardNum": "TEST001"}, {"CardNum": "TEST002"}]), cursor=1
        )
    )
    assert len(results) == 2
    spider = pokemon_kr.PokemonKrSpider(max_cards=1)
    assert len(list(spider.parse(listing(), cursor=0))) == 1


def test_job_state_preserves_deduplication_and_budget():
    first = pokemon_kr.PokemonKrSpider(max_cards=3)
    list(first.parse(listing(), cursor=0))
    resumed = pokemon_kr.PokemonKrSpider(max_cards=3)
    resumed.state = first.state
    result = list(resumed.parse(listing(cursor=1, ids=("TEST002", "TEST003", "TEST004")), cursor=1))
    assert len(result) == 1 and result[0].url.endswith("/TEST003")


@pytest.mark.parametrize(
    "updates",
    [
        {"status": False},
        {"count": 3},
        {"limit": 0},
        {"limit": 5},
        {"result": None},
        {"result": [{"CardNum": "../escape"}]},
        {"count": 0},
        {"status": "true"},
    ],
)
def test_invalid_catalogue_stops(updates):
    with pytest.raises(CloseSpider) as error:
        list(pokemon_kr.PokemonKrSpider().parse(listing(**updates), cursor=0))
    assert error.value.reason == "invalid_catalogue"


def test_repeated_batch_stops_instead_of_looping():
    spider = pokemon_kr.PokemonKrSpider()
    list(spider.parse(listing(), cursor=0))
    with pytest.raises(CloseSpider) as error:
        list(spider.parse(listing(cursor=1), cursor=1))
    assert error.value.reason == "invalid_catalogue"


def test_invalid_detail_cannot_export_an_empty_item():
    with pytest.raises(CloseSpider) as error:
        pokemon_kr.PokemonKrSpider().parse_detail(
            detail_response("<p>접근불가</p>"), card_id="TEST001"
        )
    assert error.value.reason == "invalid_card_detail"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_pages": -1},
        {"max_cards": "no"},
        {"start_page": 0},
        {"start_url": "file:///tmp"},
        {"search_params": "unknown"},
    ],
)
def test_invalid_arguments(kwargs):
    with pytest.raises(ValueError):
        pokemon_kr.PokemonKrSpider(**kwargs)


@pytest.mark.parametrize(
    "result,count",
    [
        ({}, 0),
        ({"error": {"CardNum": "TEST001"}}, 1),
        ({"1": {"CardNum": None}}, 1),
        ({"1": {"CardNum": False}}, 1),
        ({"1": {"CardNum": 42}}, 1),
        ({"1": {"CardNum": "TEST001"}, "3": {"CardNum": "TEST002"}}, 2),
    ],
)
def test_schema_errors_cannot_become_success_or_fake_detail_urls(result, count):
    with pytest.raises(CloseSpider) as error:
        list(pokemon_kr.PokemonKrSpider().parse(listing(result=result, count=count), cursor=0))
    assert error.value.reason == "invalid_catalogue"


@pytest.mark.parametrize(
    "category,subtype", [("아이템 | 미래", "미래"), ("특수 에너지 | 퓨전", "퓨전")]
)
def test_non_pokemon_subtypes_are_retained(category, subtype):
    response = detail_response(detail_html(category, '<div class="ability"><p>효과.</p></div>'))
    item = pokemon_kr.PokemonKrSpider().parse_detail(response, card_id="TEST001")
    assert item["subtypes"] == [subtype]


def test_older_visible_pokedex_species_is_preserved_without_a_comment():
    html = POKEMON.replace("<!--No. 492-->", "No. 492 감사포켓몬<br>")
    item = pokemon_kr.PokemonKrSpider().parse_detail(detail_response(html), card_id="TEST001")
    assert item["species"] == "감사포켓몬"
    assert item["pokemon"] == [{"national_pokedex_number": 492}]
    assert "감사포켓몬" in item["raw_text"]


def test_empty_card_category_is_an_explicit_detail_error():
    with pytest.raises(CloseSpider) as error:
        pokemon_kr.PokemonKrSpider().parse_detail(
            detail_response(detail_html("", "")), card_id="TEST001"
        )
    assert error.value.reason == "invalid_card_detail"
