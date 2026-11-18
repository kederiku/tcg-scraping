# ItemPokemon

Demande : un item Scrapy pour les caractéristiques des cartes physiques du JCC
Pokémon, tous types et époques. L'utilisateur exclut les prix, vendeurs, état et grading.

## Choix

Un seul `scrapy.Item`, nommé `ItemPokemon`, dans `tcg_scraper/item_pokemon.py`.
Une classe par époque ou catégorie imposerait des changements à chaque nouvelle
mécanique et gérerait mal les cartes combinant plusieurs fonctions. Des champs
libres sans schéma masqueraient les fautes de frappe. Le choix retenu est un
item commun à champs déclarés, tous facultatifs, avec structures imbriquées
documentées et un dictionnaire d'extension explicite.

Un item représente une impression, dans une langue et une variante précises.
Les textes, numéros et valeurs imprimées restent des chaînes. Les collections
(attaques, talents, types, Pokémon représentés, etc.) sont des listes sans limite
arbitraire. Le modèle accepte les cartes partielles et multiparties. Aucune liste
fermée de générations, sous-types ou mécaniques ; aucune donnée inventée par défaut.

Les métadonnées de `Field` documentent les types attendus ; elles ne valident ni
ne convertissent les données. Les sous-structures restent des dictionnaires JSON.
Le texte brut et les attributs supplémentaires préservent les cas non modélisés.
Cela permet l'extension sans promettre un inventaire exhaustif de chaque carte existante.

Hors périmètre : spider marchand, récupération réseau, validation métier, API payante,
cartes numériques Pocket, offres de vente et valeurs de marché.

Validation : exports JSONL de fixtures synthétiques anciennes/modernes, Dresseur,
Énergie et cartes multiparties ; conservation des symboles, listes et champs absents.
