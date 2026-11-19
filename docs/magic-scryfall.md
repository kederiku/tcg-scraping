# Catalogue Magic de Scryfall

Depuis la racine du projet, cette commande écrit une ligne JSON par impression
dans `data/magic_scryfall.jsonl`.

```powershell
.\make.ps1 magic-all
```

L’équivalent Make est `make magic-all`. Pour utiliser directement Scrapy dans le
conteneur, lancer `docker compose run --rm crawler scrapy crawl magic_scryfall`.
Chaque exécution utilise l’instantané disponible à ce moment-là et publie le
fichier complet après vérification. Prévoir plusieurs gigaoctets d’espace libre
pour le téléchargement compressé et le JSONL, en plus de l’export précédent.

Pour essayer cinq fiches, utiliser `.\make.ps1 magic` ou `make magic`.
Le nombre est réglable avec `-MaxCards 20` ou `MAX_CARDS=20`. L’échantillon
va dans `data/magic_scryfall-sample.jsonl`. Il contient les premières impressions
du même instantané et télécharge donc aussi les fichiers sources complets.

## Couverture

Le spider lit les fichiers **All Cards** et **Rulings** que publie Scryfall.
All Cards contient chaque fiche dans chaque langue répertoriée par le site.
Le code conserve toutes les éditions, y compris les promotions, les jetons,
les versions numériques et les avant-premières déjà présentes. La couverture
de chaque traduction dépend des données disponibles chez Scryfall.
[Extensions de Scryfall](https://scryfall.com/sets) · [Export multilingue All Cards](https://api.scryfall.com/bulk-data/all-cards) · [Export Rulings](https://api.scryfall.com/bulk-data/rulings).

- **Impression et langue.** `card_id` est l’identifiant Scryfall de l’impression,
  `language` reprend le code de langue et `set.code` garde le code d’édition.
  Plusieurs impressions peuvent partager un `oracle_id`. Lorsqu’une fiche propose
  plusieurs finitions, elles figurent dans `printing.available_finishes`.
- **Textes.** `oracle_name` et `oracle_text` contiennent les données de référence.
  `name` conserve le nom localisé lorsqu’il est disponible et le nom de référence
  pour une impression anglaise. Un texte imprimé absent de la source reste
  inconnu. `number` est le numéro du catalogue, y compris pour les cartes anciennes.
- **Faces et illustrations.** Les faces conservent leurs propres noms, textes,
  statistiques et URLs d’images. Les entrées de `images` gardent les formats
  Scryfall tels que `normal`, `large` et `png`. Les liens suffisent pour retrouver
  les images sans télécharger leur contenu.
- **Règles.** Les décisions de règles sont rattachées par identifiant Oracle,
  y compris à une face qui possède son propre identifiant. Chaque décision
  conserve sa date, sa source et son texte dans la langue fournie.
- **Autres informations.** `external_ids` garde les références aux catalogues,
  `related_cards` les liens entre cartes et `additional_attributes` les autres
  caractéristiques publiées. Les prix et les liens d’achat sont exclus.
  [Schéma ItemMagic](item-magic.md).

## Fichiers et interruptions

Scrapy télécharge les deux instantanés gzip sur disque. Le spider vérifie leur
taille annoncée, lit les objets ligne par ligne et rapproche le nombre de cartes
lues du nombre de lignes exportées. La lecture complète vérifie également
l’intégrité gzip. Le JSONL temporaire se trouve sur le même volume que la
destination. Une fois les contrôles réussis, il remplace l’export précédent.
Après un échec ou un arrêt, relancer la commande pour repartir de l’instantané
disponible.

Pour choisir un autre fichier tout en gardant ce remplacement en fin de collecte,
passer `-a output=data/mon-catalogue.jsonl` à Scrapy. L’écriture dans un
fichier local unique avec `-O data/mon-catalogue.jsonl` bénéficie de la même
vérification. L’ajout avec `-o`, les destinations distantes et les configurations
d’export personnalisées suivent le comportement standard de Scrapy.
