"""Replay archived French Pokémon.com card pages without requesting the live site."""

import gzip
import json
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse
from w3lib.url import file_uri_to_path

from tcg_scraper.pokemon_fr_cards import card_item
from tcg_scraper.spiders.pokemon_fr import CATALOGUE, check_access

CDX = "https://web.archive.org/cdx/search/cdx"
CARD_PATH = urlsplit(CATALOGUE).path + "/series/"
CARD_KEY = re.compile(re.escape(CARD_PATH) + r"([\w-]+/[\w-]+)/?", re.ASCII)
FIELDS = ["timestamp", "original", "digest"]
MAX_HTML = 10 * 1024 * 1024


def official_key(url):
    parts = urlsplit(url)
    if (
        parts.scheme not in {"https", "http"}
        or parts.hostname not in {"www.pokemon.com", "pokemon.com"}
        or parts.username is not None
        or parts.password is not None
        or parts.port not in {None, 80, 443}
        or parts.query
        or parts.fragment
    ):
        return None
    match = CARD_KEY.fullmatch(parts.path)
    return match[1].lower() if match else None


def previously_exported(feeds):
    """A local JSONL in append mode is the restart point, including live Pokémon.com items."""
    keys = set()
    if len(feeds) != 1:
        return keys
    uri, options = next(iter(feeds.items()))
    uri = str(uri)
    if (
        options.get("format") not in {"jsonlines", "jsonl", "jl"}
        or options.get("mode", "append") != "append"
        or options.get("overwrite")
        or "%(" in uri
        or "://" in uri
        and not uri.startswith("file://")
    ):
        return keys
    path = Path(file_uri_to_path(uri) if uri.startswith("file://") else uri)
    if path.is_file():
        with path.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                try:
                    if not line.endswith("\n"):
                        raise ValueError("ligne sans fin de ligne")
                    card_id = json.loads(line)["card_id"]
                    if not isinstance(card_id, str) or not card_id.startswith("pokemon.com:fr:"):
                        raise ValueError("identifiant Pokémon FR attendu")
                except (ValueError, TypeError, KeyError) as exc:
                    raise ValueError(f"Export JSONL à vérifier : {path}, ligne {number}") from exc
                keys.add(card_id.removeprefix("pokemon.com:fr:").lower())
    return keys


