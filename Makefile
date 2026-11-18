.DEFAULT_GOAL := help
DC := docker compose
RUN := $(DC) run --rm crawler
SPIDER ?= quotes
MAX_PAGES ?= 3
ARGS ?=

.PHONY: help build list crawl crawl-js test lint format shell check

help:
	@echo "make build      - Construire l'image et installer Chromium"
	@echo "make list       - Lister les spiders"
	@echo "make crawl      - Exemple HTTP vers data/quotes.jsonl"
	@echo "make crawl-js   - Exemple JavaScript vers data/quotes-js.jsonl"
	@echo "make test       - Tests locaux HTTP et Chromium"
	@echo "make lint       - Ruff et verification du format"
	@echo "make format     - Formater le code Python"
	@echo "make shell      - Shell dans le conteneur"
	@echo "make check      - Lint puis tests"
	@echo "Options : SPIDER=quotes MAX_PAGES=3 ARGS='-s LOG_LEVEL=DEBUG'"

build:
	$(DC) build --pull

list:
	$(RUN) scrapy list

crawl:
	$(RUN) scrapy crawl $(SPIDER) -a max_pages=$(MAX_PAGES) -O data/$(SPIDER).jsonl $(ARGS)

crawl-js:
	$(RUN) scrapy crawl $(SPIDER) -a javascript=true -a max_pages=$(MAX_PAGES) -O data/$(SPIDER)-js.jsonl $(ARGS)

test:
	$(RUN) pytest -q

lint:
	$(RUN) ruff check .
	$(RUN) ruff format --check .

format:
	$(RUN) ruff format .

shell:
	$(RUN) /bin/bash

check: lint test
