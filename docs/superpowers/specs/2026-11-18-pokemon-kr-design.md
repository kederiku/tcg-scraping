# Catalogue coréen Pokémon

Créer l'équivalent de `pokemon_jp` pour `https://pokemoncard.co.kr/cards`, avec
pagination, fiches et `ItemPokemon` en coréen, illustrateurs et URLs d'images.
Conserver les pratiques du projet, les données japonaises et les dépendances gratuites.

## Approche retenue

La page vide attend Recherche. Son JavaScript fait un POST vers `/v2/ajax2_dev2` :
`action=search_text_cards`, `search_text=`, `search_params=all`, `limit=0`.
« Charger plus » réutilise le `limit` retourné. L'en-tête AJAX standard
`X-Requested-With: XMLHttpRequest` est requis ; HTTP seul a été vérifié.
Le choix technique est donc Scrapy HTTP, plutôt qu'un navigateur à chaque lot.

Le spider `pokemon_kr` suit `/cards/detail/<CardNum>` et s'arrête lorsque la
réponse valide annonce `count=0`. `count` désigne le lot, pas le catalogue entier.
Les résultats peuvent être un tableau ou un objet indexé à partir de 1. Vérifier
status, count, les IDs et la progression du curseur ; un lot répété ou malformé
interrompt la collecte. Le site n'annonce pas de total global vérifiable.

`max_pages=0` et `max_cards=0` : illimité. `start_page=1` correspond au curseur 0.
Une recherche optionnelle conserve `search_text` / `search_params` sur tous les lots.
JOBDIR conserve les IDs et limites, avec un export JSONL cumulatif séparé du Japon.

Les fiches HTML fournissent nom, catégorie, stats, règles, attaques, talents, crédits,
image, numérotation, symboles de set/régulation et parfois rareté et texte descriptif.
Préserver les pictogrammes et les mécanismes inconnus. Les champs absents restent
absents ; les liens de produit/promotion ne déterminent pas automatiquement le set.
Pas d'OCR, téléchargement d'image, prix ni données de vendeur.

## Validation

Tests synthétiques : trois catégories, symboles, commentaires HTML, données absentes,
pagination POST, lot final vide, erreurs, limites et reprise persistante. Commandes
`pokemon-kr` / `pokemon-kr-all` dans Make et PowerShell, sortie générique protégée.
Suite existante et nouvelle dans Docker, essai réel borné, revue indépendante.
