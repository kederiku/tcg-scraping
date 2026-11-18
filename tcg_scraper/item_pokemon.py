"""Caractéristiques d'une impression de carte physique du JCC Pokémon.

Un item = une impression, une langue, une variante (ou une partie d'assemblage).
Tous les champs sont facultatifs : ne pas inventer de valeur si elle est inconnue.
Les métadonnées ``value_type`` documentent les types ; Scrapy ne les valide pas.
Utiliser des valeurs JSON natives dans les listes/dictionnaires imbriqués.
Voir ``docs/item-pokemon.md`` pour leur structure et les conventions.
"""

from scrapy import Field, Item


class ItemPokemon(Item):
    """Schéma commun Pokémon, Dresseur et Énergie, sans restriction d'époque.

    Les libellés restent ouverts : ex et EX, par exemple, sont distincts.
    ``additional_attributes`` et ``text_blocks`` conservent les particularités
    inconnues sans changer les champs déclarés. Aucun champ commercial.
    """

    # Identité et traçabilité de la collecte.
    card_id = Field(
        value_type="str", description="Identifiant interne de cette impression/variante."
    )
    name = Field(value_type="str", description="Nom imprimé complet, préfixes et symboles inclus.")
    language = Field(value_type="str", description="Langue de l'impression, de préférence BCP 47.")
    region = Field(value_type="str", description="Marché/région de publication si connu.")
    external_ids = Field(
        value_type="dict[str, str]", description="Identifiants par source/catalogue."
    )
    source_name = Field(value_type="str", description="Site ou catalogue d'origine.")
    source_url = Field(value_type="str", description="URL de la fiche d'origine.")
    scraped_at = Field(value_type="str", description="Date de collecte ISO 8601 avec fuseau.")

    # Catégorie et édition. Pas d'enum fermé ni de conversion des numéros.
    supertype = Field(
        value_type="str", description="Catégorie générale, ex. Pokémon/Trainer/Energy."
    )
    subtypes = Field(
        value_type="list[str]", description="Sous-types, mécaniques, affiliations/styles."
    )
    set = Field(value_type="dict", description="Extension, série, codes et tailles du set.")
    number = Field(
        value_type="str", description="Numéro dans l'extension, ex. 001, H1, TG01, SVP001."
    )
    printed_number = Field(
        value_type="str", description="Numérotation imprimée complète, ex. 201/198."
    )
    rarity = Field(value_type="str", description="Rareté de cette impression, libellé d'origine.")
    rarity_symbols = Field(value_type="list[str]", description="Symboles de rareté imprimés.")
    regulation_mark = Field(
        value_type="str", description="Marque de régulation imprimée si présente."
    )
    release_date = Field(
        value_type="str", description="Date de sortie connue, sans précision inventée."
    )
    illustrators = Field(value_type="list[str]", description="Illustrateurs/crédits artistiques.")
    copyright = Field(value_type="str", description="Mention de copyright imprimée intégrale.")
    printing = Field(value_type="dict", description="Édition, finition, tampons, format et codes.")
    images = Field(
        value_type="dict[str, str]", description="URLs nommées : front, back, large, symbol…"
    )

    # Pokémon. Les listes permettent notamment les doubles types et TAG TEAM.
    pokemon = Field(
        value_type="list[dict]", description="Pokémon représentés : nom, Pokédex, génération."
    )
    owners = Field(
        value_type="list[str]", description="Dresseurs/propriétaires nommés sur la carte."
    )
    stage = Field(value_type="str", description="Stade imprimé : Basic, Stage 1, Baby, BREAK, etc.")
    level = Field(
        value_type="str", description="Niveau imprimé, y compris les notations anciennes."
    )
    hp = Field(
        value_type="str", description="PV sous forme textuelle, sans imposer une valeur numérique."
    )
    types = Field(
        value_type="list[str]", description="Types de la carte ; conserver les types anciens."
    )
    evolves_from = Field(
        value_type="str", description="Nom/référence d'évolution effectivement indiqué."
    )
    evolution_text = Field(
        value_type="str", description="Consigne d'évolution ou de mise en jeu complète."
    )
    attacks = Field(
        value_type="list[dict]", description="Attaques : nom, coûts, dégâts, texte et catégorie."
    )
    abilities = Field(
        value_type="list[dict]", description="Talents, Pokémon Powers, Poké-Powers/Poké-Bodies."
    )
    ancient_traits = Field(value_type="list[dict]", description="Traits antiques : nom et texte.")
    weaknesses = Field(
        value_type="list[dict]", description="Faiblesses : type et valeur imprimée (+20, ×2…)."
    )
    resistances = Field(
        value_type="list[dict]", description="Résistances : type et valeur imprimée (−20…)."
    )
    retreat_cost = Field(
        value_type="list[str]", description="Symboles de retraite, répétitions conservées."
    )
    converted_retreat_cost = Field(
        value_type="int", description="Total de retraite connu ; zéro ≠ inconnu."
    )
    species = Field(value_type="str", description="Catégorie Pokédex imprimée, ex. Pokémon Souris.")
    height = Field(value_type="str", description="Taille du Pokémon avec unité/format imprimés.")
    weight = Field(value_type="str", description="Poids du Pokémon avec unité/format imprimés.")
    flavor_text = Field(value_type="str", description="Texte descriptif/Pokédex imprimé.")

    # Dresseurs et Énergies ; ces champs peuvent coexister avec les précédents.
    trainer_type = Field(value_type="str", description="Catégorie de Dresseur, sans liste fermée.")
    trainer_text = Field(value_type="str", description="Effet et texte imprimés du Dresseur.")
    energy_type = Field(
        value_type="str", description="Catégorie de carte Énergie, ex. Basic/Special."
    )
    energy_text = Field(value_type="str", description="Texte imprimé de la carte Énergie.")
    provided_energy = Field(
        value_type="list[dict]", description="Énergies fournies et conditions éventuelles."
    )

    # Règles partagées et formats particuliers, sans imposer de statistiques.
    rules = Field(
        value_type="list[str]", description="Encadrés de règles, restrictions, Récompenses, etc."
    )
    effects = Field(value_type="list[dict]", description="Autres effets/mécaniques titrés ou non.")
    composition = Field(
        value_type="dict", description="Partie et liens d'un assemblage LEGEND/V-UNION, etc."
    )
    text_blocks = Field(
        value_type="list[dict]", description="Blocs imprimés dans leur ordre de lecture."
    )
    raw_text = Field(
        value_type="str", description="Texte brut de la carte, utile pour préserver la source."
    )
    additional_attributes = Field(
        value_type="dict", description="Particularités non modélisées, JSON natif."
    )
