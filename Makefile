.DEFAULT_GOAL := help
DC := docker compose
RUN := $(DC) run --rm crawler
SPIDER ?= quotes
MAX_PAGES ?= 3
ARGS ?=

.PHONY: help build list crawl crawl-js pokemon pokemon-all pokemon-kr pokemon-kr-all test lint format shell check

help:
	@echo "make build      - Construire l'image et installer Chromium"
	@echo "make list       - Lister les spiders"
	@echo "make crawl      - Exemple HTTP vers data/quotes.jsonl"
	@echo "make crawl-js   - Exemple JavaScript vers data/quotes-js.jsonl"
	@echo "make pokemon    - Echantillon Pokemon japonais (MAX_PAGES=3)"
	@echo "make pokemon-all - Catalogue Pokemon complet, avec reprise"
	@echo "make pokemon-kr - Echantillon Pokemon coreen (MAX_PAGES=3)"
	@echo "make pokemon-kr-all - Catalogue coreen complet, avec reprise"
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
	$(RUN) scrapy crawl $(SPIDER) -a max_pages=$(MAX_PAGES) -O $(if $(filter pokemon_jp pokemon_kr,$(SPIDER)),data/$(SPIDER)-sample.jsonl,data/$(SPIDER).jsonl) $(ARGS)

crawl-js:
	$(RUN) scrapy crawl $(SPIDER) -a javascript=true -a max_pages=$(MAX_PAGES) -O data/$(SPIDER)-js.jsonl $(ARGS)

pokemon:
	$(RUN) scrapy crawl pokemon_jp -a max_pages=$(MAX_PAGES) -O data/pokemon_jp-sample.jsonl $(ARGS)

pokemon-all:
	$(RUN) scrapy crawl pokemon_jp -a max_pages=0 -s JOBDIR=data/jobs/pokemon_jp -o data/pokemon_jp.jsonl $(ARGS)

pokemon-kr:
	$(RUN) scrapy crawl pokemon_kr -a max_pages=$(MAX_PAGES) -O data/pokemon_kr-sample.jsonl $(ARGS)

pokemon-kr-all:
	$(RUN) scrapy crawl pokemon_kr -a max_pages=0 -s JOBDIR=data/jobs/pokemon_kr -o data/pokemon_kr.jsonl $(ARGS)

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
