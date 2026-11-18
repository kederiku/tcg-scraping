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

Le modèle [`ItemPokemon`](docs/item-pokemon.md) sert aux
spiders de cartes : Pokémon, Dresseurs et Énergies, caractéristiques d'impression,
attaques, talents, variantes et formats anciens ou multiparties.

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

## Structure

```text
tcg_scraper/settings.py       Réglages et intégration Playwright
tcg_scraper/item_pokemon.py   Schéma des caractéristiques de cartes Pokémon
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
