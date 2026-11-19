"""Une impression physique du ONE PIECE CARD GAME, dans une langue et une variante."""

from scrapy import Field, Item


class ItemOnePiece(Item):
    """Champs facultatifs pour les Leaders, Personnages, Événements, Lieux et DON!!.

    Chaque Field décrit le type attendu. Le spider renseigne uniquement les
    valeurs observées, selon les conventions de docs/item-one-piece.md.
    """

    # Identité de l'impression et provenance.
    card_id = Field(value_type="str", description="Identifiant de l'impression et de sa variante.")
    name = Field(value_type="str", description="Nom complet dans la langue de l'impression.")
    language = Field(value_type="str", description="Langue de l'impression, de préférence BCP 47.")
    region = Field(value_type="str", description="Marché de publication.")
    external_ids = Field(value_type="dict[str, str]", description="Identifiants par catalogue.")
    source_name = Field(value_type="str", description="Nom du catalogue consulté.")
    source_url = Field(value_type="str", description="URL de la fiche source.")
    scraped_at = Field(
        value_type="str", description="Date et heure de collecte ISO 8601 avec fuseau."
    )

    # Numéro de carte et caractéristiques propres à cette impression.
    number = Field(
        value_type="str", description="Numéro complet de la carte, par exemple OP01-001."
    )
    set = Field(value_type="dict", description="Extension ou produit de cette impression.")
    release_date = Field(value_type="str", description="Date de parution avec la précision connue.")
    rarity = Field(value_type="str", description="Rareté indiquée par la source, par exemple SEC.")
    block_icon = Field(value_type="str", description="Symbole de bloc tel qu'indiqué.")
    illustrators = Field(value_type="list[str]", description="Noms des artistes crédités.")
    copyright = Field(value_type="str", description="Mention de copyright imprimée.")
    printing = Field(value_type="dict", description="Variante, illustration, finition et tampons.")
    images = Field(value_type="dict[str, str]", description="URLs absolues par vue (front, back…).")

    # Caractéristiques du jeu. Une valeur imprimée peut contenir un signe ou un symbole.
    card_type = Field(value_type="str", description="Catégorie de carte, par exemple LEADER.")
    colors = Field(value_type="list[str]", description="Couleurs de la carte dans l'ordre indiqué.")
    attributes = Field(
        value_type="list[str]", description="Attributs de combat, par exemple Slash."
    )
    types = Field(value_type="list[str]", description="Traits ou affiliations, par exemple Navy.")
    life = Field(value_type="str", description="Valeur de vie du Leader.")
    cost = Field(value_type="str", description="Coût pour jouer la carte.")
    power = Field(value_type="str", description="Puissance de base du Leader ou du Personnage.")
    counter = Field(value_type="str", description="Valeur du symbole de Contre du Personnage.")
    don_power_bonus = Field(
        value_type="str", description="Bonus de puissance imprimé sur une DON!!."
    )

    # Texte du jeu et particularités de la source.
    keywords = Field(value_type="list[str]", description="Mots-clés relevés, par exemple Blocker.")
    effects = Field(
        value_type="list[dict]", description="Effets dans l'ordre, avec leurs libellés."
    )
    trigger = Field(value_type="str", description="Texte de la section Trigger (Déclenchement).")
    rules = Field(
        value_type="list[str]", description="Règles ou restrictions écrites sur la carte."
    )
    text_blocks = Field(value_type="list[dict]", description="Sections dans leur ordre de lecture.")
    raw_text = Field(
        value_type="str", description="Texte intégral de la carte fourni par la source."
    )
    additional_attributes = Field(value_type="dict", description="Autres caractéristiques en JSON.")
