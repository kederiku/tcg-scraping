.DEFAULT_GOAL := help
DC := docker compose
RUN := $(DC) run --rm crawler
SPIDER ?= quotes
MAX_PAGES ?= 3
MAX_CARDS ?= 5
ARGS ?=

.PHONY: help build list crawl crawl-js pokemon pokemon-all pokemon-kr pokemon-kr-all pokemon-id pokemon-id-all pokemon-fr pokemon-fr-all one-piece one-piece-fr magic magic-all test lint format shell check

help:
	@echo "make build      - Construire l'image et installer Chromium"
	@echo "make list       - Lister les spiders"
	@echo "make crawl      - Exemple HTTP vers data/quotes.jsonl"
	@echo "make crawl-js   - Exemple JavaScript vers data/quotes-js.jsonl"
	@echo "make pokemon    - Echantillon Pokemon japonais (MAX_PAGES=3)"
	@echo "make pokemon-all - Catalogue Pokemon complet, avec reprise"
	@echo "make pokemon-kr - Echantillon Pokemon coreen (MAX_PAGES=3)"
	@echo "make pokemon-kr-all - Catalogue coreen complet, avec reprise"
	@echo "make pokemon-id - Echantillon indonesien (MAX_CARDS=5)"
	@echo "make pokemon-id-all - Catalogue indonesien complet, avec reprise"
	@echo "make pokemon-fr - Echantillon Pokemon francais (MAX_CARDS=5)"
	@echo "make pokemon-fr-all - Toutes les extensions de l'encyclopedie francaise"
	@echo "make one-piece  - Catalogue japonais One Piece vers data/one_piece_jp.jsonl"
	@echo "make one-piece-fr - Catalogue francais One Piece vers data/one_piece_fr.jsonl"
	@echo "make magic      - Echantillon Magic Scryfall (MAX_CARDS=5)"
	@echo "make magic-all  - Catalogue Magic Scryfall complet vers data/magic_scryfall.jsonl"
	@echo "make test       - Tests locaux HTTP et Chromium"
	@echo "make lint       - Ruff et verification du format"
	@echo "make format     - Formater le code Python"
	@echo "make shell      - Shell dans le conteneur"
	@echo "make check      - Lint puis tests"
	@echo "Options : SPIDER=quotes MAX_PAGES=3 MAX_CARDS=5 ARGS='-s LOG_LEVEL=DEBUG'"

build:
	$(DC) build --pull

list:
	$(RUN) scrapy list

ifeq ($(SPIDER),magic_scryfall)
crawl: magic

crawl-js:
	$(error Utilisez make crawl SPIDER=magic_scryfall pour ce spider HTTP)
else
crawl:
	$(RUN) scrapy crawl $(SPIDER) -a $(if $(filter pokemon_id pokemon_fr,$(SPIDER)),max_cards=$(MAX_CARDS),max_pages=$(MAX_PAGES)) -O $(if $(filter pokemon_jp pokemon_kr pokemon_id pokemon_fr,$(SPIDER)),data/$(SPIDER)-sample.jsonl,data/$(SPIDER).jsonl) $(ARGS)

crawl-js:
	$(RUN) scrapy crawl $(SPIDER) -a javascript=true -a $(if $(filter pokemon_id,$(SPIDER)),max_cards=$(MAX_CARDS),max_pages=$(MAX_PAGES)) -O data/$(SPIDER)-js.jsonl $(ARGS)
endif

pokemon:
	$(RUN) scrapy crawl pokemon_jp -a max_pages=$(MAX_PAGES) -O data/pokemon_jp-sample.jsonl $(ARGS)

pokemon-all:
	$(RUN) scrapy crawl pokemon_jp -a max_pages=0 -s JOBDIR=data/jobs/pokemon_jp -o data/pokemon_jp.jsonl $(ARGS)

pokemon-kr:
	$(RUN) scrapy crawl pokemon_kr -a max_pages=$(MAX_PAGES) -O data/pokemon_kr-sample.jsonl $(ARGS)

pokemon-kr-all:
	$(RUN) scrapy crawl pokemon_kr -a max_pages=0 -s JOBDIR=data/jobs/pokemon_kr -o data/pokemon_kr.jsonl $(ARGS)

pokemon-id:
	$(RUN) scrapy crawl pokemon_id -a max_cards=$(MAX_CARDS) -O data/pokemon_id-sample.jsonl $(ARGS)

pokemon-id-all:
	$(RUN) scrapy crawl pokemon_id -a max_cards=0 -s JOBDIR=data/jobs/pokemon_id -o data/pokemon_id.jsonl $(ARGS)

pokemon-fr:
	$(RUN) scrapy crawl pokemon_fr -a max_cards=$(MAX_CARDS) -O data/pokemon_fr-sample.jsonl $(ARGS)

pokemon-fr-all:
	$(RUN) scrapy crawl pokemon_fr $(ARGS)

one-piece:
	$(RUN) scrapy crawl one_piece_jp $(ARGS)

one-piece-fr:
	$(RUN) scrapy crawl one_piece_fr $(ARGS)

magic:
	$(RUN) scrapy crawl magic_scryfall -a max_cards=$(MAX_CARDS) $(ARGS)

magic-all:
	$(RUN) scrapy crawl magic_scryfall $(ARGS)

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
