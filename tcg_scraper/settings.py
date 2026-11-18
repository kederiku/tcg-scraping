"""Conservative defaults; tune per site, not per request."""

import os

BOT_NAME = "tcg_scraper"
SPIDER_MODULES = ["tcg_scraper.spiders"]
NEWSPIDER_MODULE = "tcg_scraper.spiders"
ROBOTSTXT_OBEY = True
ROBOTSTXT_USER_AGENT = "tcg-scraping"

CONCURRENT_REQUESTS = 2
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = float(os.getenv("DOWNLOAD_DELAY", "3"))
DOWNLOAD_DELAY_JITTER = 0.5
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5
DOWNLOAD_TIMEOUT = 45
DOWNLOAD_MAXSIZE = 10 * 1024 * 1024
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408]
COOKIES_ENABLED = True
TELNETCONSOLE_ENABLED = False
REMOTE_CONTROL_ENABLED = False
MEMUSAGE_ENABLED = os.name != "nt"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
FEED_EXPORT_ENCODING = "utf-8"

# None lets Playwright use the actual Chromium version, with no invented fingerprint.
# Ordinary HTTP requests get a stable configurable identity in our middleware.
USER_AGENT = None
HTTP_USER_AGENT = os.getenv(
    "HTTP_USER_AGENT", "tcg-scraping/0.1 (+https://github.com/kederiku/tcg-scraping)"
)
DEFAULT_REQUEST_HEADERS = {"Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"}

HTTPCACHE_ENABLED = os.getenv("HTTP_CACHE", "false").lower() == "true"
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [401, 403, 429, 500, 502, 503, 504]

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
DOWNLOADER_MIDDLEWARES = {
    "tcg_scraper.middlewares.RequestPolicyMiddleware": 450,
    # Before cache (900) and retry (550) on the response path.
    "tcg_scraper.middlewares.StopOnBlockMiddleware": 950,
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True, "chromium_sandbox": True}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30_000
PLAYWRIGHT_MAX_CONTEXTS = 1
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 1
BROWSER_CONTEXT_OPTIONS = {
    "locale": "fr-FR",
    "timezone_id": "Europe/Paris",
    "viewport": {"width": 1365, "height": 768},
}
PLAYWRIGHT_ABORT_REQUEST = "tcg_scraper.middlewares.abort_unneeded_resource"
