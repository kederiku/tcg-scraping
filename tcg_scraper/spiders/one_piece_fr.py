"""Catalogue français Bandai exporté au format ItemOnePiece."""

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from scrapy.exceptions import CloseSpider

from tcg_scraper.one_piece_catalogue import OnePieceCatalogueSpider, product_key

# The French calendar also uses English month names on older products.
MONTHS = {
    name: number
    for number, names in enumerate(
        (
            "janvier january",
            "février february",
            "mars march",
            "avril april",
            "mai may",
            "juin june",
            "juillet july",
            "août august",
            "septembre september",
            "octobre october",
            "novembre november",
            "décembre december",
        ),
        start=1,
    )
    for name in names.split()
}
DATE_TEXT = re.compile(r"\b(?:(\d{1,2})(?:er)?\s+)?(" + "|".join(MONTHS) + r")\s+(\d{4})\b", re.I)


class OnePieceFrSpider(OnePieceCatalogueSpider):
    name = "one_piece_fr"
    language = "fr"
    allow_identical_repeats = True
    allowed_domains = ["fr.onepiece-cardgame.com"]
    catalogue_url = "https://fr.onepiece-cardgame.com/cardlist/?series=622118"
    products_url = "https://fr.onepiece-cardgame.com/products/"
    mixed_series = {"622801", "622901"}
    release_label = "Date de sortie"
    count_pattern = r"([\d,]+)résultats?"
    custom_settings = {
        "CLOSESPIDER_ERRORCOUNT": 1,
        "FEEDS": {"data/one_piece_fr.jsonl": {"format": "jsonlines", "overwrite": True}},
    }

    @staticmethod
    def market_today():
        try:
            return datetime.now(ZoneInfo("Europe/Paris")).date()
        except ZoneInfoNotFoundError:
            # Windows installations without IANA timezone data use the local day.
            return date.today()

    @staticmethod
    def read_release_date(time_node):
        # Some datetime attributes on this site are empty or contradict the displayed date.
        text = time_node.xpath("string(.)").get().strip()
        if match := DATE_TEXT.fullmatch(text):
            day, month, year = match.groups()
            if day:
                return date(int(year), MONTHS[month.lower()], int(day))
        value = time_node.attrib.get("datetime")
        return date.fromisoformat(value) if value else None

    @staticmethod
    def upcoming_distribution(label, today):
        for day, month, year in DATE_TEXT.findall(label):
            if (int(year), MONTHS[month.lower()], int(day or 1)) > (
                today.year,
                today.month,
                today.day,
            ):
                return True
        return False

    def missing_release(self, response, modal, series_id, series_name):
        # Products released on the same day can change order between pages of the main calendar.
        code = product_key(series_name, self.language)
        category = "decks" if code.startswith("ST-") else "boosters"
        url = response.css(f'a[href$="/products/?subcategory={category}"]::attr(href)').get()
        if not url:
            raise CloseSpider("missing_product_release_date")
        yield response.follow(
            url,
            self.find_release_in_category,
            cb_kwargs={"series_url": response.url, "series_id": series_id, "name": series_name},
            errback=self.request_failed,
            dont_filter=True,
        )

    def find_release_in_category(self, response, series_url, series_id, name):
        next_url = self.read_product_page(response)
        released = self.release_dates.get(product_key(name, self.language))
        if released:
            yield from self.retry_released_series(series_url, series_id, name, released)
        elif next_url:
            yield response.follow(
                next_url,
                self.find_release_in_category,
                cb_kwargs={"series_url": series_url, "series_id": series_id, "name": name},
                errback=self.request_failed,
                dont_filter=True,
            )
        else:
            self.logger.error("Missing release date for %s (%s)", name, series_id)
            raise CloseSpider("missing_product_release_date")
