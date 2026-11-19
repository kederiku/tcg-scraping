from datetime import date

import pytest
from scrapy.crawler import Crawler
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse
from scrapy.statscollectors import DummyStatsCollector

from tcg_scraper.spiders.one_piece_fr import OnePieceFrSpider


def page(path, html):
    return HtmlResponse(
        "https://fr.onepiece-cardgame.com" + path, body=html.encode(), encoding="utf-8"
    )


@pytest.fixture
def spider():
    spider = OnePieceFrSpider()
    spider.today = date(2026, 11, 19)
    spider.crawler = Crawler(OnePieceFrSpider)
    spider.crawler.stats = DummyStatsCollector(spider.crawler)
    return spider


def test_calendar_reads_displayed_french_or_english_dates_and_selects_released_series(spider):
    calendar = page(
        "/products/",
        """
        <a class="linkListColItem"><h4 class="linkListColTitle">Booster [OP-18]</h4>
        <p><span>Date de sortie</span><time datetime="2020-11-20">20 novembre 2026</time></p></a>
        <a class="linkListColItem"><h4 class="linkListColTitle">Booster [OP14-EB04]</h4>
        <p><span>Date de sortie</span><time datetime="">30 January 2026</time></p></a>
    """,
    )
    (index,) = spider.parse_products(calendar)
    catalogue = page(
        "/cardlist/?series=622118",
        """
        <select id="series"><option value>TOUT</option>
        <option value="622118" selected>Booster -Dieu- [OP-18]</option>
        <option value="622114">Booster &lt;br&gt; -L&amp;apos;aventure- [OP14-EB04]</option>
        <option value="622901">Carte promo</option></select>
    """,
    )
    queries = list(index.callback(catalogue))
    assert [q.url for q in queries] == [
        "https://fr.onepiece-cardgame.com/cardlist/?series=622114",
        "https://fr.onepiece-cardgame.com/cardlist/?series=622901",
    ]
    assert queries[0].cb_kwargs["series_name"] == "Booster -L'aventure- [OP14-EB04]"
    assert spider.release_dates["OP14-EB04"] == date(2026, 1, 30)
    spider.today = date(2026, 11, 20)
    spider.series = "622118"
    (released,) = spider.parse_index(catalogue)
    assert released.cb_kwargs["series_id"] == "622118"
    assert released.dont_filter  # The index and this series share the same URL.


def test_promotional_page_keeps_undated_printing_and_rejects_incomplete_results(spider):
    body = """
    <select id="series"><option selected value="622901">Carte promo</option></select>
    <div class="countCol">1 résultat</div><a class="modalOpen" data-src="#P-001_p1"></a>
    <dl class="modalCol" id="P-001_p1"><dt><div class="cardName">Luffy</div>
    <div class="infoCol"><span>P-001</span><span>P</span><span>PERSONNAGE</span></div></dt>
    <dd><div class="frontCol"><img data-src="../images/cardlist/card/P-001_p1.webp"></div>
    <div class="getInfo"><h3>Extension</h3>Pack de bienvenue</div></dd></dl>
    """

    def parse(html):
        return list(
            spider.parse_series(page("/cardlist/?series=622901", html), "622901", "Carte promo")
        )

    (item,) = parse(body)
    assert item["language"] == "fr"
    assert (
        item["images"]["front"]
        == "https://fr.onepiece-cardgame.com/images/cardlist/card/P-001_p1.webp"
    )
    assert "release_date" not in item
    assert not parse(body.replace("Pack de bienvenue", "Tournoi de décembre 2026"))
    with pytest.raises(CloseSpider) as failure:
        parse(body.replace("1 résultat", "2 résultats"))
    assert failure.value.reason == "invalid_catalogue"

    # Bandai lists the same Charlotte Brûlée printing twice in PRB-02.
    entry = body[body.index('<a class="modalOpen"') :].strip()
    duplicate = body.replace("1 résultat", "2 résultats") + entry
    (copy,) = parse(duplicate)
    assert copy["card_id"] == item["card_id"]
    with pytest.raises(CloseSpider):
        parse(duplicate.replace("Luffy</div>", "Autre</div>", 1))
    with pytest.raises(CloseSpider):
        parse(duplicate.replace('data-src="#P-001_p1"', 'data-src="#P-002"', 1))


def test_missing_booster_is_found_in_the_french_category_before_export(spider):
    series = page(
        "/cardlist/?series=622112",
        """
        <a href="/products/?subcategory=boosters">BOOSTERS</a>
        <select id="series"><option selected value="622112">[OP-12]</option></select>
        <div class="countCol">1 résultat</div><a class="modalOpen" data-src="#OP12-001"></a>
        <dl class="modalCol" id="OP12-001"><dt><div class="cardName">Test</div>
        <div class="infoCol"><span>OP12-001</span><span>L</span><span>LEADER</span></div></dt>
        <dd><div class="frontCol"><img data-src="/images/cardlist/card/OP12-001.webp"></div>
        </dd></dl>
    """,
    )
    name = "Booster [OP-12]"
    (category,) = spider.parse_series(series, "622112", name)
    assert category.url.endswith("/products/?subcategory=boosters")
    first = page(
        "/products/?subcategory=boosters",
        """
        <a class="linkListColItem"><h4 class="linkListColTitle">Un autre booster</h4></a>
        <a class="pagerColNext" href="?subcategory=boosters&amp;page=2">Suivant</a>
    """,
    )
    (following,) = category.callback(first, **category.cb_kwargs)
    second = page(
        "/products/?subcategory=boosters&page=2",
        """
        <a class="linkListColItem"><h4 class="linkListColTitle">Héritage [OP-12]</h4>
        <p><span>Date de sortie</span><time>22 August 2025</time></p></a>
    """,
    )
    (series_retry,) = following.callback(second, **following.cb_kwargs)
    assert series_retry.dont_filter
    (item,) = series_retry.callback(series, **series_retry.cb_kwargs)
    assert item["release_date"] == "2025-08-22"
