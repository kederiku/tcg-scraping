# Spider One Piece japonais

Depuis la racine du projet, avec Docker démarré, lancer sous PowerShell :

```powershell
.\make.ps1 one-piece
```

Avec Make, utiliser `make one-piece`. Avec l’environnement Python du projet,
lancer directement `python -m scrapy crawl one_piece_jp`.

Chaque lancement écrit **`data/one_piece_jp.jsonl`** en UTF-8 et remplace le
contenu précédent. Chaque ligne contient un [ItemOnePiece](item-one-piece.md)
par impression, avec ses caractéristiques, ses effets en japonais, les Q&A
affichées et l’URL officielle du recto dans `images.front`. Les illustrations
alternatives conservent leur propre identifiant.

Le spider découvre les séries dans le menu du catalogue Bandai et lit les
fiches accessibles au clic. Il consulte le calendrier des produits pour
écarter les extensions à venir. Dans les groupes promotionnels et limités, il
écarte une distribution annoncée pour plus tard dans le calendrier ou le
libellé d’acquisition. Il inclut les promotions dont la date est inconnue.
[Catalogue japonais Bandai](https://www.onepiece-cardgame.com/cardlist/)

Pour essayer une seule série et écrire son résultat dans un fichier de test :

```sh
docker compose run --rm crawler scrapy crawl one_piece_jp -a series=550101 -O data/one_piece_jp-sample.jsonl
```
