# Catalogue Pokémon coréen

Le spider `pokemon_kr` parcourt la [recherche officielle coréenne](https://pokemoncard.co.kr/cards)
et les fiches de cartes. Il remplit `ItemPokemon` avec les textes coréens,
`language="ko"`, `region="KR"` et des identifiants `pokemoncard.co.kr:<CardNum>`.

## Recherche et pagination

À l'ouverture, la page n'affiche pas toutes les cartes. Le bouton **검색**
(Recherche) envoie un POST à `/v2/ajax2_dev2` avec `action=search_text_cards`,
une recherche vide, `search_params=all` et `limit=0`. Le bouton **더 불러오기**
(Charger plus) répète cette requête avec le `limit` de la réponse précédente.

Le spider reproduit ces appels avec l'en-tête AJAX standard
`X-Requested-With: XMLHttpRequest`, puis suit `/cards/detail/<CardNum>` pour chaque
carte. Les fiches sont déjà en HTML : Playwright n'est pas nécessaire pour ce site.
Les réponses observées fournissent 30 cartes par lot ; la taille n'est pas codée en dur.

La pagination continue jusqu'à une réponse valide avec `status=true`, `count=0`
et une liste vide. Un lot court ne suffit pas à conclure. `count` indique le nombre
de cartes du lot, **pas un total global** : le site n'en fournit pas dans cet appel.
Les réponses incohérentes, un curseur qui saute/revient en arrière ou un lot entièrement
répété provoquent `invalid_catalogue`.

## Commandes

Depuis la racine du projet, avec Docker Desktop démarré et l'image construite :

```powershell
# Essai borné, dans Docker.
.\make.ps1 pokemon-kr -MaxPages 1 -ExtraArgs @('-a', 'max_cards=5')

# Catalogue complet, dans Docker.
.\make.ps1 pokemon-kr-all
```

```sh
make pokemon-kr MAX_PAGES=1 ARGS='-a max_cards=5'
make pokemon-kr-all
```

Commande Docker directe pour la collecte complète :

```sh
docker compose run --rm crawler scrapy crawl pokemon_kr -a max_pages=0 -s JOBDIR=data/jobs/pokemon_kr -o data/pokemon_kr.jsonl
```

Le code est monté dans le conteneur ; aucune nouvelle dépendance ni reconstruction
d'image n'est nécessaire si l'image du projet existe déjà. Sinon : `docker compose build`.
Sans Docker, après installation des dépendances locales :

```powershell
.\.venv\Scripts\python.exe -m scrapy crawl pokemon_kr -a max_cards=5 -O data/pokemon_kr-sample.jsonl
```

## Fichiers et reprise

- Essai : `data/pokemon_kr-sample.jsonl`, remplacé à chaque essai.
- Collecte complète : `data/pokemon_kr.jsonl`, complété à chaque reprise.
- Reprise : `data/jobs/pokemon_kr`, distinct du job japonais.

Le lancement générique `crawl -Spider pokemon_kr` / `crawl SPIDER=pokemon_kr`
écrit lui aussi dans le fichier d'échantillon. Chaque ligne JSONL représente une carte.
Les images sont référencées par `images.front`, sans être téléchargées.

Pour interrompre proprement : **Ctrl+C une seule fois**, attendre la fermeture,
puis relancer la même commande. JOBDIR conserve les requêtes POST en attente,
les IDs déjà planifiés et le budget `max_cards`. Garder les mêmes options lors de
la reprise et ne pas utiliser un JOBDIR dans deux processus simultanés.
Le cache de cookies de Scrapy n'est pas persistant, mais cet appel public a été
vérifié sans session authentifiée ni cookie requis.

Ne pas changer `-o` en `-O` pendant une reprise. Pour une nouvelle collecte ou
une recherche différente, choisir un nouveau couple export/JOBDIR : un job terminé
ne relance pas une collecte. Une coupure brutale ou une fiche en erreur peut laisser
des manques ; la reprise ne constitue pas une transaction. Un catalogue modifié
pendant le parcours peut également déplacer des cartes entre les lots.

## Options `-a`

| Argument | Défaut | Signification |
| --- | --- | --- |
| `max_pages` | `0` | Nombre de lots ; zéro = sans limite |
| `max_cards` | `0` | Nombre de fiches distinctes demandées ; zéro = sans limite |
| `start_page` | `1` | Premier lot, correspondant au curseur `start_page - 1` |
| `search_text` | vide | Texte de recherche ; vide pour toutes les cartes |
| `search_params` | `all` | `all`, `cardname` ou `cardtext` |
| `start_url` | `https://pokemoncard.co.kr/cards` | URL de base ; le paramètre `s` remplit la recherche si `search_text` est absent |

La commande `pokemon-kr` fixe trois lots par défaut (`MAX_PAGES` / `-MaxPages`).
La commande `pokemon-kr-all` fixe `max_pages=0` et configure la reprise.

## Champs et limites

Sont relevés lorsqu'ils sont présents : nom, illustrateurs, image, numérotation,
code/symbole de set, marque de régulation, rareté, catégorie, stade, niveau, PV,
types, attaques, coûts, dégâts, talents/anciens pouvoirs, traits antiques, règles,
faiblesses, résistances, retraite, catégorie Pokédex, taille, poids et description.
Le numéro Pokédex provient du texte visible ou, sur les gabarits plus récents,
du commentaire HTML dédié. Les sous-types sont conservés pour les trois catégories
de cartes (par exemple un Dresseur « Futur »).

Les types d'énergie utilisent les mêmes noms anglais que le spider japonais.
Les pictogrammes dans les effets deviennent `{Psychic}`, `{Colorless}`, etc.
Les coûts répétés restent des listes et les mécaniques inconnues sont conservées
dans `effects` et `text_blocks`. `raw_text` exclut les menus, commentaires éditoriaux
et liens de navigation. Le crédit artistique absent reste absent.

Les liens de produits ou récompenses sont stockés dans
`additional_attributes.related_links` et ne remplissent pas automatiquement `set.name`.
Les données visibles uniquement sur l'image ne sont pas lues par OCR. Aucun prix,
vendeur, état de carte ou copyright du pied de page n'est attribué à la carte.

Robots.txt, délais, AutoThrottle et arrêt sur 403/429 suivent les réglages du projet.
Les raisons `invalid_catalogue`, `invalid_card_detail`, `request_failed`,
`blocked_403`, `blocked_429` et `closespider_errorcount` signalent un export partiel.
Vérifier les logs : un arrêt contrôlé peut avoir un code de sortie zéro.
`finished` correspond au périmètre demandé, qui peut être limité par les options.
