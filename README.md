# TCG Scraping

Socle gratuit **Scrapy + scrapy-playwright + Chromium**, exécuté dans un
conteneur Linux. Il fournit un exemple HTTP et JavaScript, des réglages de
crawl prudents, des tests et des commandes courtes.

Le spider `quotes` utilise un site prévu pour apprendre le scraping.
Le spider [`pokemon_jp`](docs/pokemon-jp.md) parcourt le catalogue officiel
japonais Pokémon : pagination, fiches de détail et export des caractéristiques.
Le spider [`pokemon_kr`](docs/pokemon-kr.md) fait de même pour le catalogue coréen,
en reproduisant les requêtes Recherche et « Charger plus » du site.
Le spider [`pokemon_id`](docs/pokemon-id.md) collecte les fiches indonésiennes
de TCG Collector à partir de ses sitemaps publics autorisés.
Le spider `pokemon_fr` découvre les extensions dans les filtres de l’encyclopédie
française de Pokémon.com et ouvre chaque fiche de carte.

Le modèle [`ItemPokemon`](docs/item-pokemon.md) sert aux
spiders de cartes : Pokémon, Dresseurs et Énergies, caractéristiques d'impression,
attaques, talents, variantes et formats anciens ou multiparties.
Le modèle [`ItemOnePiece`](docs/item-one-piece.md) décrit les impressions du
ONE PIECE CARD GAME, des Leaders bicolores aux DON!!, avec leurs effets,
illustrations alternatives et rééditions.
Le spider [`one_piece_jp`](docs/one-piece-jp.md) remplit cet item depuis le
catalogue officiel japonais avec les informations de la fiche, ses Q&A et
l’URL de son recto. À chaque lancement, il écrit `data/one_piece_jp.jsonl`.
Le spider `one_piece_fr` utilise le même modèle pour le catalogue français.
Il exporte chaque impression avec son texte français et l’URL officielle de
son recto. Il suit les dates de sortie françaises et inclut les promotions sans date.

Le modèle [`ItemMagic`](docs/item-magic.md) décrit les cartes Magic depuis Alpha.
Il conserve le texte imprimé et le texte Oracle, les variantes d'une même carte,
les caractéristiques de chaque face et les cartes liées, comme les jetons.
Le [spider Magic Scryfall](docs/magic-scryfall.md) remplit cet item depuis les exports
officiels de Scryfall pour toutes les éditions et langues répertoriées.

## Démarrer

Prérequis : Docker Engine avec Docker Compose, ou Docker Desktop configuré
pour les conteneurs Linux. Make est facultatif sous Windows.

```sh
make build
make crawl
make crawl-js
make check
```

Sous **PowerShell**, sans installer Make :

```powershell
.\make.ps1 build
.\make.ps1 crawl
.\make.ps1 crawl-js
.\make.ps1 check
```

Si la politique PowerShell empêche les scripts locaux, utilise directement
les commandes `docker compose` ci-dessous ; inutile de modifier cette politique.

Les résultats sont écrits dans `data/quotes.jsonl` et `data/quotes-js.jsonl`,
sur ta machine. Chaque lancement **remplace** le fichier correspondant.
La limite initiale est de **3 pages** ; les fichiers de données ne sont pas versionnés.

```sh
make crawl-js MAX_PAGES=2
make crawl ARGS='-s LOG_LEVEL=DEBUG'
```

```powershell
.\make.ps1 crawl-js -MaxPages 2
.\make.ps1 crawl -ExtraArgs @('-s', 'LOG_LEVEL=DEBUG')
```

## Commandes

| Make / `make.ps1` | Utilité |
| --- | --- |
| `help` | Afficher les commandes |
| `build` | Construire l'image et installer Chromium |
| `list` | Lister les spiders disponibles |
| `crawl` | Lancer l'exemple HTTP |
| `crawl-js` | Lancer l'exemple avec Chromium |
| `pokemon` | Échantillon Pokémon japonais, 3 pages par défaut |
| `pokemon-all` | Catalogue Pokémon complet, export cumulatif et reprise |
| `pokemon-kr` | Échantillon coréen, 3 lots par défaut |
| `pokemon-kr-all` | Catalogue coréen complet, export cumulatif et reprise |
| `pokemon-id` | Échantillon indonésien, 5 cartes par défaut |
| `pokemon-id-all` | Catalogue indonésien complet, export cumulatif et reprise |
| `pokemon-fr` | Échantillon français, 5 fiches par défaut |
| `pokemon-fr-all` | Toutes les extensions de l’encyclopédie française dans `data/pokemon_fr.jsonl` |
| `one-piece` | Catalogue japonais One Piece dans `data/one_piece_jp.jsonl` |
| `one-piece-fr` | Catalogue français One Piece dans `data/one_piece_fr.jsonl` |
| `magic` | Échantillon Scryfall, 5 impressions par défaut |
| `magic-all` | Catalogue Scryfall multilingue dans `data/magic_scryfall.jsonl` |
| `test` | Tester HTTP et Chromium sur un serveur local |
| `lint` | Vérifier Ruff et le formatage |
| `format` | Formater le Python |
| `check` | Lint puis tests |
| `shell` | Ouvrir un shell dans le conteneur |

