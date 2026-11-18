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

## Ajout du spider pokemon_id

Source : catalogue indonésien de TCG Collector, vérifié le 18 novembre 2026.

- Robots.txt interdit la pagination et `/api/`. L'index public donne trois sitemaps
  de cartes ID : 5 000 + 5 000 + 4 004 entrées, 14 004 IDs uniques sur l'origine
  attendue, correspondant au compteur de recherche. Les liens ont tous été validés
  hors ligne ; seule une poignée de fiches a été téléchargée.
- Essai réel dans Docker : **3 cartes**, sept réponses HTTP 200 (deux robots.txt,
  index, sitemap ID1 et trois fiches), fermeture `finished` en **27,26 secondes**.
  IDs, langue/région, illustrateurs et exclusion des images génériques vérifiés.
- Navigation manuelle vérifiée pour Fiery Flint 221/183 : le dos `default-card-image`
  est bien une image de remplacement du site, également visible depuis la recherche.
- Premier passage Docker : **128 tests réussis en 188,51 secondes**.
- Revue indépendante : quatre corrections avec régressions reproduites avant
  correction : structure `provided_energy`, structure commune `text_blocks`,
  attaque gratuite sans zone énergie et compatibilité des paramètres positionnels
  PowerShell. Les contrats unitaires indonésiens passent désormais au nombre de 30,
  en plus des huit parcours HTTP locaux (limites, erreurs, blocages et deux reprises).
- Après corrections, parsing vérifié sur cinq fiches réelles conservées en scratch :
  [Exeggcute 89967](https://www.tcgcollector.com/cards/89967/exeggcute-30th-celebration-001-130),
  [Fiery Flint 80454](https://www.tcgcollector.com/cards/80454/fiery-flint-hidden-shadow-set-a-221-183),
  [Greninja-GX 80456](https://www.tcgcollector.com/cards/80456/greninja-gx-hidden-shadow-set-a-212-183),
  [Water Energy 75496](https://www.tcgcollector.com/cards/75496/water-energy-silver-lance-095-070)
  et [Alolan Rattata 79650](https://www.tcgcollector.com/cards/79650/alolan-rattata-sky-ruler-set-a-106-178).
  Les coûts gratuits et payants, rectos réels, champs partagés et types d'énergie
  fournis ont été contrôlés sur ces réponses.
- Ruff (`check` et `format --check`) et les tests PowerShell passent.
- Vérification finale après toutes les corrections : **133 tests réussis dans Docker
  en 156,54 secondes**, incluant les spiders japonais/coréen et les parcours Chromium.

Les limites de la source sont décrites dans [le guide indonésien](pokemon-id.md) :
textes anglais, texte d'ambiance non fourni dans les fiches examinées, finitions
regroupées par fiche, images parfois manquantes. Le tri est celui des sitemaps.
La reprise après arrêt brutal n'est pas garantie ; les tests vérifient l'arrêt propre.
Les fichiers de travail restent dans `.tools/pokemon-id`. Aucune collecte complète,
aucun téléchargement d'image et aucune modification des exports JP/KR n'ont eu lieu.
Ces résultats concernent les vérifications locales effectuées avant publication sur GitHub.
