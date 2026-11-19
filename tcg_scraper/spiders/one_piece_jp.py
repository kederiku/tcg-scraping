"""Catalogue japonais Bandai exporté au format ItemOnePiece."""

import re
from datetime import date, datetime, timedelta, timezone

from scrapy.exceptions import CloseSpider

from tcg_scraper.one_piece_catalogue import OnePieceCatalogueSpider, product_key


class OnePieceJpSpider(OnePieceCatalogueSpider):
    name = "one_piece_jp"
    language = "ja"
    allowed_domains = ["www.onepiece-cardgame.com"]
    catalogue_url = "https://www.onepiece-cardgame.com/cardlist/?series=550118"
    products_url = "https://www.onepiece-cardgame.com/products/"
    series_query = "?search=true&series={series}&reprintsFlag=off"
    mixed_series = {"550801", "550901"}
    release_label = "発売日"
    count_pattern = r"([\d,]+)件"
    custom_settings = {
        "CLOSESPIDER_ERRORCOUNT": 1,
        "FEEDS": {"data/one_piece_jp.jsonl": {"format": "jsonlines", "overwrite": True}},
    }

    @staticmethod
    def market_today():
        return datetime.now(timezone(timedelta(hours=9))).date()

    @staticmethod
    def read_release_date(time_node):
        value = time_node.attrib.get("datetime")
        return date.fromisoformat(value) if value else None

    @staticmethod
    def upcoming_distribution(label, today):
        # A magazine issue can carry a future cover month even after it goes on sale.
        for match in re.finditer(r"(\d{4})年\s*(\d{1,2})月(?:\s*(\d{1,2})日)?", label):
            if re.match(r"\s*(?:特大)?号", label[match.end() :]):
                continue
            year, month, day = match.groups()
            if (int(year), int(month), int(day or 1)) > (today.year, today.month, today.day):
                return True
        return False

    def missing_release(self, response, modal, series_id, series_name):
        # Some historical products are absent from the product calendar.
        link = modal.xpath('.//a[normalize-space(.)="商品情報"]/@href').get()
        if not link:
            raise CloseSpider("missing_product_release_date")
        yield response.follow(
            link,
            self.parse_product_detail,
            cb_kwargs={"series_url": response.url, "series_id": series_id, "name": series_name},
            errback=self.request_failed,
        )

    def parse_product_detail(self, response, series_url, series_id, name):
        value = (
            response.xpath('//*[normalize-space(text())="発売日"]/following-sibling::*[1]')
            .xpath("string(.)")
            .re_first(r"(\d{4}\.\d{1,2}\.\d{1,2})")
        )
        if not value:
            raise CloseSpider("missing_product_release_date")
        released = datetime.strptime(value, "%Y.%m.%d").date()
        self.release_dates[product_key(name)] = released
        yield from self.retry_released_series(series_url, series_id, name, released)
