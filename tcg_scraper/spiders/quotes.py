"""A bounded demonstration on a site made for practicing scraping."""

from urllib.parse import urlsplit

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy_playwright.page import PageMethod


class QuotesSpider(scrapy.Spider):
    name = "quotes"

    def __init__(self, start_url=None, javascript="false", max_pages="3", **kwargs):
        super().__init__(**kwargs)
        if str(javascript).lower() not in {"true", "false"}:
            raise ValueError("javascript must be true or false")
        self.javascript = str(javascript).lower() == "true"
        try:
            self.max_pages = int(max_pages)
        except (TypeError, ValueError) as exc:
            raise ValueError("max_pages must be a positive integer") from exc
        if self.max_pages < 1:
            raise ValueError("max_pages must be a positive integer")
        self.start_url = start_url or (
            "https://quotes.toscrape.com/js/" if self.javascript else "https://quotes.toscrape.com/"
        )
        parsed = urlsplit(self.start_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("start_url must be an absolute HTTP(S) URL")
        self.allowed_domains = [parsed.hostname]

    def page_request(self, url, page_number):
        return scrapy.Request(
            url,
            callback=self.parse,
            errback=self.on_request_error,
            cb_kwargs={"page_number": page_number},
            meta={
                "playwright": self.javascript,
                "playwright_context": "default",
                "playwright_context_kwargs": self.settings.getdict("BROWSER_CONTEXT_OPTIONS"),
                "playwright_page_methods": [
                    PageMethod(
                        "wait_for_function",
                        "document.querySelector('.quote') || "
                        "performance.getEntriesByType('navigation')[0]?.responseStatus >= 400",
                        timeout=15_000,
                    ),
                ],
            },
        )

    async def start(self):
        yield self.page_request(self.start_url, 1)

    def parse(self, response, page_number):
        quotes = response.css(".quote")
        if not quotes:
            raise CloseSpider("unexpected_content")
        for quote in quotes:
            yield {
                "text": quote.css(".text::text").get(),
                "author": quote.css(".author::text").get(),
                "tags": quote.css(".tags .tag::text").getall(),
                "source_url": response.url,
            }
        next_page = response.css("li.next a::attr(href)").get()
        if next_page and page_number < self.max_pages:
            yield self.page_request(response.urljoin(next_page), page_number + 1)

    def on_request_error(self, failure):
        # The block middleware has already selected its own finish reason.
        if str(failure.value).startswith("blocked_"):
            return
        self.logger.warning("Request failed: %s", failure.getErrorMessage())
        raise CloseSpider("request_failed")
