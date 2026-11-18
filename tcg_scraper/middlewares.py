"""Small policies that apply to every spider."""

import asyncio

from scrapy.exceptions import IgnoreRequest


def abort_unneeded_resource(request):
    return request.resource_type in {"image", "media", "font"}


class RequestPolicyMiddleware:
    def __init__(self, crawler):
        self.user_agent = crawler.settings.get("HTTP_USER_AGENT")

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_request(self, request):
        if request.meta.get("playwright"):
            # Browser sessions must not replay cached DOMs from another context.
            request.meta["dont_cache"] = True
        else:
            request.headers.setdefault("User-Agent", self.user_agent)


class StopOnBlockMiddleware:
    def __init__(self, crawler):
        self.crawler = crawler
        self.blocked = False
        self.close_task = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_request(self, request):
        if self.blocked:
            raise IgnoreRequest("Crawl stopped after a block")

    async def process_response(self, request, response):
        if response.status not in {403, 429}:
            return response
        self.blocked = True
        reason = f"blocked_{response.status}"
        self.crawler.stats.inc_value(f"policy/{reason}")
        retry_after = response.headers.get("Retry-After", b"unspecified").decode(errors="replace")
        self.crawler.spider.logger.warning(
            "Stopping: %s at %s; Retry-After=%s. Review before restarting.",
            reason,
            response.url,
            retry_after,
        )
        if self.close_task is None:
            # Awaiting engine shutdown inside an active request would deadlock.
            self.close_task = asyncio.create_task(
                self.crawler.engine.close_spider_async(reason=reason)
            )
        raise IgnoreRequest(reason)
