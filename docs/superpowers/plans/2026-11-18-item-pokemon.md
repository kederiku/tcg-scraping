# ItemPokemon Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution.

**Goal:** Fournir un schéma extensible des caractéristiques de cartes physiques Pokémon.
**Architecture:** Un `scrapy.Item` facultatif, descriptions/types dans les métadonnées,
dictionnaires et listes JSON pour les structures répétées. Aucune conversion automatique.
**Tech Stack:** Scrapy existant, ItemAdapter, exporteur JSONL, pytest et Ruff existants.
**Spec:** `docs/superpowers/specs/2026-11-18-item-pokemon-design.md`.

## Global Constraints

Aucune dépendance ajoutée. Aucun champ de vente. Noms Python en anglais,
documentation française. Travail dans le checkout courant propre.

## Review Focus

Valeurs `30+`, `×2`, `?` et numéros préfixés ; listes non tronquées ; données
inconnues distinctes de zéro ; parties LEGEND/V-UNION ; types futurs non bloqués.

## Task 1: Schéma et documentation

Fichiers : `tcg_scraper/item_pokemon.py`, `tests/test_item_pokemon.py`,
`docs/item-pokemon.md`, `README.md`.

- [x] Définir les contrats d'export des cartes partielles et complexes, puis
      constater l'échec en l'absence du module.
- [x] Déclarer `ItemPokemon` et ses champs documentés, sans constructeur personnalisé.
- [x] Vérifier les exports par `python -m pytest tests/test_item_pokemon.py -q`.
- [x] Documenter les sous-structures et l'import dans un futur spider.
- [x] Exécuter la suite complète et Ruff ; revue indépendante puis corrections utiles.
