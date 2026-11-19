"""Catalogue multilingue Magic et décisions de règles des exports officiels Scryfall."""

import gzip
import json
from collections import defaultdict
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

import scrapy
from scrapy import signals
from scrapy.exceptions import CloseSpider
from w3lib.url import file_uri_to_path

from tcg_scraper.scryfall_cards import parse_card

BULK_API = "https://api.scryfall.com/bulk-data"


def bulk_location(metadata, kind, api):
    """Valide le type multilingue et le fichier annoncé avant le téléchargement."""
    if metadata.get("object") != "bulk_data" or metadata.get("type") != kind:
        raise ValueError(f"La réponse Scryfall ne décrit pas l’export {kind}.")
    url = metadata.get("jsonl_download_uri")
    size = metadata.get("compressed_size")
    target = urlsplit(url or "")
    origin = urlsplit(api)
    allowed_origins = {("https", "data.scryfall.io"), (origin.scheme, origin.netloc)}
    if (target.scheme, target.netloc) not in allowed_origins or not target.path.endswith(".gz"):
        raise ValueError(f"URL du fichier {kind} invalide : {url!r}")
    if type(size) is not int or size <= 0:
        raise ValueError(f"Taille compressée invalide pour {kind} : {size!r}")
    return url, size


def read_records(path):
    with gzip.open(path, "rb") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("objet JSON attendu")
            except ValueError as exc:
                raise ValueError(f"{path.name}, ligne {line_number} : {exc}") from exc
            yield row


def local_jsonl_overwrite(feeds):
    """Reconnaît le cas standard de scrapy crawl -O fichier.jsonl."""
    if len(feeds) != 1:
        return None
    uri, options = next(iter(feeds.items()))
    if options.get("mode") != "overwrite" or options.get("format") not in {
        "jsonlines",
        "jl",
        "jsonl",
    }:
        return None
    uri = str(uri)
    if options.keys() - {"format", "mode"} or "%(" in uri:
        return None
    if uri.startswith("file://"):
        return Path(file_uri_to_path(uri))
    if Path(uri).is_absolute() or not urlsplit(uri).scheme:
        return Path(uri)
    return None