class PokemonFrArchivesSpider(scrapy.Spider):
    name = "pokemon_fr_archives"
    allowed_domains = ["web.archive.org"]
    custom_settings = {
        "CLOSESPIDER_ERRORCOUNT": 1,
        "FEED_STORE_EMPTY": False,
    }

    def __init__(self, extension=None, max_cards=0, **kwargs):
        super().__init__(**kwargs)
        self.extension = extension.lower() if extension else None
        self.max_cards = int(max_cards)
        if self.extension and not re.fullmatch(r"[a-z0-9_-]+", self.extension):
            raise ValueError("Invalid extension code")
        if self.max_cards < 0:
            raise ValueError("max_cards must be nonnegative")
        self.state = {}

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        feeds = crawler.settings.getdict("FEEDS")
        if not feeds:
            stem = "data/pokemon_fr_archives"
            if spider.extension:
                stem += "-" + spider.extension
            filename = stem + ("-sample.jsonl" if spider.max_cards else ".jsonl")
            mode = "overwrite" if spider.max_cards else "append"
            feeds = {filename: {"format": "jsonlines", "mode": mode}}
            crawler.settings.set("FEEDS", feeds, priority="spider")
        spider.previous = previously_exported(feeds)
        return spider

    def index_request(self, cursor=None):
        prefix = "www.pokemon.com" + CARD_PATH
        if self.extension:
            prefix += self.extension + "/"
        params = [
            ("url", prefix),
            ("matchType", "prefix"),
            ("filter", "statuscode:200"),
            ("filter", "mimetype:text/html"),
            ("output", "json"),
            ("fl", ",".join(FIELDS)),
            ("showResumeKey", "true"),
            ("limit", "1000"),
        ]
        if cursor:
            params.append(("resumeKey", cursor))
        return scrapy.Request(
            CDX + "?" + urlencode(params),
            callback=self.parse,
            errback=self.request_failed,
            meta={"dont_redirect": True},
        )

    async def start(self):
        yield self.index_request()

    def parse(self, response):
        # CDX sorts by URL key then timestamp. A card may straddle two index pages.
        try:
            rows = json.loads(response.body)
            if rows and rows[0] != FIELDS:
                raise ValueError
            rows = rows[1:]
            cursor = None
            if len(rows) >= 2 and rows[-2] == [] and len(rows[-1]) == 1:
                cursor = rows[-1][0]
                rows = rows[:-2]
            groups = {}
            if carry := self.state.pop("carry", None):
                groups[carry[0]] = carry[1]
            for timestamp, original, digest in rows:
                if not re.fullmatch(r"[0-9]{14}", timestamp):
                    raise ValueError
                key = official_key(original)
                if key and (not self.extension or key.split("/")[0] == self.extension):
                    group = groups.setdefault(key, {})
                    group[digest if digest != "-" else timestamp] = (timestamp, original)
            if cursor:
                if cursor == self.state.get("last_cursor"):
                    raise ValueError
                self.state["last_cursor"] = cursor
                if groups:
                    self.state["carry"] = groups.popitem()
        except (TypeError, ValueError, KeyError, IndexError) as exc:
            raise CloseSpider("invalid_archive_index", error=True) from exc
        self.state["cursor"] = cursor
        self.state["queue"] = list(reversed(groups.items()))
        self.crawler.stats.inc_value("archive/indexed_cards", len(groups))
        yield from self.advance()

    def advance(self):
        emitted = self.state.setdefault("emitted", set())
        if self.max_cards and len(emitted) >= self.max_cards:
            return
        while self.state["queue"]:
            key, group = self.state["queue"].pop()
            if key in self.previous:
                self.crawler.stats.inc_value("archive/already_exported")
            elif key not in emitted:
                yield self.snapshot_request(key, sorted(group.values()))
                return
        if cursor := self.state.pop("cursor", None):
            yield self.index_request(cursor)
        elif not emitted and not self.crawler.stats.get_value("archive/already_exported"):
            raise CloseSpider("no_readable_archived_cards", error=True)

    def snapshot_request(self, key, captures):
        timestamp, original = captures[-1]
        return scrapy.Request(
            f"https://web.archive.org/web/{timestamp}id_/{original}",
            callback=self.parse_snapshot,
            errback=self.request_failed,
            cb_kwargs={
                "key": key,
                "original": original,
                "timestamp": timestamp,
                "older": captures[:-1],
            },
            meta={
                "dont_redirect": True,
                "handle_httpstatus_list": [301, 302, 303, 307, 308, 404, 410, 451],
            },
        )

    def parse_snapshot(self, response, key, original, timestamp, older):
        item = None
        if response.status == 200:
            # Some raw replays retain an inner gzip layer after HTTP decompression.
            body = response.body
            if body.startswith(b"\x1f\x8b"):
                try:
                    with gzip.GzipFile(fileobj=BytesIO(body)) as archive:
                        body = archive.read(MAX_HTML + 1)
                except (OSError, EOFError):
                    body = b""
            url = "https://www.pokemon.com" + urlsplit(original).path
            page = HtmlResponse(url, body=body, headers=response.headers)
            if b"Memento-Datetime" not in response.headers:
                check_access(page)
            actual = page.css(".full-card-information::attr(data-card-id)").get("")
            language = page.css("html::attr(lang)").get("fr").lower().split("-")[0]
            if len(body) <= MAX_HTML and actual.lower() == key and language == "fr":
                try:
                    item = card_item(page, {})
                except CloseSpider as exc:
                    if exc.reason != "invalid_card_detail":
                        raise
        if item is not None:
            item.setdefault("additional_attributes", {})["archive"] = {
                "url": response.url,
                "timestamp": timestamp,
            }
            self.state.setdefault("emitted", set()).add(key)
            yield item
        elif older and response.status != 451:
            self.crawler.stats.inc_value("archive/older_capture_attempts")
            yield self.snapshot_request(key, older)
            return
        else:
            self.crawler.stats.inc_value("archive/unreadable_cards")
            self.logger.debug("Aucune capture lisible pour %s", key)
        yield from self.advance()

    def request_failed(self, failure):
        if str(failure.value).startswith("blocked_"):
            return
        self.logger.error("%s : %s", failure.request.url, failure.getErrorMessage())
        raise CloseSpider("archive_request_failed", error=True)
