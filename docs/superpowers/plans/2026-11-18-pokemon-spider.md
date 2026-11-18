# Plan : catalogue Pokémon japonais

Spec : `docs/superpowers/specs/2026-11-18-pokemon-spider-design.md`.

Conserver les modifications ItemPokemon existantes dans le checkout courant.
Exécution directe avec les compétences Superpowers, tests avant implémentation,
puis revue indépendante. Pas de publication GitHub demandée pour cette modification.

## Tâche 1 — Spider et extraction

- [x] Écrire les contrats de parsing, pagination, limites et erreurs dans
  `tests/test_pokemon_jp.py`, avec fixtures synthétiques HTML.
- [x] Observer leur échec, puis créer `tcg_scraper/spiders/pokemon_jp.py`.
- [x] Vérifier les contrats avec pytest ; résultat attendu : tout passe.

## Tâche 2 — Commandes et utilisation

- [x] Ajouter les tests PowerShell des commandes `pokemon` et `pokemon-all`.
- [x] Ajouter les deux commandes dans Makefile et make.ps1, documenter le spider
  et la reprise JOBDIR. Le mode complet ajoute au JSONL au lieu de l'écraser.
- [x] Vérifier le wrapper ; résultat attendu : tous les arguments sont corrects.

## Tâche 3 — Vérifications finales

- [x] Crawl local sur deux pages et plusieurs catégories, erreurs et doublons.
- [x] Échantillon réel borné, contrôle des données et de la pagination publique.
- [x] Ruff, format, suite complète et revue indépendante, corrections si nécessaire.

## Points de revue

Pagination répétée/invalide, export partiel présenté comme complet, limites sur les
requêtes et non seulement les items, attribution erronée des règles/énergies, fuite
du texte de navigation dans raw_text, confusion logo de set/marque de régulation,
reprise avec JOBDIR et écrasement accidentel des données.

## Journal de validation

- RED : module vide, 20 contrats échouent (spider absent), puis implémentation.
- GREEN : 20 contrats passent ; correction des assertions d'arrêt pour utiliser
  `CloseSpider.reason` (le message de cette exception Scrapy est vide).
- RED commandes : `pokemon` rejeté par le wrapper ; GREEN après ajout des cibles.
- Suite complète : **43 tests passent**, 117,04 s, Python local/Chromium installé,
  avec serveurs locaux. Le wrapper PowerShell passe également.
- Ruff : lint réussi, 23 fichiers formatés. Le formatteur a également normalisé
  l'exemple Python préexistant de `docs/item-pokemon.md`.
- Échantillon réel : 3 cartes, 5 requêtes (robots.txt 404, 1 liste, 3 fiches),
  arrêt `finished`, aucun téléchargement d'image. Illustrateurs et URLs vérifiés.
- Reconnaissance : pages publiques 1 et 2 lues ; toutes deux annoncent 604 pages.
  Cinq formats de fiches réelles vérifiés en parsing local, dont Énergie spéciale.
- Revue indépendante : cinq défauts reproduits par des tests puis corrigés :
  pagination répétée/tronquée, écrasement de l'export par `crawl`, budget de reprise
  réinitialisé, provenance promotionnelle confondue avec le nom du set et commentaire
  HTML faisant échouer l'extraction. L'état JOBDIR conserve désormais les IDs/pages,
  la pagination vérifie les plages et le cardinal final, et toute erreur de callback
  interrompt le spider (`CLOSESPIDER_ERRORCOUNT=1`).
- Après correction : 27 contrats unitaires et tests PowerShell passent. Un nouvel
  échantillon réel de 3 cartes de la page 2 passe (5 requêtes, 23,83 s, `finished`).
  La suite complète a ensuite donné 52 succès et un échec d'assertion dans le test
  d'erreur injectée : Scrapy retourne correctement 1, alors que le test attendait 0.
  Après correction de cette assertion, les 7 tests d'intégration passent (59,17 s),
  dont les deux reprises JOBDIR et l'erreur injectée. Aucun changement de production
  entre ces deux vérifications. Les 53 cas sont ainsi vérifiés, ainsi que Ruff et
  le wrapper PowerShell. Aucun constat de revue restant ouvert.
- Docker local : `docker version` confirme que Docker Desktop ne peut toujours pas
  démarrer. Ce spider a été testé avec Python local ; aucune nouvelle validation
  dans le conteneur ni publication GitHub n'a été effectuée.
- Vérification avant commit demandée par l'utilisateur : nouvelle suite complète,
  **53 tests réussis en 148,76 s** ; Ruff et tests PowerShell réussis également.
