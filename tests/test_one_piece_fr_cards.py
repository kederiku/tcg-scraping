"""Contracts for printings from Bandai's French catalogue."""

from datetime import datetime

import pytest
from scrapy.http import HtmlResponse

from tcg_scraper.item_one_piece import ItemOnePiece
from tcg_scraper.one_piece_cards import parse_card

BASE = "https://fr.onepiece-cardgame.com"
FRONT = "../images/cardlist/card/OP14-001_p1.webp?261016"
MODAL = """
<dl class="modalCol" id="OP14-001_p1"><dt><div class="infoCol">
  <span>OP14-001</span> | <span>L</span> | <span>LEADER</span></div>
  <div class="cardName">L&#039;Écaillé</div></dt><dd>
  <div class="frontCol"><img src="/images/cardlist/dummy.gif"
      data-src="../images/cardlist/card/OP14-001_p1.webp?261016"></div>
  <div class="backCol">
    <div class="cost"><h3>Vie</h3>4</div><div class="attribute"><h3>Attribut</h3>
      <img alt="Frappe/Spécial"><i>Frappe/Spécial</i></div>
    <div class="power"><h3>Puissance</h3>5000</div><div class="counter"><h3>Contre</h3>-</div>
    <div class="color"><h3>Couleur</h3>Rouge/Bleu</div>
    <div class="block"><h3>Numéro<br>de bloc</h3>4</div>
    <div class="feature"><h3>Type</h3>Animal/Royaume d&#039;Alabasta</div>
    <div class="text"><h3>Effet</h3>[Bloqueur]<br>[DON!!&nbsp;x1] [En attaquant]
      Votre Leader gagne [Initiative].<br>Si le Leader adverse a l'attribut <Tranche>, piochez.
    </div><div class="trigger"><h3>Déclenchement</h3>[Déclenchement] Jouez cette carte.</div>
    <div class="getInfo"><h3>Extension</h3>-L'AVENTURE- [OP15-EB04]</div>
    <div class="getInfo remarks"><h3>Notes</h3><a href="/topics/notice.php">Cartes Errata</a></div>
  </div></dd></dl>"""


def parse(html=MODAL, series="622115", name="BOOSTER -L'AVENTURE- [OP15-EB04]"):
    response = HtmlResponse(
        f"{BASE}/cardlist/?series={series}#old", body=html.encode(), encoding="utf-8"
    )
    return parse_card(response, response.css(".modalCol")[0], series, name, language="fr")


def test_printing_records_french_stats_set_image_and_provenance():
    item = parse()
    assert isinstance(item, ItemOnePiece)
    assert item["language"] == "fr" and item["region"] == "FR"
    assert item["source_name"] == "fr.onepiece-cardgame.com"
    assert item["source_url"] == BASE + "/cardlist/?series=622115#OP14-001_p1"
    assert item["card_id"] == "fr.onepiece-cardgame.com:622115:OP14-001_p1"
    assert item["external_ids"] == {"series": "622115", "card": "OP14-001_p1"}
    assert datetime.fromisoformat(item["scraped_at"]).utcoffset() is not None
    assert item["printing"] == {"variant": "p1"}
    assert item["name"] == "L'Écaillé"
    assert item["number"] == "OP14-001" and item["rarity"] == "L" and item["card_type"] == "LEADER"
    assert item["colors"] == ["Rouge", "Bleu"] and item["types"] == ["Animal", "Royaume d'Alabasta"]
    assert item["attributes"] == ["Frappe", "Spécial"]
    assert item["block_icon"] == "4" and item["life"] == "4" and item["power"] == "5000"
    assert "cost" not in item and "counter" not in item
    assert item["images"] == {"front": BASE + "/images/cardlist/card/OP14-001_p1.webp?261016"}
    assert item["set"] == {
        "code": "OP15-EB04",
        "name": "-L'AVENTURE- [OP15-EB04]",
        "series": "BOOSTER -L'AVENTURE- [OP15-EB04]",
    }
    assert item["additional_attributes"]["remarks"] == [
        {
            "text": "Cartes Errata",
            "links": [{"label": "Cartes Errata", "url": BASE + "/topics/notice.php"}],
        }
    ]


def test_printed_effects_keep_adjacent_labels_symbols_and_the_separate_trigger():
    item = parse()
    assert item["effects"] == [
        {"text": "[Bloqueur]", "labels": ["[Bloqueur]"]},
        {
            "text": "[DON!!\xa0x1] [En attaquant] Votre Leader gagne [Initiative].",
            "labels": ["[DON!!\xa0x1]", "[En attaquant]"],
        },
        {"text": "Si le Leader adverse a l'attribut <Tranche>, piochez."},
    ]
    assert item["keywords"] == ["Bloqueur"]
    assert item["trigger"] == "[Déclenchement] Jouez cette carte."
    assert [block["title"] for block in item["text_blocks"]] == ["Effet", "Déclenchement"]
    assert item["raw_text"] == (
        "[Bloqueur]\n[DON!!\xa0x1] [En attaquant] Votre Leader gagne [Initiative].\n"
        "Si le Leader adverse a l'attribut <Tranche>, piochez.\n[Déclenchement] Jouez cette carte."
    )


def test_promos_keep_their_printed_product_and_only_observed_statistics():
    html = """<dl class="modalCol" id="P-155"><dt><div class="infoCol">
    <span>P-155</span> | <span>P</span> | <span>PERSONNAGE</span></div></dt>
    <dd><div class="backCol"><div class="cost"><h3>Coût</h3>0</div>
    <div class="attribute"><h3>Attribut</h3><img alt="Distance"></div>
    <div class="counter"><h3>Contre</h3>+1000</div><div class="text"><h3>Effet</h3>-</div>
    <div class="getInfo"><h3>Extension</h3>Pack de Tournoi 2026 Vol.1</div></div></dd></dl>"""
    item = parse(html, "622901", "Carte promo")
    assert item["cost"] == "0" and item["counter"] == "+1000"
    assert item["attributes"] == ["Distance"]
    assert item["set"] == {"series": "Carte promo", "name": "Pack de Tournoi 2026 Vol.1"}
    assert "life" not in item and "printing" not in item and "raw_text" not in item


def test_printed_rules_and_inline_triggers_preserve_their_position():
    rule = "Le nom de cette carte est aussi considéré comme [Sanji] selon les règles."
    html = f"""<dl class="modalCol" id="OP18-045"><dd><div class="backCol"><div class="text">
    <h3>Effet</h3>{rule}<br>[Initiative&nbsp;: Personnage]<br>[Déclenchement] Piochez 1 carte.
    </div></div></dd></dl>"""
    item = parse(html)
    assert item["rules"] == [rule]
    assert item["trigger"] == "[Déclenchement] Piochez 1 carte."
    assert item["keywords"] == ["Initiative\xa0: Personnage"]
    assert len(item["effects"]) == 1
    assert (
        item["raw_text"]
        == f"{rule}\n[Initiative\xa0: Personnage]\n[Déclenchement] Piochez 1 carte."
    )


@pytest.mark.parametrize(
    "front",
    [
        "../images/cardlist/card/dummy.gif",
        "//www.onepiece-cardgame.com/images/cardlist/card/OP14-001.png",
        "/images/cardlist/attribute/ico_type03.png",
    ],
)
def test_images_require_a_french_card_face(front):
    assert "images" not in parse(MODAL.replace(FRONT, front))
