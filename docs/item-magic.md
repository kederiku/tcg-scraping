# ItemMagic

`ItemMagic` est l’item Scrapy pour Magic: The Gathering. Un spider peut émettre
une fiche par impression, langue et variante. Le même modèle couvre les cartes
d’Alpha (1993), les rééditions, les jetons et les versions numériques. Les champs
sont facultatifs et le spider les remplit à partir de sa source.

## Exemple avec Black Lotus en Alpha

```python
from tcg_scraper.item_magic import ItemMagic

carte = ItemMagic(
    name="Black Lotus",
    language="en",
    set={"code": "LEA", "name": "Limited Edition Alpha"},
    number="232",
    release_date="1993-08-05",
    printed_type_line="Mono Artifact",
    type_line="Artifact",
    mana_cost="{0}",
    mana_value=0,
    illustrators=["Christopher Rush"],
    source_name="mtg.wtf",
    source_url="https://mtg.wtf/card/lea/232/Black-Lotus",
)
```

Le catalogue attribue le numéro `232` à cette impression. La carte Alpha se
lit « Mono Artifact » et ne porte aucun numéro de collection. Cette fiche omet
donc `printed_number` et conserve le type Oracle dans `type_line`.
[Fiche et image de Black Lotus en Alpha](https://mtg.wtf/card/lea/232/Black-Lotus).

## Identité, impression et provenance

| Champ | Convention |
| --- | --- |
| `card_id`, `oracle_id` | `card_id` identifie l’impression, sa langue et sa variante. `oracle_id` relie les impressions de la même carte lorsque la source fournit cet identifiant. |
| `name`, `oracle_name`, `flavor_name` | Nom dans la langue de la fiche, nom canonique Oracle et nom alternatif utilisé pour une illustration. |
| `language`, `region`, `games` | Langue de l’impression, marché et supports de jeu. Une fiche peut par exemple indiquer `games=["arena"]` pour une version numérique. |
| `set`, `number`, `printed_number`, `release_date`, `rarity` | Dans `set`, utiliser `code`, `name`, `type`, `series` ou `symbol_url` selon les données disponibles. Les numéros gardent leurs zéros, suffixes et symboles. La date concerne cette impression. |
| `printing` | Dictionnaire avec, par exemple, `finish`, `frame`, `frame_effects`, `border_color`, `watermark`, `security_stamp`, `promo_types`, `illustration_id`, `is_full_art`, `is_textless` ou `is_reprint`. |
| `illustrators`, `copyright`, `images` | Artistes crédités, mention imprimée et URLs absolues par vue ou format (`front`, `back`, `normal`, `art_crop`). |
| `external_ids`, `source_name`, `source_url`, `scraped_at` | Identifiants sous leur nom de catalogue (Scryfall, Gatherer, MTGJSON, Arena…), nom du catalogue consulté, URL de la fiche et horodatage ISO 8601 avec fuseau. Conserver les identifiants multiples sous forme de liste. |

Si un catalogue regroupe plusieurs finitions sur une seule fiche, conserver sa
liste dans `printing.available_finishes`. Renseigner `printing.finish` lorsque la
source identifie la finition de la variante décrite.

## Règles imprimées et règles actuelles

- Conserver le texte de l’édition et sa langue dans `printed_text` et
  `printed_type_line`. Le texte de référence au moment de la collecte va dans
  `oracle_text` et `type_line`. `flavor_text` conserve le texte d’ambiance.
- `supertypes`, `types` et `subtypes` décomposent la ligne de type Oracle si la
  source fournit cette décomposition. `keywords` conserve les mots-clés.
- `mana_cost` préserve les symboles Oracle et leur ordre, par exemple `{X}{W/U}{B/P}`.
  `printed_mana_cost` conserve le coût observé sur l’impression.
  `mana_value` est numérique. Un coût de `{0}`, une carte sans coût et une
  valeur de mana inconnue sont trois situations distinctes. Un coût explicitement
  absent peut être représenté par `""`, une donnée inconnue par un champ omis.
- `colors`, `color_identity`, `color_indicator` et `produced_mana` décrivent
  respectivement les couleurs, l’identité couleur, la pastille de couleur et le
  mana que la carte peut produire. Une liste vide conserve une absence confirmée.
- `power`, `toughness`, `loyalty` et `defense` gardent les valeurs Oracle sous
  forme de chaînes telles que `"*"`, `"1+*"` ou `"X"`. `printed_power` et
  `printed_toughness` conservent la force et l’endurance imprimées. Par exemple,
  *Elvish Archers* en Alpha porte 1/2 et ses valeurs de référence sont 2/1.
  [Erreurs d’impression d’Alpha documentées par Wizards](https://magic.wizards.com/en/news/making-magic/25-random-things-about-magic-2009-02-16).
- Les cartes Vanguard peuvent porter un
  `hand_modifier` et un `life_modifier` signés. `attraction_lights` liste les
  numéros allumés d’une Attraction.
- `legalities` associe chaque format à son statut au moment du relevé.
  `rulings` conserve des entrées avec `date`, `text` et, si fournis,
  `source` et `url`. `is_reserved` indique l’appartenance à la Reserved List.

Ces conventions reprennent les distinctions des [règles de Wizards of the Coast](https://magic.wizards.com/en/rules)
et du [modèle de carte par extension de MTGJSON](https://mtgjson.com/data-models/card/card-set/).

## Faces, parties et cartes liées

`layout` conserve le libellé de la source. Pour une carte recto verso, placer les
deux faces dans `faces`, dans l’ordre. Chaque entrée peut porter `side`, `name`,
ses propres textes imprimé et Oracle, type, coût, statistiques, artistes et
`images`. Les clés ont les mêmes noms qu’au niveau de la carte. Ainsi, une bataille
recto verso peut porter `defense` au recto et `power` et `toughness` au verso.
L’identité couleur de la carte entière reste au niveau de l’item.

Pour une carte double (*split*) ou une aventure, les parties peuvent occuper le
même recto. L’ordre de `faces` conserve l’ordre des parties et `side` décrit le
côté physique quand il est connu. Pour l’assimilation (*meld*), créer une fiche
pour chaque impression physique avec l’image de son propre verso. Si le catalogue
décrit la face assemblée, lui donner sa propre fiche avec son image, ses textes
et ses caractéristiques. Relier les fiches via `related_cards`, avec le rôle
`meld_part` ou `meld_result` dans `component`. Un lien peut également contenir
`name`, `card_id`, `external_ids` et `url`. La même structure relie une carte
aux jetons qu’elle crée.

## Particularités historiques et futures

Les champs `text_blocks` (liste ordonnée de blocs avec `kind`, `title` et `text`)
et `raw_text` préservent la transcription, les symboles et les sauts de ligne.
Pour une caractéristique propre à un catalogue ou à une mécanique encore inconnue,
utiliser `additional_attributes`, par exemple `{"catalogue": {"symbole": "★"}}`.
Toutes les sous-structures utilisent des valeurs JSON natives. L’export JSONL
préserve leur structure. Les métadonnées `value_type` des champs documentent
les types attendus et le spider reste responsable des valeurs qu’il émet.
