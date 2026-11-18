# Socle de scraping

Projet neuf demandé le 18 novembre 2026 : Scrapy, scrapy-playwright, conteneur,
Makefile et nouveau dépôt GitHub. L'utilisateur privilégie la réduction des
blocages et confie les choix techniques à l'agent.

## Approche retenue

HTTP par défaut et Chromium à la demande. Tout passer par Chromium augmente
le nombre de requêtes et la consommation sans garantir l'indétectabilité.
HTTP seul ne couvre pas les pages rendues en JavaScript. Le mode hybride
conserve les sessions et évite les changements artificiels d'identité.

## Livrables et contraintes

- Python 3.13, Scrapy 2.20.0, scrapy-playwright 0.0.48, Playwright 1.65.2.
- Image Linux avec Chromium installé par la même version de Playwright,
  utilisateur non-root, sandbox Chromium et profil seccomp officiel.
- Spider de démonstration `quotes`, modes HTTP et JavaScript, pagination
  bornée à 3 pages par défaut, export JSONL hors du conteneur.
- Respect de robots.txt, 1 requête par domaine, délai de base de 3 secondes
  avec variation, AutoThrottle, retries limités aux erreurs temporaires.
- Arrêt sur HTTP 403/429, signalement du Retry-After, pas de relance en boucle.
- Cache HTTP de développement optionnel, désactivé par défaut pour les prix.
- Chromium conserve une identité native et un contexte de session par crawl.
  Les médias inutiles sont bloqués ; les requêtes internes du navigateur
  ne passent pas par le limiteur Scrapy (limite documentée).
- Exemples sur quotes.toscrape.com, tests locaux sans solliciter de sites tiers.
- Makefile et équivalent PowerShell pour Windows sans Make installé.
- README et guide de scraping en français. Aucun proxy ni service payant.
- Dépôt `kederiku/tcg-scraping`, branche main, commit et push demandés.
  Privé recommandé initialement ; l'utilisateur a créé le dépôt public et fourni son URL.
- CI sur runner Linux standard GitHub Actions, gratuite pour ce dépôt public,
  avec condition désactivant le job si le dépôt devient privé ; aucun stockage d'artefact.

## Validation

Tests de bout en bout sur serveur HTTP local : extraction, pagination,
limite de pages, rendu JavaScript, robots.txt et blocages 403/429.
Lint et formatage Ruff ; validation de Compose. Construction et tests Docker
si le moteur est disponible.

## État de l'hôte

Docker Desktop est installé mais Virtual Machine Platform est désactivé.
L'utilisateur autorise son activation sans redémarrer. Les tests Python et
Chromium peuvent être exécutés sur Windows ; la validation réelle du conteneur
exige un moteur Linux fonctionnel après redémarrage.

## Limites

Ce socle ne contient pas encore de spider propre à un marchand TCG.
Aucune garantie d'indétectabilité, aucun contournement de CAPTCHA ni d'accès.
Les décisions d'architecture ci-dessus sont celles de l'agent.
