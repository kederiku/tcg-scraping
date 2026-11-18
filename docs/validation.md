# Vérifications du 18 novembre 2026

## Résultats obtenus

- 13 tests de bout en bout passent sur Windows : extraction HTTP et Chromium,
  pagination, limite de pages, robots.txt, arrêts 403/429 et arguments invalides.
- Tests du wrapper PowerShell : commandes transmises et arrêt dès une erreur Docker.
- `ruff check tcg_scraper tests` et `ruff format --check tcg_scraper tests` : succès.
- `docker compose config --quiet` : configuration valide.
- Aucun crawl de marchand ou de site tiers n'a été lancé pendant ces tests.

## Conteneur Linux validé

La [CI GitHub Actions](https://github.com/kederiku/tcg-scraping/actions/runs/44276131348)
s'est terminée avec succès sur le commit
`b6ca61068c22c7c2abd0dc6f50eb465aaa29b66a` :

- Construction de l'image Python 3.13 avec Chromium : succès.
- Ruff et formatage exécutés dans le conteneur : succès.
- **13 tests HTTP/Chromium dans le conteneur : succès en 19,91 secondes.**
- Wrapper PowerShell : succès sous le shell utilisé par GitHub Actions.
- Chromium lancé sans root avec `chromium_sandbox=True` et le profil seccomp fourni.

Le premier build a révélé l'absence de `libatomic1` dans l'image Python minimale.
Le Dockerfile installe désormais cette bibliothèque avant de lancer l'installateur
de navigateurs Playwright. Le second build et toute la suite sont passés.

Une revue indépendante a également fait corriger l'exclusion des fichiers
`playwright/.auth/` du contexte Docker et le code de sortie du test PowerShell.
Elle n'a laissé aucun défaut critique ou important ouvert.

## Hôte

Windows, Python 3.13.18, Chromium installé par Playwright 1.65.2.
Les dépendances du conteneur sont verrouillées pour Linux/Python 3.13.

Virtual Machine Platform a été activée avec `-NoRestart` à la demande de
l'utilisateur. Windows avait retourné `RestartNeeded: true` et Docker était
alors indisponible. Le moteur fonctionne désormais ; voir la validation coréenne ci-dessous.

L'environnement Python utilisé pour la suite finale a été réinstallé depuis les
paquets officiels après qu'un premier passage de Ruff a parcouru des outils
temporaires. Ces dossiers sont désormais explicitement exclus du lint et de Git.

## Lancement local après redémarrage

```powershell
.\make.ps1 build
.\make.ps1 check
.\make.ps1 crawl
.\make.ps1 crawl-js
```

Le build Linux et l'exécution du conteneur sont validés par la CI ci-dessus.
Le lancement sur ce PC Windows a ensuite été vérifié lors de l'ajout du spider coréen.

## Ajout ItemPokemon et spider pokemon_jp

Vérifications locales de la modification non publiée :

- `ItemPokemon` : 6 tests de schéma et de sérialisation.
- Spider japonais : 27 contrats unitaires et 7 tests de crawl local, dont pagination,
  doublons, limites, erreurs 429/JSON, arrêt sur erreur de parsing et deux reprises
  JOBDIR réelles. Les 13 tests HTTP/Chromium précédents passent également.
- Vérification complète avant commit : **53 tests réussis en 148,76 s**,
  après correction de l'assertion du test d'erreur injectée pour attendre le
  code de sortie non nul de Scrapy.
- `ruff check .`, `ruff format --check .` et tests PowerShell : succès.
- Revue indépendante : cinq défauts reproduits et corrigés (pagination, protection
  de l'export, budget de reprise, provenance promotionnelle, commentaires HTML).
- Essais réels bornés : trois cartes de la première page, puis trois cartes de
  la deuxième page avec la version corrigée. Chaque essai utilise cinq requêtes
  (robots.txt, liste, trois fiches) ; illustrateurs et URLs d'images contrôlés.
  La dernière exécution se termine avec `finished` en 23,83 secondes.
- Parsing local de cinq fiches officielles préalablement consultées : Pokémon,
  Méga Pokémon avec talent, Dresseur, Énergie de base et Énergie spéciale.

Le catalogue complet n'a pas été collecté. Aucune image n'a été téléchargée.
Lors de cette validation, Docker Desktop retournait `Docker Desktop is unable to start` :
la validation japonaise ci-dessus utilise Python/Chromium locaux. La CI Linux citée plus
haut valide le socle initial, pas encore cette modification.

## Ajout du spider pokemon_kr

Docker Engine 29.9.3 est désormais disponible sur ce PC. Les vérifications coréennes
utilisent le conteneur du projet, sans reconstruire l'image ni ajouter de dépendance.

- Requêtes officielles vérifiées : Recherche vide, deuxième lot et recherche vide de
  résultats. L'API fournit un objet indexé à partir de 1, puis un tableau vide en fin.
  L'en-tête AJAX standard est requis ; aucun navigateur ni cookie n'est nécessaire.
- Premier passage complet dans Docker après configuration du chemin d'import pytest :
  **85 tests passent en 195,57 s**. La configuration `pythonpath = ["."]` corrige un
  problème préexistant de la commande console `pytest`, que `python -m pytest` masquait.
- Revue indépendante : réponses AJAX malformées, sous-types Dresseur/Énergie et
  catégorie Pokédex ancienne corrigés. Dix régressions ajoutées, toutes passantes,
  dont une garde sur une catégorie de carte vide : **34 contrats unitaires coréens**.
- Vérification finale après ces corrections : **95 tests réussis dans Docker en
  200,28 s**, incluant les tests japonais existants et les reprises JOBDIR des deux sites.
- `make.ps1 lint` dans Docker, Ruff local et tests du wrapper PowerShell : succès.
- Essai réel dans Docker : **3 cartes du deuxième lot**, cinq requêtes HTTP réussies
  (robots.txt, POST de recherche, trois fiches), `finished` en 20 secondes.
  Langue/région coréennes, illustrateurs et URLs d'images contrôlés.
- Parsing de cinq formats réels, puis vérification des deux fiches de régression :
  [Dresseur Futur](https://pokemoncard.co.kr/cards/detail/BS2023022060) et
  [ancienne carte avec catégorie Pokédex](https://pokemoncard.co.kr/cards/detail/BS2022017022).

Les données de test restent dans `.tools/pokemon-kr` ; les données japonaises n'ont
pas été modifiées. Aucune collecte complète ni aucun téléchargement d'image n'a été
lancé. Les tests automatisés utilisent uniquement des serveurs locaux. Le cache
optionnel de pytest est désactivé pour ces vérifications Docker, car le dossier de
cache préexistant sous Windows n'est pas accessible en écriture à l'utilisateur du conteneur.
