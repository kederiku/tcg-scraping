# Plan d'implémentation Pokémon ID

Spec : `docs/superpowers/specs/2026-11-18-pokemon-id-spider.md`.
Exécution inline avec Superpowers, sur `codex/pokemon-id-spider`.

## Contraintes

Réutiliser ItemPokemon et les politiques réseau existantes, sans dépendance.
Ne jamais parcourir la pagination ou l'API interdites. Préserver JP/KR,
les exports existants et le checkout courant. Aucun commit/push prévu.

## Tâche 1 — Découverte et extraction

Écrire des tests synthétiques de sitemap et de fiches Pokémon/Dresseur/Énergie.
Constater leur échec avant création du module. Implémenter la découverte limitée
aux sitemaps indonésiens, le budget persistant, la validation de région et les
champs observés. Vérifier champs manquants, symboles, variantes et erreurs.
Commande : `python -m pytest tests/test_pokemon_id.py -q -p no:cacheprovider`.

## Tâche 2 — Parcours réel et commandes

Écrire un serveur HTTP de test couvrant sitemaps multiples, déduplication,
robots, limites, interruption/reprise et erreurs. Exécuter le spider en
sous-processus. Ajouter les commandes Make/PowerShell et leurs tests avant
implémentation. Limiter l'essai à `max_cards=5`; le complet utilise un JOBDIR
dédié et `-o`. Ajouter le guide et les références README.

## Tâche 3 — Vérification et revue

Exécuter Ruff, les tests PowerShell et toute la suite dans Docker. Vérifier
quelques fiches réelles avec les délais normaux et un export de scratch.
Effectuer une revue indépendante unique du diff complet, corriger les défauts
importants avec test de régression et vérifier les changements. Mettre à jour
les preuves dans le guide et le journal. Laisser les modifications disponibles
localement pour l'utilisateur.
