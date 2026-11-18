# Cartes Pokémon indonésiennes — TCG Collector

Le spider `pokemon_id` collecte les caractéristiques des fiches indonésiennes
de [TCG Collector](https://www.tcgcollector.com/cards/id?releaseDateOrder=newToOld&displayAs=images)
dans `ItemPokemon`. Aucun compte, abonnement, API payante ou navigateur requis.
Les images sont enregistrées sous forme d'URLs, sans télécharger leurs fichiers.

## Démarrer avec Docker

Depuis le dossier du projet, Docker Desktop démarré :

```powershell
# Essai de cinq cartes, remplace uniquement le fichier d'échantillon.
.\make.ps1 pokemon-id

# Choisir la taille de l'essai.
.\make.ps1 pokemon-id -MaxCards 10

# Catalogue complet, export cumulatif et reprise.
.\make.ps1 pokemon-id-all
```

Équivalents Make :

```sh
make pokemon-id MAX_CARDS=5
make pokemon-id-all
```

Commandes Docker directes :

```sh
docker compose run --rm crawler scrapy crawl pokemon_id -a max_cards=5 -O data/pokemon_id-sample.jsonl
docker compose run --rm crawler scrapy crawl pokemon_id -a max_cards=0 -s JOBDIR=data/jobs/pokemon_id -o data/pokemon_id.jsonl
```

Les sources sont montées dans le conteneur ; il n'est pas nécessaire de
reconstruire une image déjà fonctionnelle. Pour une première installation,
lancer `.\make.ps1 build` / `make build`.

## Découverte des cartes

Le [robots.txt du site](https://www.tcgcollector.com/robots.txt) interdit
`/api/` et les URLs avec `?page=` ou `&page=`. Le spider utilise donc
l'[index public des sitemaps](https://static.tcgcollector.com/sitemaps/sitemap.xml),
puis uniquement les fichiers `sitemap-cards-idN.xml` et les fiches qu'ils listent.
Il ne suit ni les sitemaps JP/KR/internationaux ni les liens de recherche des fiches.

Le 18 novembre 2026, les trois sitemaps ID contenaient 5 000 + 5 000 + 4 004
URLs distinctes, soit les 14 004 cartes annoncées par la recherche. Ce nombre
peut évoluer ; les nouveaux fichiers ID sont découverts automatiquement.
La couverture dépend de la mise à jour des sitemaps par le site.
**L'ordre est celui des sitemaps**, pas le tri « nouveautés d'abord » de la recherche.
L'essai commence donc par des éditions différentes de la première page du site.

## Champs et limites de la source

- Identité de la fiche, nom affiché, langue de l'impression `id`, région `ID`,
  source, date de collecte, extension, numéro, rareté et marque de régulation.
- Illustrateurs, `images.front` et plus grande image disponible dans `images.large`.
- Pokémon : PV, types, stade/évolution, numéros Pokédex, attaques avec coûts et
  dégâts, talents, traits antiques, autres effets, règles, faiblesse, résistance,
  retraite. Les valeurs connues nulles (retraite gratuite) restent distinctes
  des valeurs absentes.
- Dresseurs/Énergies : catégorie, effets, règles et types d'énergie fournis
  lorsqu'ils sont explicitement indiqués. Les quantités/conditions non fournies
  restent absentes.
- `text_blocks` conserve les blocs structurés et `raw_text` le contenu de la fiche,
  sans menus, prix, données de collection ni copyright du site.

**Les textes affichés par cette source sont en anglais**, même pour les impressions
indonésiennes. `additional_attributes.text_language` reprend la langue du document
(`en` sur les fiches observées). `name`, attaques et effets sont donc les textes du
catalogue, pas une transcription garantie de l'image indonésienne. Pas de traduction
inventée ni d'OCR. La région de chaque fiche est vérifiée via le JSON public embarqué.

**Texte d'ambiance :** aucune section correspondante n'a été trouvée dans les
fiches examinées. `flavor_text` reste absent, comme la taille, le poids ou d'autres
mentions uniquement lisibles sur l'image. Le spider n'assimile pas les effets
de Dresseurs/Énergies ou la description SEO à du texte d'ambiance.

**Rectos manquants :** certaines fiches affichent le dos générique
`default-card-image`, y compris après navigation manuelle. Il n'est enregistré
ni dans `images.front` ni dans `images.large` ; l'item porte
`additional_attributes.image_status = "missing"`. La fiche reste exportée.
Exemple vérifié : Fiery Flint, Hidden Shadow (Set A), 221/183.

**Finitions :** une fiche TCG Collector peut regrouper plusieurs finitions.
L'export contient un item par ID de fiche ; `additional_attributes.available_variants`
énumère leurs identifiants et libellés. Aucun `printing.finish` n'est choisi sans
preuve et les variantes ne sont pas artificiellement dédoublées. Cela constitue
une limite de cette source par rapport au modèle idéal « une impression/variante ».

## Options et reprise

| Argument Scrapy `-a` | Défaut | Effet |
| --- | --- | --- |
| `max_cards` | `0` | Limite totale de fiches planifiées, 0 = toutes |
| `max_sitemaps` | `0` | Limite de fichiers ID après l'index, 0 = tous |
| `start_url` | Index public ci-dessus | Index XML ; utile pour les tests locaux |
| `card_base_url` | `https://www.tcgcollector.com` | Origine autorisée des fiches ; tests locaux |

`max_pages` n'est pas accepté : le nombre de sitemaps n'est pas celui des pages de
recherche. Les commandes d'essai utilisent `max_cards=5`, le complet `max_cards=0`.
Les commandes génériques `crawl -Spider pokemon_id` et `make crawl SPIDER=pokemon_id`
restent bornées à cinq fiches et écrivent dans le fichier d'échantillon.

Les fichiers complets sont `data/pokemon_id.jsonl` et `data/jobs/pokemon_id/`.
Arrêter avec **Ctrl+C une seule fois**, attendre la fermeture propre, puis relancer
exactement la même commande. Les requêtes en attente, IDs déjà planifiés et budget
sont conservés. Ne pas partager ce JOBDIR entre deux processus ni modifier les
limites pendant une reprise. Ne pas utiliser `-O` avec le JOBDIR complet : cela
effacerait les lignes déjà exportées. Garder l'export et son état ensemble.

Une reprise ne redécouvre pas les nouveautés d'un crawl terminé. Pour une nouvelle
collecte, utiliser **un nouvel export et un nouveau JOBDIR**. Après un arrêt brutal,
une erreur réseau ou un blocage, la reprise n'est pas une transaction garantissant
le réessai des requêtes échouées : inspecter les logs et conserver les fichiers.

Les politiques communes restent actives : robots.txt, une requête par domaine,
délais et AutoThrottle, arrêt sur 403/429. Un HTML/XML inattendu arrête le spider
avec `invalid_catalogue` ou `invalid_card_detail`, un échec réseau avec
`request_failed`. Vérifier `finish_reason` dans les logs : Scrapy peut terminer
avec un code système 0 après un arrêt contrôlé qui n'est pas une collecte complète.
Prévoir plusieurs heures pour le catalogue complet avec les délais normaux.

## Vérifications

Les tests synthétiques couvrent Pokémon, Dresseur, Énergie, illustrateurs, images
réelles et placeholder, variantes, absence de texte d'ambiance, symboles, limites,
rejet des autres régions et des URLs inattendues. Les tests HTTP locaux vérifient
les sitemaps multiples, la déduplication, robots.txt, le budget, JOBDIR et les erreurs.

```sh
docker compose run --rm crawler pytest tests/test_pokemon_id.py tests/test_pokemon_id_crawl.py -q -p no:cacheprovider
```