class ScryfallSpider(scrapy.Spider):
    name = "magic_scryfall"
    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {"Accept": "application/json;q=0.9,*/*;q=0.8"},
        # Native HTTP streams the bulk response into body_file.
        "DOWNLOAD_HANDLERS": {
            "https": "scrapy.core.downloader.handlers.http11.HTTP11DownloadHandler",
            "http": "scrapy.core.downloader.handlers.http11.HTTP11DownloadHandler",
        },
        "CLOSESPIDER_ERRORCOUNT": 1,
    }

    def __init__(self, max_cards=0, output=None, **kwargs):
        super().__init__(**kwargs)
        self.max_cards = int(max_cards)
        if self.max_cards < 0:
            raise ValueError("max_cards doit être positif ou nul")
        self.output = output
        self.rulings = defaultdict(list)
        self.rows = 0
        self.complete = False

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.api = crawler.settings.get("SCRYFALL_BULK_API", BULK_API).rstrip("/")
        spider.allowed_domains = [urlsplit(spider.api).hostname, "data.scryfall.io"]
        feeds = crawler.settings.getdict("FEEDS")
        if feeds and spider.output:
            raise ValueError("Choisir soit -a output=..., soit un export Scrapy -o/-O.")
        default = "magic_scryfall-sample.jsonl" if spider.max_cards else "magic_scryfall.jsonl"
        spider.destination = (
            local_jsonl_overwrite(feeds) if feeds else Path(spider.output or Path("data") / default)
        )
        parent = None
        if spider.destination is not None:
            spider.destination = spider.destination.resolve()
            parent = spider.destination.parent
            parent.mkdir(parents=True, exist_ok=True)
        spider.workspace = TemporaryDirectory(dir=parent, prefix=".scryfall-")
        spider.workdir = Path(spider.workspace.name)
        if spider.destination:
            # A sibling of the destination inherits the output directory's Windows ACL.
            # Files created inside TemporaryDirectory would keep its private ACL on rename.
            spider.staged_feed = spider.workdir.with_name(spider.workdir.name + ".jsonl")
            spider.staged_feed.touch(exist_ok=False)
            crawler.settings.set(
                "FEEDS",
                {str(spider.staged_feed): {"format": "jsonlines", "mode": "overwrite"}},
                priority=crawler.settings.getpriority("FEEDS") if feeds else "spider",
            )
        crawler.signals.connect(spider.finish_export, signal=signals.engine_stopped)
        return spider

    async def start(self):
        self.scraped_at = datetime.now(UTC).isoformat()
        yield self.metadata_request("rulings")

    def metadata_request(self, kind):
        return scrapy.Request(
            f"{self.api}/{kind.replace('_', '-')}",
            callback=self.parse_metadata,
            cb_kwargs={"kind": kind},
            meta={"dont_cache": True},
            errback=self.request_failed,
        )

    def parse_metadata(self, response, kind):
        metadata = response.json()
        url, size = bulk_location(metadata, kind, self.api)
        path = self.workdir / f"{kind}.jsonl.gz"
        self.crawler.stats.set_value(f"scryfall/{kind}/updated_at", metadata.get("updated_at"))
        self.logger.info("Export %s, %d octets compressés, %s", kind, size, url)
        yield scrapy.Request(
            url,
            callback=self.parse_bulk,
            cb_kwargs={"kind": kind, "path": path, "expected_size": size},
            headers={"Accept-Encoding": "identity"},
            meta={
                "body_file": str(path),
                "download_maxsize": size,
                "download_warnsize": 0,
                "download_timeout": 1800,
                "dont_cache": True,
                "dont_redirect": True,
            },
            errback=self.request_failed,
        )

    def parse_bulk(self, response, kind, path, expected_size):
        if response.status != 200 or path.stat().st_size != expected_size:
            raise ValueError(f"L’export {kind} reçu est incomplet.")
        if kind == "rulings":
            for row in read_records(path):
                if row.get("object") != "ruling" or not row.get("oracle_id"):
                    raise ValueError("Décision de règles Scryfall sans identité.")
                self.rulings[row["oracle_id"]].append(
                    {"date": row["published_at"], "text": row["comment"], "source": row["source"]}
                )
            if not self.rulings:
                raise ValueError("L’export des décisions de règles est vide.")
            yield self.metadata_request("all_cards")
            return

        sets = set()
        languages = set()
        for row in islice(read_records(path), self.max_cards or None):
            card = parse_card(row, self.scraped_at)
            for part in (card, *card.get("faces", [])):
                if rulings := self.rulings.get(part.get("oracle_id")):
                    part["rulings"] = rulings
            sets.add(card["set"]["code"])
            languages.add(card["language"])
            self.rows += 1
            yield card
        if not self.rows:
            raise ValueError("L’export des cartes est vide.")
        self.crawler.stats.set_value("scryfall/editions", len(sets))
        self.crawler.stats.set_value("scryfall/langues", sorted(languages))
        self.complete = True

    def request_failed(self, failure):
        self.logger.error("Échec de %s : %s", failure.request.url, failure.getErrorMessage())
        raise CloseSpider("scryfall_request_failed", error=True)

    def finish_export(self):
        # engine_stopped runs after the feed has closed and the final stats are available.
        stats = self.crawler.stats
        try:
            if not (
                self.complete
                and stats.get_value("finish_reason") == "finished"
                and self.rows == stats.get_value("item_scraped_count")
                and not any(k.startswith("feedexport/failed_count/") for k in stats.get_stats())
            ):
                raise ValueError("Collecte interrompue ou export incomplet.")
            if self.destination:
                if stats.get_value("feedexport/item_count/FileFeedStorage") != self.rows:
                    raise ValueError("Le nombre de lignes exportées diffère du nombre de cartes.")
                self.staged_feed.replace(self.destination)
                self.logger.info("Export publié : %s (%d cartes)", self.destination, self.rows)
        except (OSError, ValueError) as exc:
            stats.set_value("finish_reason_error", True)
            self.logger.error("Échec de l’export Scryfall : %s", exc)
        finally:
            if self.destination:
                self.staged_feed.unlink(missing_ok=True)
            self.workspace.cleanup()