Les commandes complètes restent disponibles :

```sh
docker compose build --pull
docker compose run --rm crawler scrapy list
docker compose run --rm crawler scrapy crawl quotes -a max_pages=3 -O data/quotes.jsonl
docker compose run --rm crawler scrapy crawl quotes -a javascript=true -O data/quotes-js.jsonl
docker compose run --rm crawler pytest -q
```

## Cartes One Piece françaises

Depuis la racine du projet, lance le catalogue complet avec Docker Compose.
Chaque lancement remplace `data/one_piece_fr.jsonl`, avec une ligne par impression.

```sh
docker compose run --rm crawler scrapy crawl one_piece_fr
```

Pour essayer une seule série, utilise le numéro du paramètre `series` de l’URL
Bandai. Par exemple, cette commande exporte le deck ST-15 dans un fichier séparé.

```sh
docker compose run --rm crawler scrapy crawl one_piece_fr -a series=622015 -O data/one_piece_fr_st15.jsonl
```

## Cartes Pokémon françaises

Pour parcourir toutes les extensions de l’[encyclopédie officielle](https://www.pokemon.com/fr/jcc-pokemon/cartes-pokemon),
lance cette commande depuis la racine du projet avec Docker démarré.

```powershell
.\make.ps1 pokemon-fr-all
```

L’équivalent direct est `docker compose run --rm crawler scrapy crawl pokemon_fr`.
Le spider suit les filtres d’extension, y compris les promotions et sous-collections
qui ont leur propre filtre. Il avance avec « Résultats suivants » et exporte une
ligne JSON par fiche dans `data/pokemon_fr.jsonl`. La première carte d’un nouveau
lancement remplace le contenu précédent de ce fichier.

Pour essayer cinq fiches de *Dragons Exaltés* dans `data/pokemon_fr-sample.jsonl` :

```powershell
.\make.ps1 pokemon-fr -MaxCards 5 -ExtraArgs @('-a', 'extension=bw6')
```

Le paramètre facultatif `extension` correspond au code du filtre dans l’URL de
recherche, par exemple `bw6` dans `?bw6=on`. L’export conserve le nom de l’extension
et de la série, le numéro imprimé, la rareté, l’illustrateur, l’URL du recto et celle
de la fiche. Selon la carte, il contient aussi les PV, le stade, l’évolution, les
types, les attaques et leurs coûts, les talents, faiblesses, résistances, le coût
de retraite, les règles et les textes des cartes Dresseur ou Énergie.

En cas de CAPTCHA, Scrapy termine avec `blocked_captcha`. Un export commencé
avant ce blocage contient uniquement les fiches déjà reçues.

### Compléter la collection avec les archives de Pokémon.com

Le spider `pokemon_fr_archives` lit les copies historiques de l’encyclopédie
française dans la Wayback Machine. Cette commande ajoute les cartes manquantes
à une collection locale. Relancer la même commande reprend à partir des
identifiants présents dans le JSONL et conserve les fiches déjà enregistrées.

```powershell
docker compose run --rm crawler scrapy crawl pokemon_fr_archives -o data/pokemon_fr_collection.jsonl
```

Pour compléter un export direct existant, indique son chemin après `-o`.
Utilise un seul processus par fichier. L’option `-O` demande un nouvel export
et remplace le fichier. Pour essayer dix fiches d’une seule extension :

```powershell
docker compose run --rm crawler scrapy crawl pokemon_fr_archives -a extension=bw6 -a max_cards=10
```

Chaque ligne porte l’URL Pokémon.com dans `source_url`. Une fiche archivée
porte aussi l’URL de la capture et son horodatage UTC (`YYYYMMDDhhmmss`)
dans `additional_attributes.archive`. Le spider essaie les captures de la
plus récente à la plus ancienne jusqu’à retrouver la bonne fiche. Certaines
cartes ou extensions manquent dans l’archive, et certaines captures ne
contiennent qu’une page de blocage. Les statistiques Scrapy comptent les
fiches indexées, déjà exportées et illisibles.

## Cartes Pokémon japonaises

Petit essai, limité à cinq fiches :

```powershell
.\make.ps1 pokemon -MaxPages 1 -ExtraArgs @('-a', 'max_cards=5')
```

```sh
make pokemon MAX_PAGES=1 ARGS='-a max_cards=5'
```

Pour toutes les pages et toutes les fiches, lancer `make pokemon-all` ou
`.\make.ps1 pokemon-all`. Le résultat s'ajoute à `data/pokemon_jp.jsonl`.
Un arrêt propre avec **Ctrl+C une seule fois**, puis la même commande, permet
de reprendre les requêtes en attente. Le catalogue comporte des dizaines de
milliers de fiches : prévoir plusieurs heures avec les délais actuels.
Les [options, champs collectés et limites de reprise](docs/pokemon-jp.md)
sont détaillés dans le guide.

## Cartes Pokémon coréennes

Le bouton Recherche et la pagination du site utilisent JavaScript, mais leurs
requêtes HTTP publiques suffisent au spider : aucun navigateur n'est nécessaire.

```powershell
# Petit essai : cinq cartes au maximum.
.\make.ps1 pokemon-kr -MaxPages 1 -ExtraArgs @('-a', 'max_cards=5')

# Toutes les cartes, avec reprise.
.\make.ps1 pokemon-kr-all
```

Équivalents Make : `make pokemon-kr MAX_PAGES=1 ARGS='-a max_cards=5'` et
`make pokemon-kr-all`. L'export complet est `data/pokemon_kr.jsonl`, avec son propre
état de reprise `data/jobs/pokemon_kr`. Voir le [guide coréen](docs/pokemon-kr.md).

## Cartes Pokémon indonésiennes

```powershell
# Cinq fiches dans data/pokemon_id-sample.jsonl.
.\make.ps1 pokemon-id

# Catalogue complet dans data/pokemon_id.jsonl, avec reprise.
.\make.ps1 pokemon-id-all
```

Équivalents Make : `make pokemon-id MAX_CARDS=5` et `make pokemon-id-all`.
TCG Collector interdit la pagination dans son robots.txt : le spider découvre
les fiches via ses sitemaps ID. Les textes du catalogue sont en anglais, même
pour les cartes indonésiennes ; le texte d'ambiance n'est pas fourni dans les
fiches examinées. Les dos génériques sont exclus des URLs de recto.
Voir le [guide indonésien](docs/pokemon-id.md) pour les champs, limites et commandes Docker.

## Configuration

Copie `.env.example` vers `.env` uniquement si tu souhaites modifier les valeurs.
Compose lit ce fichier automatiquement ; aucune clé API n'est nécessaire.

| Variable | Défaut | Effet |
| --- | --- | --- |
| `DOWNLOAD_DELAY` | `3` | Base du délai Scrapy, avec variation de ±50 % |
| `HTTP_CACHE` | `false` | Cache HTTP de développement, durée d'une heure |
| `LOG_LEVEL` | `INFO` | Niveau des journaux |
| `HTTP_USER_AGENT` | Identité stable du projet | User-Agent HTTP ; Chromium conserve le sien |
| `USER_UID` / `USER_GID` | `1000` / `1000` | Identité Linux du conteneur |

Sous Linux, renseigne ton UID/GID (`id -u`, `id -g`) s'ils diffèrent de 1000,
puis reconstruis l'image pour pouvoir écrire dans le dossier monté.

Les sources sont montées dans le conteneur : modifier un spider ne nécessite
pas de reconstruire l'image. Reconstruis après une modification des dépendances.

## Limiter les blocages

- HTTP suffit pour le HTML déjà rendu ; Chromium sert aux pages JavaScript.
- Une requête Scrapy par domaine, AutoThrottle, délais variables et pagination bornée.
- Un contexte Chromium conservé pendant le crawl, avec sa véritable version de navigateur.
- Images, médias et polices écartés ; scripts et appels nécessaires au rendu conservés.
- Arrêt sur **403 ou 429**, sans réessai ; `Retry-After` apparaît dans les logs.
- Respect de `robots.txt`, cache HTTP facultatif et pas de cache pour les pages Playwright.

Ces choix réduisent le trafic et les incohérences ; **ils ne rendent pas un bot
indétectable**. L'identité HTTP par défaut est explicite. Aucun proxy payant,
rotation d'IP, spoofing de fingerprint ou résolveur de CAPTCHA n'est nécessaire.
Le [guide de scraping](docs/scraping.md) détaille les limites et l'adaptation à un site.

## Contribuer

La branche `main` est protégée : les modifications passent par une pull request.
Le contrôle GitHub Actions `container` doit réussir et la branche doit être à jour
avec `main` avant fusion. Les conversations de revue doivent être résolues.
Ces règles s'appliquent également aux administrateurs ; les push forcés et la
suppression de `main` sont interdits.

Le dépôt ayant actuellement un seul contributeur, aucune approbation d'une seconde
personne n'est exigée. Les contrôles s'exécutent aussi pour les changements limités
à la documentation afin de ne pas bloquer leur fusion.

## Structure

```text
tcg_scraper/settings.py       Réglages et intégration Playwright
tcg_scraper/item_pokemon.py   Schéma des caractéristiques de cartes Pokémon
tcg_scraper/item_one_piece.py Schéma des caractéristiques de cartes One Piece
tcg_scraper/item_magic.py     Schéma des impressions et des faces de cartes Magic
tcg_scraper/middlewares.py    Identité HTTP, cache, arrêt sur blocage
tcg_scraper/spiders/quotes.py Exemple et pagination
tcg_scraper/spiders/pokemon_jp.py Catalogue Pokémon japonais et fiches
tcg_scraper/spiders/pokemon_kr.py Catalogue coréen, recherche AJAX et fiches
tcg_scraper/spiders/pokemon_id.py Catalogue indonésien, sitemaps et fiches
tests/                       Tests locaux HTTP, Chromium et commandes Windows
docker/                      Profil seccomp et licence amont
data/                        Exports non versionnés
requirements*.txt            Dépendances directes
requirements*.lock           Résolution Linux Python 3.13 verrouillée
```

L'image utilise Python 3.13 et les versions verrouillées des dépendances,
avec Chromium installé par Playwright 1.65.2. Le navigateur tourne sans root,
avec son sandbox et un profil seccomp explicite. L'image Python de base suit
les mises à jour du tag `3.13-slim-bookworm` ; ce n'est pas un build bit à bit figé.

## Développement sans Docker

Avec Python 3.13 installé :

```sh
python -m venv .venv
# Linux/macOS : source .venv/bin/activate
# Windows PowerShell : .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -m pytest -q
ruff check .
ruff format --check .
```

Sur Linux, `python -m playwright install --with-deps chromium` installe aussi
les dépendances système. Sous Windows, les appels au navigateur restent dans
des `PageMethod`, pour éviter les incompatibilités entre boucles asyncio.
Les tests accélèrent les délais **uniquement sur localhost**.

Pour renouveler les fichiers verrouillés avec l'outil gratuit `uv` :

```sh
uv pip compile requirements.txt --python-version 3.13 --python-platform x86_64-unknown-linux-gnu -o requirements.lock
uv pip compile requirements-dev.txt --python-version 3.13 --python-platform x86_64-unknown-linux-gnu -o requirements-dev.lock
make build
make check
```

## Windows : Virtual Machine Platform

Si Docker indique que cette fonctionnalité est absente, ouvre PowerShell en
administrateur et exécute :

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart
```

Enregistre ton travail puis **redémarre Windows**, pas seulement Docker Desktop.
Vérifie ensuite `wsl --status` et démarre Docker Desktop. Une virtualisation CPU
désactivée dans le BIOS/UEFI ou une politique d'entreprise peut aussi empêcher WSL.

## Coûts et vérifications

Scrapy, scrapy-playwright, Playwright, Python, pytest, Ruff et Make sont gratuits
et open source. Aucun abonnement, proxy ou service cloud n'est configuré, et
la CI utilise uniquement un runner Linux standard gratuit pour les dépôts publics.
Elle ne stocke ni cache ni artefact payant et se désactive si le dépôt devient privé.
Voir les [conditions GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
Docker Desktop a
ses propres [conditions de gratuité](https://docs.docker.com/subscription/desktop-license/) ;
Docker Engine reste une alternative libre sous Linux.

Voir [le compte rendu des vérifications](docs/validation.md) pour distinguer
les tests réellement exécutés de ceux qui attendent un moteur Docker fonctionnel.
