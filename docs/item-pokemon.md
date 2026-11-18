# ItemPokemon

`tcg_scraper/item_pokemon.py` fournit un `scrapy.Item` commun aux cartes physiques
**Pokémon, Dresseur et Énergie**, anciennes ou récentes. Il ne dépend d'aucune API.
Il n'inclut pas de prix, vendeur, état de conservation, grading ou données d'annonce.

## Utilisation dans un futur spider

```python
from tcg_scraper.item_pokemon import ItemPokemon

yield ItemPokemon(
    name="Nom relevé sur la carte",
    supertype="Pokémon",
    language="fr",
    number="001",
    printed_number="001/198",
    hp="120",
    types=["Feu"],
    illustrators=["Nom de l'illustrateur"],
    images={"front": "https://example.org/cards/001-front.png"},
    attacks=[
        {
            "name": "Nom relevé",
            "cost": ["Feu", "Feu", "Incolore"],
            "damage": "30+",
            "text": "Texte relevé sur la carte.",
        }
    ],
    source_url=response.url,
)
```

Cet exemple illustre la structure ; il ne décrit pas une carte réelle.
L'export JSON/JSONL de Scrapy conserve les dictionnaires et listes. Un export CSV
ne constitue pas un format adapté aux attaques, talents et autres listes imbriquées.

## Conventions

- **Un item = une impression, une langue et une variante.** Deux finitions ou langues
  d'une même carte doivent rester distinguables. Le numéro seul n'est pas un ID unique.
- Tous les champs sont facultatifs. Omettre un champ inconnu ; ne pas fabriquer
  de `0`, `False`, liste vide ou chaîne vide. Une liste vide signifie qu'on a vérifié
  l'absence d'éléments ; zéro est une valeur connue, notamment pour la retraite gratuite.
- Conserver la langue, les symboles et la casse d'origine. `ex` et `EX` ne doivent
  pas être fusionnés. Les types et sous-types sont libres, sans enum limitant une époque.
- Les numéros, PV, niveaux, dégâts, modificateurs, tailles et poids restent du texte :
  `001`, `H1`, `TG01`, `201/198`, `30+`, `20×`, `×2`, `−30` et `?` sont préservés.
- Pour les coûts, répéter chaque symbole : `["Feu", "Feu", "Incolore"]` compte trois
  symboles. Une liste `[]` signifie un coût explicitement nul, pas un coût inconnu.
- Les générations concernent les Pokémon représentés, dans `pokemon[].generation`.
  La série de publication appartient à `set.series` : ce sont deux informations différentes.
- Les identifiants de source sont rangés sous leur espace de noms (`external_ids`).
  Les informations de catalogue absentes de la carte (date de sortie, génération, etc.)
  sont facultatives et ne doivent être renseignées que lorsqu'une source les fournit.
- La clé `value_type` des métadonnées de chaque `Field` est une **convention documentaire**, pas une validation.
  L'item ne remplit, ne normalise et ne convertit rien. Le futur spider/pipeline en sera responsable.
- Utiliser uniquement des valeurs JSON natives dans les sous-structures : dictionnaires,
  listes, chaînes, nombres, booléens ou `None`. Sérialiser les dates en chaînes ISO 8601.

## Champs principaux

Chaque champ est également décrit dans le fichier Python.

| Groupe | Champs |
| --- | --- |
| Identité et collecte | `card_id`, `name`, `language`, `region`, `external_ids`, `source_name`, `source_url`, `scraped_at` |
| Extension et impression | `supertype`, `subtypes`, `set`, `number`, `printed_number`, `rarity`, `rarity_symbols`, `regulation_mark`, `release_date`, `illustrators`, `copyright`, `printing`, `images` |
| Pokémon | `pokemon`, `owners`, `stage`, `level`, `hp`, `types`, `evolves_from`, `evolution_text`, `species`, `height`, `weight`, `flavor_text` |
| Jeu | `attacks`, `abilities`, `ancient_traits`, `weaknesses`, `resistances`, `retreat_cost`, `converted_retreat_cost`, `rules`, `effects` |
| Dresseur | `trainer_type`, `trainer_text` |
| Énergie | `energy_type`, `energy_text`, `provided_energy` |
| Cas particuliers et conservation | `composition`, `text_blocks`, `raw_text`, `additional_attributes` |

## Structures imbriquées

Toutes les clés ci-dessous sont facultatives. Ce sont les noms recommandés pour
les futurs spiders, sans validation implicite des dictionnaires.

### Extension : `set`

`id` (str, à contextualiser par la source), `name` (str), `series` (str),
`code` (str), `release_date` (str), `printed_total` (int), `total_with_secrets` (int),
`symbol_url` (str), `logo_url` (str).

Le dénominateur imprimé reste aussi dans `printed_number`. Ne pas déduire que toutes
les cartes d'un set ont le même dénominateur ou que les cartes secrètes en font partie.

### Illustrateur et image

