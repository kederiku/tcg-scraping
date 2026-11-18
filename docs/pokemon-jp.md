# Catalogue officiel Pokémon japonais

Le spider `pokemon_jp` utilise la [recherche officielle](https://www.pokemon-card.com/card-search/index.php?keyword=&se_ta=&regulation_sidebar_form=all&pg=&illust=&sm_and_keyword=true).
Il appelle le même endpoint public `resultAPI.php` que la recherche du site,
lit `thisPage` et `maxPage`, puis suit chaque URL `details.php/card/<id>/regu/<regulation>`.
Suivre ces URLs produit le même accès aux fiches que cliquer sur les cartes.
Le HTML des fiches est déjà disponible : Chromium n'est pas nécessaire ici.

## Lancement

Docker doit être démarré. Les commandes s'exécutent à la racine du projet.

```powershell
# Cinq fiches au maximum, fichier de démonstration remplacé à chaque essai.
.\make.ps1 pokemon -MaxPages 1 -ExtraArgs @('-a', 'max_cards=5')

# Toutes les pages et fiches, avec état de reprise persistant.
.\make.ps1 pokemon-all
```

```sh
make pokemon MAX_PAGES=1 ARGS='-a max_cards=5'
make pokemon-all
```

Sans Make ni script PowerShell :

```sh
docker compose run --rm crawler scrapy crawl pokemon_jp -a max_pages=1 -a max_cards=5 -O data/pokemon_jp-sample.jsonl
docker compose run --rm crawler scrapy crawl pokemon_jp -a max_pages=0 -s JOBDIR=data/jobs/pokemon_jp -o data/pokemon_jp.jsonl
```

Sans Docker, après installation des dépendances :

```powershell
.\.venv\Scripts\python.exe -m scrapy crawl pokemon_jp -a max_cards=5 -O data/pokemon_jp-sample.jsonl
```

Chaque ligne de l'export JSONL contient un `ItemPokemon`. Les deux fichiers
d'export sont distincts pour éviter qu'un essai écrase la collecte complète.
La commande générique `crawl` avec `SPIDER=pokemon_jp` / `-Spider pokemon_jp`
utilise également le fichier d'échantillon.
Les images ne sont pas téléchargées ; leur URL est enregistrée dans `images.front`.

## Options du spider

| Argument `-a` | Défaut direct | Signification |
| --- | --- | --- |
| `max_pages` | `0` | Nombre de pages de résultats à lire ; `0` = toutes |
| `max_cards` | `0` | Nombre maximal de fiches distinctes à demander ; `0` = toutes |
| `start_page` | `1` | Première page de résultats à lire |
| `start_url` | Recherche ci-dessus | URL de recherche ; ses filtres sont conservés |

La commande `pokemon` impose 3 pages par défaut (`MAX_PAGES` / `-MaxPages`).
La commande `pokemon-all` impose `max_pages=0` et configure la reprise.
`max_pages` compte à partir de `start_page`. Pour changer le filtre, passer par
exemple `-a "start_url=https://www.pokemon-card.com/card-search/index.php?regulation_sidebar_form=all&se_ta=energy"`.
Une recherche filtrée doit avoir son propre export et son propre JOBDIR.

## Reprise et renouvellement

`pokemon-all` utilise `data/jobs/pokemon_jp` pour la file de requêtes et les
empreintes déjà vues, et `-o` pour **ajouter** au JSONL.

L'état conserve aussi les IDs planifiés, la couverture des pages et le budget
`max_cards` : la limite ne repart pas de zéro lors d'une reprise du même job.
Appuyer une seule fois sur Ctrl+C et attendre la fermeture avant de relancer
exactement la même commande.
Ne pas lancer deux processus avec le même JOBDIR. Ne pas remplacer `-o` par `-O`
pendant une reprise, car les données déjà exportées seraient effacées.

Un JOBDIR terminé ne relance pas une nouvelle collecte. Pour un nouveau passage,
choisir un autre couple JOBDIR/export, par exemple :

```sh
docker compose run --rm crawler scrapy crawl pokemon_jp -s JOBDIR=data/jobs/pokemon_jp-run2 -o data/pokemon_jp-run2.jsonl
```

La reprise Scrapy n'est pas une transaction : une coupure brutale, une fiche en
erreur ou un arrêt sur blocage peut laisser des données manquantes. Après une
erreur, examiner les logs et refaire une collecte avec un nouveau couple de
fichiers si nécessaire. Le catalogue peut aussi changer pendant un long passage :
le dédoublonnage par ID évite les doublons dans un passage normal, mais des ajouts
qui décalent les pages peuvent nécessiter un nouveau passage. Une variation du
nombre annoncé, une plage de résultats incohérente, une page répétée ou un total
d'IDs incomplet à la dernière page d'un parcours intégral provoquent un arrêt
`invalid_catalogue`, plutôt qu'une fin normale.

## Contenu collecté

- Identifiant stable `pokemon-card.com:<id>`, nom japonais, provenance, langue,
  région, date de collecte UTC, illustrateur(s) et URL de l'image.
- Numérotation textuelle, code/symbole de set et total imprimé lorsque présents.
  Les liens de produit ou de provenance promotionnelle sont stockés séparément
  dans `additional_attributes.related_links` : ils ne déterminent pas `set.name`.
- Pokémon : stade, PV, types, attaques et coûts, talents/anciennes capacités,
  traits antiques, faiblesses, résistances, retraite, Pokédex, taille, poids et description.
- Dresseurs et Énergies : catégorie et texte des effets, règles spéciales.
- `text_blocks` et `raw_text` conservent les textes et les mécanismes non reconnus.
  Les pictogrammes d'énergie deviennent `{Water}`, `{Dragon}`, etc. Les répétitions
  des coûts sont conservées ; `icon-void` représente un coût de zéro.

Les noms et effets restent en japonais. Les types d'énergie sont normalisés en
anglais (Grass, Fire, Water, Lightning, Psychic, Fighting, Darkness, Metal, Fairy,
Dragon, Colorless). Les champs absents restent absents, selon les conventions de
[`ItemPokemon`](item-pokemon.md). Aucun prix ni état de vente n'est collecté.

La recherche donne accès au catalogue publié sur ce site, qui n'est pas une
garantie de couverture de toutes les cartes physiques jamais imprimées. Les
informations visibles seulement sur l'image ne sont pas extraites par OCR. En
particulier, le logo de set nommé `img-regulation` dans le HTML ne constitue pas
la marque de régulation imprimée. Ni cette marque, ni la rareté, ni le copyright
du pied de page ne sont inventés ou attribués à la carte. Le widget d'évolution
est une navigation de recherche ; il ne remplit pas automatiquement `evolves_from`.

## Surveillance et tests

Les logs indiquent `Catalogue page N/M` et la raison de fermeture. `finished`
signifie que le périmètre demandé (éventuellement borné) est épuisé. Les raisons
`invalid_catalogue`, `invalid_card_detail`, `request_failed`, `blocked_403` ou
`blocked_429` ou `closespider_errorcount` signalent une interruption : l'export est
alors partiel. Cette dernière raison couvre les erreurs de parsing inattendues.
Scrapy peut
retourner un code processus zéro après un arrêt contrôlé ; vérifier les logs,
pas uniquement le code de sortie.

Le spider conserve les délais, AutoThrottle, robots.txt et l'arrêt sur blocage
du projet. Aucun contournement de CAPTCHA, proxy ou service payant n'est ajouté.

`make test` / `.\make.ps1 test` exécute les tests sur des données synthétiques
et des serveurs locaux, sans contacter le site Pokémon.
