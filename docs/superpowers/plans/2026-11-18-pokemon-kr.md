# Pokemon Korean catalogue implementation plan

> Execution: `superpowers:executing-plans`, inline implementation and final independent review.

**Goal:** Collect the Korean public catalogue and details into `ItemPokemon`.
**Architecture:** POST the search/load-more AJAX request, follow detail URLs, export JSONL.
**Tech stack:** Existing Scrapy, pytest, Docker and PowerShell; no new dependencies.
**Spec:** `docs/superpowers/specs/2026-11-18-pokemon-kr-design.md`.

## Global constraints

Keep Japanese data and code intact. HTTP delays, robots and block-stop policy apply.
Use `language=ko`, `region=KR`, source-prefixed IDs and source labels in Korean.
Keep full and sample exports separate; preserve job state and POST fields on resume.

## Review focus

- A zero result means end only for a valid response, not an error or failed search.
- Offset/cursor repetition and cardinal mismatch cannot silently complete a catalogue.
- JSON object keys and image-only energy symbols must not lose cards or meaning.
- Promotion links, rarity and regulation logos must not be confused with set metadata.
- A generic or sample command must not overwrite the full export or Japanese data.

## Task 1 — Parser and pagination

- [x] Add synthetic contracts in `tests/test_pokemon_kr.py`, observe RED.
- [x] Implement `tcg_scraper/spiders/pokemon_kr.py`: AJAX POST, cursor validation,
  persistent scheduling limits, detail parsing and safe failure reasons. Confirm GREEN.

## Task 2 — Commands and integration

- [x] Add failing PowerShell expectations, then `pokemon-kr` / `pokemon-kr-all` targets.
- [x] Add `tests/test_pokemon_kr_crawl.py`: local POST catalogue, details, empty terminal
  lot, block/error, limits, JOBDIR pause/resume. Run inside Docker, expect all passing.
- [x] Document commands and limitations in `docs/pokemon-kr.md` and README.

## Task 3 — Final verification

- [x] Run complete suite, Ruff and PowerShell tests. Run a bounded live sample.
- [x] Independent review, reproduce/correct important findings and update validation.

## Ledger

Research: robots allows `/`; HTTP AJAX works with the standard request header.
First two lots each contain 30 cards, cursor 1 then 2; empty search returns count 0.
Docker Engine is now available locally (29.9.3), unlike the earlier Japanese task.

- RED: 24 contracts failed with the empty spider module; GREEN: all 24 passed.
- RED commands: PowerShell rejected `pokemon-kr`; GREEN: new commands and protected
  generic output passed. No Japanese code or data changed.
- Docker revealed a preexisting console-pytest import failure for package imports.
  Added `pythonpath = ["."]` to pytest configuration; the full 85-case Docker suite
  then passed in 195.57 seconds. Validation disables pytest's optional disk cache
  because the existing Windows cache directory is not writable by the container user.
- Live Docker sample: three cards from batch 2, five successful HTTP requests,
  `finished` in 20 seconds. Korean language/region, artists and image URLs checked.
- Independent review found malformed JSON coercion, missing Trainer/Energy subtypes
  and missing older printed species. Ten new RED contracts reproduced these and an
  empty-category error; after fixes, all 34 Korean unit contracts pass.
- Final complete Docker suite: **95 tests pass in 200.28 seconds**. Docker lint and
  PowerShell command tests also pass. Official regression cards BS2023022060 and
  BS2022017022 were rechecked successfully after the fixes. No review finding remains
  open. No commit or push requested.
