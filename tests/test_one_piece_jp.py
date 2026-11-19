from datetime import date

import pytest
from scrapy.crawler import Crawler
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse
from scrapy.statscollectors import DummyStatsCollector

from tcg_scraper.spiders.one_piece_jp import OnePieceJpSpider

BASE = "https://www.onepiece-cardgame.com"


def page(html, path):
    return HtmlResponse(BASE + path, body=html.encode(), encoding="utf-8")


@pytest.fixture
def spider():
    spider = OnePieceJpSpider()
    spider.today = date(2026, 11, 19)
    crawler = Crawler(OnePieceJpSpider)
    crawler.stats = DummyStatsCollector(crawler)
    spider.crawler = crawler
    return spider


def test_release_calendar_then_all_series_with_reprints(spider):
    calendar = page(
        '<a class="linkListColItem" href="/products/op01.html">'
        '<h4 class="linkListColTitle">ROMANCE DAWN【OP-01】</h4>'
        '<p class="linkListColDate"><span class="head">発売日</span>'
        '<time datetime="2022-07-22"></time></p></a>'
        '<a class="linkListColItem" href="/products/op18.html">'
        '<h4 class="linkListColTitle">神の支配【OP-18】</h4>'
        '<p class="linkListColDate"><span class="head">発売日</span>'
        '<time datetime="2026-11-21"></time></p></a>'
        '<a class="pagerColNext disable" href="?page=1"></a>',
        "/products/",
    )
    (index,) = spider.parse_products(calendar)
    catalogue = page(
        '<select id="series"><option value="">指定なし</option>'
        '<option value="550118" selected>神の支配【OP-18】</option>'
        '<option value="550101">パック &lt;br class="spInline"&gt;ROMANCE DAWN【OP-01】</option>'
        '<option value="550901">プロモーションカード</option></select>',
        "/cardlist/?series=550118",
    )
    requests = list(index.callback(catalogue))
    assert [r.cb_kwargs["series_id"] for r in requests] == ["550101", "550901"]
    assert all("reprintsFlag=off" in r.url and "search=true" in r.url for r in requests)
    assert requests[0].cb_kwargs["series_name"] == "パック ROMANCE DAWN【OP-01】"


def test_next_calendar_page_is_followed_before_catalogue(spider):
    html = (
        '<a class="linkListColItem" href="/products/x"><h4 class="linkListColTitle">X</h4></a>'
        '<a class="pagerColNext" href="?page=2"></a>'
    )
    (request,) = spider.parse_products(page(html, "/products/"))
    assert request.url == BASE + "/products/?page=2"
    assert request.callback == spider.parse_products


def test_legacy_series_uses_linked_product_release_before_export(spider):
    series = page(
        '<select id="series"><option selected value="550106">【OP-06】</option></select>'
        '<div class="countCol">1件HIT</div><a class="modalOpen" data-src="#OP06-001"></a>'
        '<dl class="modalCol" id="OP06-001"><dt><div class="infoCol"><span>OP06-001</span>'
        '<span>L</span><span>LEADER</span></div><div class="cardName">テスト</div></dt>'
        '<dd><div class="frontCol"><img data-src="/images/cardlist/card/OP06-001.png"></div>'
        '<div class="getInfo"><h3>入手情報</h3>テスト【OP-06】<div class="getInfoBtnCol">'
        '<a href="/products/boosters/op06.php">商品情報</a></div></div></dd></dl>',
        "/cardlist/?series=550106",
    )
    (product,) = spider.parse_series(series, "550106", "テスト【OP-06】")
    detail = page(
        "<div><h4>発売日</h4><div>2023.11.25(土)</div></div>",
        "/products/boosters/op06.php",
    )
    (retry,) = product.callback(detail, **product.cb_kwargs)
    (item,) = retry.callback(series, **retry.cb_kwargs)
    assert item["release_date"] == "2023-11-25"
    assert item["number"] == "OP06-001"
    assert item["images"]["front"] == BASE + "/images/cardlist/card/OP06-001.png"


@pytest.mark.parametrize(
    "results",
    [
        '<div class="countCol">2件HIT</div><dl class="modalCol" id="A"></dl>',
        '<div class="countCol">1件HIT</div><a class="modalOpen" data-src="#B"></a>'
        '<dl class="modalCol" id="A"></dl>',
        '<p class="errMsgCol">検索結果が多すぎます</p>',
    ],
)
def test_incomplete_or_wrong_result_page_is_rejected_before_export(spider, results):
    body = '<select id="series"><option selected value="550101">OP-01</option></select>'
    with pytest.raises(CloseSpider) as error:
        list(spider.parse_series(page(body + results, "/cardlist/"), "550101", "OP-01"))
    assert error.value.reason == "invalid_catalogue"


def test_mixed_series_exports_new_undated_promos_and_skips_announced_distributions(spider):
    cards = [
        ("P-999", "新しいプロモーションパック"),
        ("P-999_p1", "スタンダードバトル 2026年12月優勝記念品"),
        ("P-999_p2", "Vジャンプ2027年1月号付録（2026年11月10日売）"),
        ("P-999_p3", "スタンダードバトル 2026年11月21日開催記念品"),
    ]
    html = '<select id="series"><option selected value="550901">プロモ</option></select>'
    html += '<div class="countCol">4件HIT</div>'
    for modal_id, name in cards:
        html += (
            f'<a class="modalOpen" data-src="#{modal_id}"></a><dl class="modalCol" id="{modal_id}">'
            '<dt><div class="infoCol"><span>P-999</span><span>P</span><span>CHARACTER</span></div>'
            '<div class="cardName">テスト</div></dt><dd><div class="frontCol">'
            f'<img data-src="/images/cardlist/card/{modal_id}.png"></div>'
            f'<div class="getInfo"><h3>入手情報</h3>{name}</div></dd></dl>'
        )
    items = list(spider.parse_series(page(html, "/cardlist/"), "550901", "プロモ"))
    assert [item["external_ids"]["card"] for item in items] == ["P-999", "P-999_p2"]
    assert "release_date" not in items[0]
