# ItemOnePiece

`ItemOnePiece` est le modèle Scrapy des cartes physiques du ONE PIECE CARD GAME.
Comme pour `ItemPokemon`, chaque item décrit une impression dans une langue et
une variante précises. Un spider peut le renvoyer directement avec `yield` pour
l’exporter en JSON ou JSONL.

## Exemple

Cette fiche partielle de Kaloo illustre comment conserver les deux couleurs
et les deux types d’un Leader. [Fiche OP18-001 du catalogue Bandai](https://fr.onepiece-cardgame.com/cardlist/?series=622118)

```python
from tcg_scraper.item_one_piece import ItemOnePiece

carte = ItemOnePiece(
    name="Kaloo",
    language="fr",
    number="OP18-001",
    set={"code": "OP-18"},
    card_type="LEADER",
    rarity="L",
    block_icon="5",
    colors=["Rouge", "Bleu"],
    attributes=["Frappe"],
    types=["Animal", "Royaume d'Alabasta"],
    life="4",
    power="5000",
)
```

## Champs de jeu

| Champ | Valeur attendue |
| --- | --- |
| `card_type` | Catégorie dans la langue de la source, par exemple Leader, Personnage, Événement, Lieu ou DON!!. |
| `colors`, `attributes`, `types` | Trois listes distinctes pour les couleurs, les attributs de combat et les types ou affiliations. Conserver l’ordre indiqué. |
| `life`, `power`, `cost` | Vie du Leader, puissance de base et coût pour jouer la carte, selon les valeurs disponibles. |
| `counter` | Valeur imprimée du Contre d’un Personnage, par exemple `"+2000"`. Un effet portant le libellé `[Contre]` va dans `effects`. |
| `don_power_bonus` | Bonus imprimé sur une DON!!, par exemple `"+1000"`. Conserver sa condition de tour dans le texte. |
| `keywords`, `effects` | Mots-clés et liste ordonnée d’effets. Chaque effet peut porter `labels` (liste de chaînes) et `text` (texte intégral avec conditions et coûts d’activation). |
| `trigger` | Texte complet de la section Déclenchement, lorsqu’elle figure sur la carte. |
| `rules`, `text_blocks`, `raw_text` | Règles imprimées, blocs ordonnés (`kind`, `title`, `text`) et transcription brute de la carte. |

Un effet conditionné par `DON!! ×1` conserve ce libellé dans `effects[].labels`.
Le coût pour jouer la carte reste dans `cost`. Les catégories et les mots-clés
sont libres pour accueillir plusieurs langues et de futures mécaniques.
[Manuel officiel Bandai, sections sur les cartes et leurs effets](https://en.onepiece-cardgame.com/pdf/rule_manual.pdf)

## Impressions, variantes et sources

- `number` conserve le numéro complet, par exemple `OP01-001` ou `P-001`.
  `card_id` identifie l’impression précise. Une illustration parallèle, une
  réédition dans un autre produit ou une autre langue peut partager le même numéro.
- `set` décrit le produit de cette impression avec les clés facultatives `code`,
  `name` et `series`. Pour une réédition, relever le produit sur la fiche.
  Le préfixe du numéro de carte peut renvoyer à l’extension d’origine.
- `rarity` et `block_icon` conservent leurs libellés. Dans `printing`, utiliser
  `variant` pour la version parallèle, `illustration_type` pour le type de visuel,
  `finish` pour la finition, `stamps` pour les tampons (liste) et `distribution`
  pour une distribution promotionnelle identifiée.
- `name`, `language`, `region`, `release_date`, `illustrators` et `copyright`
  décrivent l’impression. `images` associe chaque vue (`front`, `back`, `large`)
  à son URL absolue.
- `source_name`, `source_url`, `scraped_at` (ISO 8601 avec fuseau) et
  `external_ids` (identifiants par catalogue) permettent de retrouver le relevé.
  `additional_attributes` accueille les particularités supplémentaires en JSON.

Tous les champs sont facultatifs. Omettre les valeurs inconnues ou inapplicables.
Conserver un zéro explicitement observé sous forme de chaîne, ainsi que les signes,
les symboles et la casse. Les métadonnées `value_type` documentent les types
attendus. Le spider est responsable de l’interprétation des valeurs de sa source.