`illustrators` contient le nom de chaque illustrateur crédité, même s'il n'y en a
qu'un : `["Nom de l'illustrateur"]`. `images["front"]` est l'URL de l'image principale
du recto ; `images["back"]` et `images["large"]` peuvent compléter la fiche.
Les URLs doivent être absolues : dans un spider, utiliser `response.urljoin(src)`
si le site renvoie un chemin relatif. L'item stocke ces URLs sans télécharger les images.

### Variante : `printing`

`edition` (str), `finish` (str), `holo_pattern` (str), `stamps` (list[str]),
`border_color` (str), `orientation` (str), `layout` (str), `is_jumbo` (bool),
`dimensions_mm` (dict avec `width` et `height` numériques),
`print_codes` (dict[str, str]), `distribution` (str), `printed_signature` (str).

Cela distingue notamment première édition/unlimited, shadowless, holo/reverse,
motifs de foil, tampons promotionnels, signatures imprimées et formats jumbo.
Les codes e-Reader ou codes de fabrication peuvent aller dans `print_codes`.
Une dédicace manuscrite ajoutée sur un exemplaire relève de l'exemplaire, pas de ce schéma.

### Pokémon représentés : `pokemon`

Liste de dictionnaires : `name` (str), `national_pokedex_number` (int),
`generation` (int), `form` (str). Plusieurs entrées pour les cartes associant plusieurs
Pokémon. Ne pas confondre numéro Pokédex et numéro de carte.

### Attaques : `attacks`

Liste de dictionnaires : `name` (str), `cost` (list[str]), `converted_energy_cost` (int),
`damage` (str), `text` (str), `kind` (str), `cost_text` (str).
`kind` peut préciser une attaque GX, un pouvoir VSTAR sous forme d'attaque ou un
autre libellé imprimé. Une attaque sans dégâts peut omettre `damage`.
`cost_text` préserve un coût inhabituel qui ne se représente pas par une simple liste.

### Talents et autres effets

- `abilities` : liste de `{kind, name, text}` (chaînes) ; couvre notamment Talent,
  Ability, Pokémon Power, Poké-Power, Poké-Body ou pouvoir VSTAR sous forme de talent.
- `ancient_traits` : liste de `{name, text}` (chaînes).
- `effects` : liste de `{kind, name, text}` (chaînes) pour les sections supplémentaires.
- `rules` : liste des textes de règles, sans leur imposer une mécanique particulière.
- `weaknesses` / `resistances` : listes de `{type, value}` (chaînes), sans convertir
  une multiplication en addition ni perdre le signe d'un modificateur.

### Énergies fournies : `provided_energy`

Liste de `{types: list[str], amount: str, condition: str, text: str}`.
Une quantité variable, un choix de type ou une condition doivent garder leur texte.
Leur présence ne signifie pas que ces énergies sont fournies simultanément : `text`
et `condition` conservent la règle exacte, sans moteur de règles implicite.

### Assemblage : `composition`

`group_name` (str), `part_name` (str), `part_index` (int, à partir de 1),
`part_count` (int), `related_cards` (list[dict], avec `name`, `number`, `external_ids`).
Chaque moitié LEGEND ou quart V-UNION a son propre item et son propre numéro.
Ne pas recopier artificiellement les statistiques de l'assemblage sur chaque partie.

### Conservation intégrale

- `text_blocks` : liste ordonnée de `{kind, title, text, position}` (chaînes).
  Elle préserve les sections, langues ou symboles mal compris lors du premier scraping.
- `raw_text` : texte brut **de la carte**, pas l'intégralité d'une page de vente.
- `additional_attributes` : dictionnaire JSON pour les particularités encore inconnues,
  les variantes de mise en page ou les caractéristiques propres à une source.
- `images` : dictionnaire de noms vers des URLs (`front`, `back`, `large`, `symbol`, etc.).

## Couverture et limites

Le schéma ne fixe ni nombre maximal d'attaques/talents, ni liste de générations.
Il peut conserver les mécaniques anciennes et modernes, les doubles types, cartes
associant plusieurs Pokémon, cartes multiparties, Dresseurs avec statistiques et
Énergies spéciales. Les conventions de noms sont documentées, sans imposer une
partition étanche entre Pokémon, Dresseur et Énergie.

Il ne garantit pas que chaque singularité de chaque carte jamais publiée ait un
champ dédié. `text_blocks`, `printing` et `additional_attributes` permettent de la
conserver, puis d'ajouter un champ explicite quand plusieurs sources le justifient.
Aucune valeur n'est récupérée tant qu'un spider n'alimente pas l'item.

## Références de conception

- [Règles officielles du JCC Pokémon](https://assets.pokemon.com/assets/cms2/pdf/trading-card-game/rulebook/svi_rulebook_en.pdf) : catégories et parties imprimées.
- [Objet Card de TCGdex](https://tcgdex.dev/reference/card) : champs de catalogue.
- [Schéma historique Pokémon TCG API](https://docs.pokemontcg.io/api-reference/cards/card-object/) : diversité des champs anciens ; aucune connexion à cette API n'est ajoutée.
- [Items Scrapy](https://docs.scrapy.org/en/latest/topics/items.html) : champs déclarés et métadonnées.
