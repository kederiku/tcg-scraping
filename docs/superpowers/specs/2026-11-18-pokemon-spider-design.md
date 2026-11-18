# Spider du catalogue japonais Pokémon

## Demande

Parcourir toutes les pages de la recherche fournie, suivre chaque fiche de carte
et produire un `ItemPokemon`, avec l'illustrateur et l'URL de l'image. Uniquement
les caractéristiques de la carte, sans données commerciales.

## Conception retenue

- Spider `pokemon_jp`, HTTP : le site appelle lui-même `resultAPI.php` avec ses
  filtres et `page`, puis ouvre `details.php/card/<id>/regu/<regulation>`.
- Conserver les filtres du lien de recherche ; utiliser `thisPage` / `maxPage` pour
  parcourir la pagination et le dédoublonnage Scrapy pour les fiches.
- `max_pages=0` et `max_cards=0` signifient sans limite ; `start_page=1` par défaut.
  La commande de démonstration est bornée, la commande complète explicite.
- Réutiliser robots.txt, délais, AutoThrottle et arrêt sur 403/429 du projet.
- Extraire les champs présents dans le HTML : identité, numérotation, extension,
  illustration, statistiques, attaques, talents, règles, textes Dresseur/Énergie.
  Garder les libellés japonais, les symboles d'énergie et les blocs non reconnus.
  Ne pas déduire de l'image les champs absents (rareté, marque de régulation, etc.).
- Rejeter les pages/API incohérentes avec une raison d'arrêt explicite. Les liens
  vers des produits et recherches d'évolution ne sont pas des fiches à suivre.
- Export JSONL ; collecte complète avec JOBDIR et ajout au fichier pour permettre
  une reprise après arrêt propre. Aucune collecte exhaustive pendant le développement.

## Validation

Fixtures synthétiques reprenant la structure observée (Pokémon, Dresseur, Énergie,
formats spéciaux), tests de pagination/erreurs/limites et crawl local de bout en bout.
Puis échantillon réel borné, Ruff et suite existante. Aucune nouvelle dépendance.
