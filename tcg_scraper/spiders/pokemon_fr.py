"""Encyclopédie officielle française : filtres d'extension, résultats et fiches."""

import re
from urllib.parse import parse_qs, urlencode, urlsplit

import scrapy
from scrapy.exceptions import CloseSpider

from tcg_scraper.pokemon_fr_cards import card_item, text_of

CATALOGUE = "https://www.pokemon.com/fr/jcc-pokemon/cartes-pokemon"


def check_access(response):
    if response.css('iframe[src*="_Incapsula_Resource"], iframe[src*="hcaptcha.com"]') or (
        response.css("title::text").get() == "Pardon Our Interruption"
    ):
        raise CloseSpider("blocked_captcha", error=True)


class PokemonFrSpider(scrapy.Spider):
    name = "pokemon_fr"
    custom_settings = {
        "CLOSESPIDER_ERRORCOUNT": 1,
        "FEED_STORE_EMPTY": False,
        "FEEDS": {"data/pokemon_fr.jsonl": {"format": "jsonlines", "mode": "overwrite"}},
    }

    def __init__(self, start_url=CATALOGUE, extension=None, max_cards=0, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = [start_url]
        self.allowed_domains = [urlsplit(start_url).hostname]
        self.extension = extension
        self.max_cards = int(max_cards)
        if self.max_cards < 0:
            raise ValueError("max_cards must be nonnegative")
        self.state = {}

    async def start(self):
        yield scrapy.Request(self.start_urls[0], errback=self.request_failed)

    def parse(self, response):
        check_access(response)
        form = response.css("form#filters")
        sets = {}
        for group in form.css("#filterExpansions fieldset"):
            series = text_of(group.css("h2"))
            for row in group.css("li"):
                field = row.css('input[type="checkbox"][name]')
                if not field:
                    continue
                code = field.attrib["name"]
                metadata = {"id": code, "name": text_of(row.css("label span")), "series": series}
                query = urlencode({code: field.attrib.get("value", "on")})
                action = response.urljoin(form.attrib.get("action") or response.url)
                sets[code] = (action + "?" + query, metadata)
        if not sets:
            raise CloseSpider("invalid_extension_index", error=True)
        if self.extension:
            if self.extension not in sets:
                raise CloseSpider("unknown_extension", error=True)
            sets = {self.extension: sets[self.extension]}
        self.logger.info("%d extension(s) à parcourir", len(sets))
        listings = list(sets.values())
        if self.max_cards:
            # A sample typically fits on the first page. Defer the other sets.
            self.state["remaining_sets"] = listings[1:][::-1]
            listings = listings[:1]
        for url, expansion in listings:
            yield self.listing_request(url, expansion)

    def listing_request(self, url, expansion):
        return scrapy.Request(
            url,
            callback=self.parse_results,
            errback=self.request_failed,
            cb_kwargs={"expansion": expansion},
            priority=-1,
        )

    def parse_results(self, response, expansion):
        check_access(response)
        results = response.css(".card-results")
        links = results.css('#cardResults a[href*="/series/"]::attr(href)').getall()
        if not links and not re.search(r"aucune? (?:carte|résultat)", text_of(results), re.I):
            raise CloseSpider("invalid_card_results", error=True)
        scheduled = self.state.setdefault("scheduled_cards", set())
        for href in links:
            url = response.urljoin(href)
            card_key = url.rstrip("/")
            if card_key not in scheduled:
                scheduled.add(card_key)
                yield scrapy.Request(
                    url,
                    callback=self.parse_card,
                    errback=self.request_failed,
                    cb_kwargs={"expansion": expansion},
                )
                if self.max_cards and len(scheduled) >= self.max_cards:
                    return
        pager = results.css("#cards-load-more")
        next_url = next(
            (a.attrib["href"] for a in pager.css("a[href]") if "suivants" in text_of(a).lower()),
            None,
        )
        if next_url:
            url = response.urljoin(next_url)
            current = parse_qs(urlsplit(response.url).query, keep_blank_values=True)
            following = parse_qs(urlsplit(url).query, keep_blank_values=True)
            code = expansion["id"]
            page_number = current.get("page", ["1"])[0]
            if (
                code not in current
                or following.get(code) != current[code]
                or not page_number.isdecimal()
                or following.get("page") != [str(int(page_number) + 1)]
            ):
                raise CloseSpider("invalid_next_page", error=True)
            yield self.listing_request(url, expansion)
        else:
            pages = re.search(r"(\d+)\s+sur\s+(\d+)", text_of(pager))
            if pages and pages[1] != pages[2]:
                raise CloseSpider("missing_next_page", error=True)
            if self.state.get("remaining_sets"):
                yield self.listing_request(*self.state["remaining_sets"].pop())

    def parse_card(self, response, expansion):
        check_access(response)
        return card_item(response, expansion)

    def request_failed(self, failure):
        if str(failure.value).startswith("blocked_"):
            return
        self.logger.error("%s : %s", failure.request.url, failure.getErrorMessage())
        raise CloseSpider("request_failed", error=True)
