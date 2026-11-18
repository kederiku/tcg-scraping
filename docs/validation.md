# Vérifications du 18 novembre 2026

## Résultats obtenus

- 13 tests de bout en bout passent sur Windows : extraction HTTP et Chromium,
  pagination, limite de pages, robots.txt, arrêts 403/429 et arguments invalides.
- Tests du wrapper PowerShell : commandes transmises et arrêt dès une erreur Docker.
- `ruff check tcg_scraper tests` et `ruff format --check tcg_scraper tests` : succès.
- `docker compose config --quiet` : configuration valide.
- Aucun crawl de marchand ou de site tiers n'a été lancé pendant ces tests.

## Hôte

Windows, Python 3.13.18, Chromium installé par Playwright 1.65.2.
Les dépendances du conteneur sont verrouillées pour Linux/Python 3.13.

Virtual Machine Platform a été activée avec `-NoRestart` à la demande de
l'utilisateur. Windows a retourné `RestartNeeded: true`. Le redémarrage
reste à effectuer par l'utilisateur.

L'environnement Python utilisé pour la suite finale a été réinstallé depuis les
paquets officiels après qu'un premier passage de Ruff a parcouru des outils
temporaires. Ces dossiers sont désormais explicitement exclus du lint et de Git.

## Validation Docker à effectuer après redémarrage

```powershell
.\make.ps1 build
.\make.ps1 check
.\make.ps1 crawl
.\make.ps1 crawl-js
```

Le build Linux et l'exécution dans le conteneur ne sont pas validés tant que
Docker Desktop n'a pas démarré. Les tests Windows ne remplacent pas cette vérification.
