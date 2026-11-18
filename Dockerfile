FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app
COPY requirements-dev.lock /tmp/requirements-dev.lock
# Playwright's bundled Node needs libatomic before it can install browser deps.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && pip install --no-cache-dir -r /tmp/requirements-dev.lock \
    && python -m playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid "${USER_GID}" scraper \
    && useradd --create-home --uid "${USER_UID}" --gid "${USER_GID}" scraper \
    && mkdir -p /app/data /app/.scrapy \
    && chown -R scraper:scraper /app

COPY --chown=scraper:scraper . /app
USER scraper
CMD ["scrapy", "list"]
