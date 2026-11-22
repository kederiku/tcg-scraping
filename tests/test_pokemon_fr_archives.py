import gzip
import json
from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy.crawler import Crawler
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse, TextResponse
from scrapy.spiderloader import SpiderLoader
from scrapy.statscollectors import MemoryStatsCollector
from scrapy.utils.project import get_project_settings

BASE = "https://www.pokemon.com/fr/jcc-pokemon/cartes-pokemon/series/"
CDX = "https://web.archive.org/cdx/search/cdx"
FIELDS = ["timestamp", "original", "digest"]


def spider(feeds=None, **kwargs):
    settings = get_project_settings()
    if feeds is not None:
        settings.set("FEEDS", feeds, priority="cmdline")
    loader = SpiderLoader.from_settings(settings)
    assert "pokemon_fr_archives" in loader.list()
    cls = loader.load("pokemon_fr_archives")
    crawler = Crawler(cls, settings)
    crawler.stats = MemoryStatsCollector(crawler)
    return cls.from_crawler(crawler, **kwargs)


def index(rows):
    return TextResponse(CDX, body=json.dumps([FIELDS, *rows]).encode(), encoding="utf-8")


def replay(req, body, status=200, archived=True):
    headers = {"Memento-Datetime": "Thu, 19 Nov 2026 10:00:00 GMT"} if archived else {}
    return HtmlResponse(req.url, body=body, status=status, headers=headers, request=req)


def follow(req, response):
    return list(req.callback(response, **req.cb_kwargs))


def html(key):
    return f"""<div class="card-image"><img src="/recto.png"></div>
    <div class="full-card-information" data-card-id="{key}">
    <div class="card-description"><h1>Héricendre</h1>
    <div class="card-type"><h2>Pokémon de base</h2></div></div>
    <div class="stats-footer"><h3>Extension française</h3><span>1/99 Rare</span></div>
    </div>""".encode()


def test_index_pages_keep_older_captures_and_export_only_the_expected_official_card():
    crawler = spider(extension="bw6", max_cards=1)
    first = index(
        [
            ["20210101100000", BASE + "bw6/1/", "A"],
            ["20220101100000", BASE + "bw6/1", "A"],
            [],
            ["opaque+cursor"],
        ]
    )
    (more,) = crawler.parse(first)
    query = parse_qs(urlsplit(more.url).query)
    assert query["resumeKey"] == ["opaque+cursor"]
    assert query["url"] == ["www.pokemon.com/fr/jcc-pokemon/cartes-pokemon/series/bw6/"]
    later = index(
        [
            ["20230101100000", BASE + "bw6/1", "B"],
            ["20240101100000", BASE + "bw6/1/", "C"],
            ["20240101100000", BASE.replace("www.pokemon.com", "example.com") + "bw6/2", "D"],
            ["20240101100000", BASE + "bw6/2?cardName=test", "E"],
            ["20240101100000", BASE + "bw6/3/", "F"],
        ]
    )
    (newest,) = follow(more, later)
    assert "/20240101100000id_/" in newest.url
    captcha = b'<iframe src="/_Incapsula_Resource?x"></iframe>'
    (wrong,) = follow(newest, replay(newest, captcha))
    (older,) = follow(wrong, replay(wrong, html("other/5")))
    assert "/20220101100000id_/" in older.url
    (item,) = follow(older, replay(older, gzip.compress(html("bw6/1"))))
    assert item["name"] == "Héricendre"
    assert item["source_url"] == BASE + "bw6/1"
    assert item["set"]["name"] == "Extension française"
    assert item["additional_attributes"]["archive"]["url"] == older.url
    assert item["additional_attributes"]["archive"]["timestamp"] == "20220101100000"


def test_missing_replay_moves_to_the_next_card_but_archive_service_block_stops():
    crawler = spider()
    rows = [["20230101100000", BASE + f"bw6/{n}/", str(n)] for n in (1, 2)]
    (req,) = crawler.parse(index(rows))
    (next_card,) = follow(req, replay(req, b"", status=404, archived=False))
    assert next_card.url.endswith("/bw6/2/")
    with pytest.raises(CloseSpider):
        follow(
            next_card,
            replay(next_card, b'<iframe src="/_Incapsula_Resource"></iframe>', archived=False),
        )


def test_bad_index_cannot_finish_as_a_successful_empty_export():
    with pytest.raises(CloseSpider):
        list(spider().parse(TextResponse(CDX, body=b"<html>Error</html>", encoding="utf-8")))


def test_appending_to_direct_export_resumes_and_preserves_live_cards(tmp_path):
    path = tmp_path / "cartes.jsonl"
    path.write_text(json.dumps({"card_id": "pokemon.com:fr:bw6/1", "name": "Granivol"}) + "\n")
    crawler = spider(feeds={str(path): {"format": "jsonlines", "mode": "append"}}, max_cards=1)
    rows = [["20230101100000", BASE + f"bw6/{n}/", str(n)] for n in (1, 2)]
    (req,) = crawler.parse(index(rows))
    assert req.url.endswith("/bw6/2/")
    assert "Granivol" in path.read_text()


def test_explicitly_english_replay_is_skipped():
    crawler = spider()
    rows = [["20230101100000", BASE + f"bw6/{n}/", str(n)] for n in (1, 2)]
    (req,) = crawler.parse(index(rows))
    (next_card,) = follow(req, replay(req, b'<html lang="en">' + html("bw6/1") + b"</html>"))
    assert next_card.url.endswith("/bw6/2/")
