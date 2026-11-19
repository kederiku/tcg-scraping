"""Shared traversal and completeness checks for Bandai's ONE PIECE catalogues."""

import re
from collections import Counter
from html import unescape
from urllib.parse import parse_qs, urlsplit

import scrapy
from scrapy.exceptions import CloseSpider

from tcg_scraper.one_piece_cards import CATALOGUES, parse_card


def product_key(title, language="ja"):
    code = CATALOGUES[language].product_code.search(title)
    return code[1] if code else title.strip()


class OnePieceCatalogueSpider(scrapy.Spider):
    series_query = "?series={series}"
    allow_identical_repeats = False

    def __init__(self, series=None, **kwargs):
        super().__init__(**kwargs)
        self.series = series
        self.today = self.market_today()
        self.release_dates = {}

    async def start(self):
        yield scrapy.Request(self.products_url, self.parse_products, errback=self.request_failed)

    def parse_products(self, response):
        next_url = self.read_product_page(response)
        if next_url:
            yield response.follow(next_url, self.parse_products, errback=self.request_failed)
        else:
            yield scrapy.Request(self.catalogue_url, self.parse_index, errback=self.request_failed)

    def read_product_page(self, response):
        products = response.css("a.linkListColItem")
        if not products:
            raise CloseSpider("invalid_release_calendar")
        for product in products:
            title = product.css(".linkListColTitle").xpath("string(.)").get()
            times = product.xpath(
                ".//p[span[normalize-space(.)=$label]]/time", label=self.release_label
            )
            if title and times and (release_date := self.read_release_date(times[0])):
                self.release_dates[product_key(title, self.language)] = release_date
                self.release_dates[title.strip()] = release_date
        next_url = response.css(".pagerColNext:not(.disable)::attr(href)").get()
        if next_url:
            current = parse_qs(urlsplit(response.url).query).get("page", ["1"])[0]
            next_page = parse_qs(urlsplit(next_url).query).get("page", [""])[0]
            if not next_page.isdigit() or int(next_page) != int(current) + 1:
                raise CloseSpider("invalid_release_calendar")
        return next_url

    def parse_index(self, response):
        options = response.css("select#series option[value]")
        series_names = {}
        for option in options:
            series_id = option.attrib["value"]
            if not series_id:
                continue
            if not series_id.isdecimal() or series_id in series_names:
                raise CloseSpider("invalid_series_index")
            name = re.sub(
                r"<br\b[^>]*>", " ", unescape(option.xpath("string(.)").get()), flags=re.I
            )
            series_names[series_id] = " ".join(name.split())
        if not series_names or (self.series and self.series not in series_names):
            raise CloseSpider("unknown_series")
        self.crawler.stats.set_value("one_piece/series_listed", len(series_names))
        for series_id, name in series_names.items():
            if self.series and series_id != self.series:
                continue
            released = self.release_dates.get(product_key(name, self.language))
            if released and released > self.today:
                self.logger.info("Upcoming series %s (%s): %s", series_id, released, name)
                self.crawler.stats.inc_value("one_piece/upcoming_series")
                continue
            url = response.urljoin(self.series_query.format(series=series_id))
            yield response.follow(
                url,
                self.parse_series,
                cb_kwargs={"series_id": series_id, "series_name": name},
                errback=self.request_failed,
                dont_filter=url == response.url,
            )

    def parse_series(self, response, series_id, series_name):
        selected = response.css("select#series option[selected]::attr(value)").get()
        count_text = "".join(response.css(".countCol").xpath("string(.)").get(default="").split())
        count = re.search(self.count_pattern, count_text)
        modals = response.css("dl.modalCol")
        targets = response.css("a.modalOpen::attr(data-src)").getall()
        ids = [card.attrib.get("id") for card in modals]
        if (
            selected != series_id
            or count is None
            or int(count[1].replace(",", "")) != len(modals)
            or not all(ids)
            or Counter(targets) != Counter("#" + card_id for card_id in ids)
        ):
            self.logger.error("Card count, selection or modal links disagree at %s", response.url)
            raise CloseSpider("invalid_catalogue")

        unique = {}
        for card_id, modal in zip(ids, modals, strict=True):
            if card_id in unique:
                if not self.allow_identical_repeats or unique[card_id].get() != modal.get():
                    self.logger.error(
                        "Conflicting or unexpected duplicate %s at %s", card_id, response.url
                    )
                    raise CloseSpider("invalid_catalogue")
                self.crawler.stats.inc_value("one_piece/identical_repeats")
            else:
                unique[card_id] = modal

        released = self.release_dates.get(product_key(series_name, self.language))
        if released and released > self.today:
            self.crawler.stats.inc_value("one_piece/upcoming_series")
            return
        if series_id not in self.mixed_series and released is None and modals:
            yield from self.missing_release(response, modals[0], series_id, series_name)
            return

        self.crawler.stats.inc_value("one_piece/series_checked")
        self.crawler.stats.inc_value("one_piece/listed_in_checked_series", len(modals))
        for modal in unique.values():
            item = parse_card(response, modal, series_id, series_name, language=self.language)
            if not all(item.get(key) for key in ("name", "number", "card_type")):
                self.logger.error("Incomplete card header at %s", item["source_url"])
                raise CloseSpider("invalid_card_detail")
            item_release = released
            if series_id in self.mixed_series:
                acquisition = item["set"].get("name", "")
                item_release = self.release_dates.get(acquisition)
                if (item_release and item_release > self.today) or self.upcoming_distribution(
                    acquisition, self.today
                ):
                    self.crawler.stats.inc_value("one_piece/distribution_excluded")
                    continue
            if item_release:
                item["release_date"] = item_release.isoformat()
            if not item.get("images", {}).get("front"):
                raise CloseSpider("missing_card_image")
            yield item

    def retry_released_series(self, series_url, series_id, name, released):
        if released > self.today:
            self.crawler.stats.inc_value("one_piece/upcoming_series")
            return
        yield scrapy.Request(
            series_url,
            self.parse_series,
            cb_kwargs={"series_id": series_id, "series_name": name},
            errback=self.request_failed,
            dont_filter=True,
        )

    def request_failed(self, failure):
        self.logger.error("Failed request: %s (%s)", failure.request.url, failure.getErrorMessage())
        if not str(failure.value).startswith("blocked_"):
            raise CloseSpider("request_failed")
