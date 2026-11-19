"""Caractéristiques d'une impression ou version numérique de Magic: The Gathering."""

from scrapy import Field, Item


class ItemMagic(Item):
    """Une fiche par impression, langue et variante, quel que soit le type de carte.

    Tous les champs sont facultatifs. Les structures JSON et les conventions pour
    les textes imprimés, les données Oracle et les faces figurent dans docs/item-magic.md.
    """

    # Identité de l'impression, identité de jeu et provenance.
    card_id = Field(value_type="str", description="Identifiant de cette impression et variante.")
    oracle_id = Field(value_type="str", description="Identifiant Oracle commun aux rééditions.")
    name = Field(value_type="str", description="Nom de la carte dans la langue de l'impression.")
    oracle_name = Field(value_type="str", description="Nom de référence dans Oracle.")
    flavor_name = Field(
        value_type="str", description="Nom alternatif porté par cette illustration."
    )
    language = Field(value_type="str", description="Langue de l'impression.")
    region = Field(value_type="str", description="Marché de publication indiqué.")
    external_ids = Field(value_type="dict", description="Identifiants par catalogue ou plateforme.")
    source_name = Field(value_type="str", description="Nom du catalogue consulté.")
    source_url = Field(value_type="str", description="URL de la fiche source.")
    scraped_at = Field(value_type="str", description="Date de collecte ISO 8601 avec fuseau.")

    # Édition, variante et caractéristiques visuelles.
    set = Field(value_type="dict", description="Nom, code et série de l'extension ou du produit.")
    number = Field(value_type="str", description="Numéro de collection attribué par le catalogue.")
    printed_number = Field(value_type="str", description="Numérotation effectivement imprimée.")
    release_date = Field(value_type="str", description="Date de parution avec la précision connue.")
    rarity = Field(value_type="str", description="Rareté de cette impression.")
    printing = Field(value_type="dict", description="Finition, cadre, tampons et autres variantes.")
    games = Field(value_type="list[str]", description="Supports de jeu indiqués par la source.")
    layout = Field(value_type="str", description="Disposition de la carte, par exemple transform.")
    illustrators = Field(value_type="list[str]", description="Noms des artistes crédités.")
    copyright = Field(value_type="str", description="Mention de copyright imprimée.")
    images = Field(value_type="dict[str, str]", description="URLs absolues par vue ou format.")

    # Règles et caractéristiques de jeu.
    mana_cost = Field(value_type="str", description="Coût de mana Oracle avec ses symboles.")
    printed_mana_cost = Field(value_type="str", description="Coût de mana tel qu’imprimé.")
    mana_value = Field(value_type="int | float", description="Valeur de mana, y compris zéro.")
    colors = Field(value_type="list[str]", description="Couleurs de la carte.")
    color_identity = Field(value_type="list[str]", description="Identité couleur de la carte.")
    color_indicator = Field(
        value_type="list[str]", description="Couleurs indiquées par la pastille."
    )
    produced_mana = Field(value_type="list[str]", description="Types de mana que la carte produit.")
    type_line = Field(value_type="str", description="Ligne de type Oracle intégrale.")
    printed_type_line = Field(value_type="str", description="Ligne de type telle qu'imprimée.")
    supertypes = Field(value_type="list[str]", description="Sur-types, par exemple Legendary.")
    types = Field(value_type="list[str]", description="Types de carte, par exemple Artifact.")
    subtypes = Field(value_type="list[str]", description="Sous-types, par exemple Equipment.")
    power = Field(value_type="str", description="Force Oracle, y compris les expressions comme *.")
    toughness = Field(
        value_type="str", description="Endurance Oracle, y compris les expressions comme 1+*."
    )
    printed_power = Field(value_type="str", description="Force imprimée sur cette édition.")
    printed_toughness = Field(value_type="str", description="Endurance imprimée sur cette édition.")
    loyalty = Field(value_type="str", description="Loyauté initiale d'un planeswalker.")
    defense = Field(value_type="str", description="Défense initiale d'une bataille.")
    hand_modifier = Field(
        value_type="str", description="Modificateur de main d'une carte Vanguard."
    )
    life_modifier = Field(value_type="str", description="Modificateur de vie d'une carte Vanguard.")
    attraction_lights = Field(
        value_type="list[int]", description="Numéros allumés d'une Attraction."
    )
    keywords = Field(value_type="list[str]", description="Mots-clés répertoriés par la source.")
    printed_text = Field(value_type="str", description="Texte de règles de cette impression.")
    oracle_text = Field(value_type="str", description="Texte de règles Oracle au moment du relevé.")
    flavor_text = Field(value_type="str", description="Texte d'ambiance dans la langue imprimée.")

    # Parties d'une carte, relations et données de catalogue.
    faces = Field(value_type="list[dict]", description="Faces ou parties dans l'ordre de lecture.")
    related_cards = Field(value_type="list[dict]", description="Cartes liées et nature du lien.")
    legalities = Field(value_type="dict[str, str]", description="Statut de légalité par format.")
    rulings = Field(value_type="list[dict]", description="Précisions de règles datées et sourcées.")
    is_reserved = Field(value_type="bool", description="Présence sur la Reserved List.")
    text_blocks = Field(value_type="list[dict]", description="Sections de texte ordonnées.")
    raw_text = Field(value_type="str", description="Transcription intégrale fournie par la source.")
    additional_attributes = Field(value_type="dict", description="Autres caractéristiques en JSON.")
