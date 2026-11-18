# Spider Pokémon indonésien

Ajouter `pokemon_id` pour les cartes physiques indonésiennes de TCG Collector,
avec le même ItemPokemon, export JSONL local, Docker et reprise que JP/KR.

La recherche demandée est `/cards/id?releaseDateOrder=newToOld&displayAs=images`.
Le 18 novembre 2026, robots.txt interdit la pagination (`?page=`/`&page=`) et
`/api/`. L'index public `https://static.tcgcollector.com/sitemaps/sitemap.xml`
référence trois fichiers `sitemap-cards-idN.xml`, contenant 14 004 liens uniques,
autant que la recherche. Utiliser exclusivement ces sitemaps et les fiches HTML
autorisées. Ne pas suivre les liens des autres régions, listes, filtres ou API.
L'ordre du sitemap ne garantit pas le tri chronologique de la recherche.

Extraire les caractéristiques disponibles : identité, langue de l'impression
`id`, région `ID`, extension, numéro, rareté, illustrateurs, URLs des images,
PV, types, évolutions, attaques, talents, règles, faiblesses, résistances,
retraite et données Dresseur/Énergie. Valider la région de chaque fiche via
l'état JSON public embarqué dans son HTML, sans exécuter de JavaScript.
Les noms/effets observés sont en anglais : documenter cette langue de texte
séparément. Ne pas inventer le texte d'ambiance, absent des fiches examinées,
ni le nom indonésien à partir de l'image. Pas d'OCR ni de prix/collection privée.
Exclure l'image générique `default-card-image` (dos de remplacement) des rectos
exportés et signaler `additional_attributes.image_status = "missing"`.
Une fiche peut regrouper des finitions : les conserver comme variantes
disponibles, sans attribuer arbitrairement une finition à l'image.

Limiter par `max_cards` et `max_sitemaps` (0 = illimité), dédupliquer les IDs et
persister le budget dans JOBDIR. Garder robots.txt, délais, AutoThrottle et
arrêt 403/429. Échouer explicitement sur un catalogue ou une fiche invalide.
Les commandes `pokemon-id` et `pokemon-id-all` séparent l'essai de cinq fiches
et le fichier cumulatif complet. Les essais génériques ne remplacent pas cet export.

Vérifier avec fixtures synthétiques, crawl local incluant plusieurs sitemaps,
limites, reprise, erreurs/blocages, tests des commandes et essai réel borné.
Pas de collecte complète automatique, commit ou publication dans cette demande.
