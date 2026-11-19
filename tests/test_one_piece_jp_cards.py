"""Contracts for the Japanese catalogue's card modals, using offline HTML."""

from datetime import datetime

from scrapy.http import HtmlResponse

from tcg_scraper.item_one_piece import ItemOnePiece
from tcg_scraper.one_piece_jp_cards import parse_card

BASE = "https://www.onepiece-cardgame.com"


def parse(html, series_id="550118", series_name="ブースターパック 神の支配【OP-18】"):
    response = HtmlResponse(
        BASE + "/cardlist/?series=" + series_id, body=html.encode(), encoding="utf-8"
    )
    return parse_card(response, response.css(".modalCol")[0], series_id, series_name)


LEADER = """
<dl class="modalCol" id="OP18-001">
  <dt><div class="infoCol"><span>OP18-001</span> | <span>L</span> | <span>LEADER</span></div>
  <div class="cardName">カルー</div></dt>
  <dd><div class="frontCol"><img src="/images/cardlist/dummy.gif"
       data-src="../images/cardlist/card/OP18-001.png?261113" alt="カルー"></div>
  <div class="backCol">
    <div class="cost"><h3>ライフ</h3>4</div>
    <div class="attribute"><h3>属性</h3><img alt="斬/射" src="/icons/type.png"></div>
    <div class="power"><h3>パワー</h3>5000</div><div class="counter"><h3>カウンター</h3>-</div>
    <div class="color"><h3>色</h3>赤/青</div><div class="block"><h3>ブロック<br>アイコン</h3>5</div>
    <div class="feature"><h3>特徴</h3>動物/アラバスタ王国</div>
    <div class="text"><h3>テキスト</h3>【ドン‼×1】【アタック時】カード1枚を引く。<br>【速攻】</div>
    <div class="trigger"><h3>トリガー</h3>【トリガー】<img alt="①">を払う。</div>
  </div><div class="getInfo"><h3>入手情報</h3>神の支配【OP-18】
      <div class="getInfoBtnCol"><a class="getInfoBtn" href="./?series=550118">カードリスト</a>
      <a class="getInfoBtn" href="/products/op18.html">商品情報</a></div></div>
  <div class="getInfo remarks"><h3>備考</h3>
    <a href="/topics/notice.php">訂正のお知らせ</a></div></dd>
  <dd class="cardFaqWrap"><div class="cardFaqCol">
    <div class="cardFaqNumCol"><h5 class="cardFaqNum">Q1503</h5>
      <time datetime="2026-11-13">2026.11.13</time>更新</div>
    <dl><dt class="cardFaqDataQ">できますか？</dt>
    <dd class="cardFaqDataA">いいえ。<br>カード1枚を引きます。</dd></dl></div></dd></dl>
"""


def test_leader_keeps_printed_statistics_and_provenance():
    item = parse(LEADER)
    assert isinstance(item, ItemOnePiece)
    assert item["name"] == "カルー"
    assert item["number"] == "OP18-001" and item["rarity"] == "L" and item["card_type"] == "LEADER"
    assert item["language"] == "ja" and item["region"] == "JP"
    assert item["source_url"] == BASE + "/cardlist/?series=550118#OP18-001"
    assert datetime.fromisoformat(item["scraped_at"]).utcoffset() is not None
    assert item["life"] == "4" and item["power"] == "5000" and item["block_icon"] == "5"
    assert "counter" not in item and "cost" not in item
    assert item["colors"] == ["赤", "青"] and item["types"] == ["動物", "アラバスタ王国"]
    assert item["attributes"] == ["斬", "射"]
    assert item["images"] == {"front": BASE + "/images/cardlist/card/OP18-001.png?261113"}
    assert item["set"] == {
        "code": "OP-18",
        "name": "神の支配【OP-18】",
        "series": "ブースターパック 神の支配【OP-18】",
    }


def test_effects_preserve_labels_breaks_inline_symbols_and_the_separate_trigger():
    item = parse(LEADER)
    assert item["effects"] == [
        {
            "labels": ["【ドン‼×1】", "【アタック時】"],
            "text": "【ドン‼×1】【アタック時】カード1枚を引く。",
        },
        {"labels": ["【速攻】"], "text": "【速攻】"},
    ]
    assert item["keywords"] == ["速攻"]
    assert item["trigger"] == "【トリガー】①を払う。"
    assert (
        item["raw_text"]
        == "【ドン‼×1】【アタック時】カード1枚を引く。\n【速攻】\n【トリガー】①を払う。"
    )
    assert [section["title"] for section in item["text_blocks"]] == ["テキスト", "トリガー"]


def test_faq_and_remarks_are_separate_from_card_and_set_text():
    item = parse(LEADER)
    details = item["additional_attributes"]
    assert details["product_links"] == [
        {"label": "カードリスト", "url": BASE + "/cardlist/?series=550118"},
        {"label": "商品情報", "url": BASE + "/products/op18.html"},
    ]
    assert details["remarks"] == [
        {
            "text": "訂正のお知らせ",
            "links": [{"label": "訂正のお知らせ", "url": BASE + "/topics/notice.php"}],
        }
    ]
    assert details["faq"] == [
        {
            "id": "Q1503",
            "updated_at": "2026-11-13",
            "question": "できますか？",
            "answer": "いいえ。\nカード1枚を引きます。",
        }
    ]
    assert "release_date" not in item


def test_reprints_keep_their_variant_and_product_in_their_identity():
    html = """
    <dl class="modalCol" id="ST01-006_r1"><dt><div class="infoCol">
    <span>ST01-006</span> | <span>C</span> | <span>CHARACTER</span></div>
    <div class="cardName">カード</div></dt><dd><div class="frontCol"><img
    src="/images/cardlist/dummy.gif"></div><div class="backCol">
    <div class="cost"><h3>コスト</h3>0</div><div class="power"><h3>パワー</h3>0</div>
    <div class="counter"><h3>カウンター</h3>+1000</div><div class="text"><h3>テキスト</h3>-</div>
    </div><div class="getInfo"><h3>入手情報</h3>プロモーションパック Vol.1</div></dd></dl>"""
    first = parse(html, "550901", "プロモーションカード")
    second = parse(html, "550801", "限定商品収録カード")
    assert first["card_id"] != second["card_id"]
    assert first["external_ids"] == {"series": "550901", "card": "ST01-006_r1"}
    assert first["printing"]["variant"] == "r1"
    assert first["number"] == "ST01-006" and first["set"]["name"] == "プロモーションパック Vol.1"
    assert "code" not in first["set"] and "images" not in first
    assert first["cost"] == "0" and first["power"] == "0" and first["counter"] == "+1000"
    assert "life" not in first and "raw_text" not in first and "effects" not in first


def test_explicit_deck_rule_keeps_its_position_in_the_transcription():
    rule = "ルール上、このカードはデッキに何枚でも入れることができる。"
    item = parse(LEADER.replace("【速攻】", rule))
    assert item["rules"] == [rule]
    assert len(item["effects"]) == 1
    assert rule in item["text_blocks"][0]["text"]


def test_trigger_printed_inside_the_effect_section_is_kept_as_a_trigger():
    # OP01-119 prints both sections inside .text instead of using a .trigger div.
    html = """<dl class="modalCol" id="OP01-119"><dd><div class="backCol"><div class="text">
    <h3>テキスト</h3>【カウンター】パワー+4000。<br>【トリガー】ドン‼1枚までを追加する。
    </div></div></dd></dl>"""
    item = parse(html)
    assert item["trigger"] == "【トリガー】ドン‼1枚までを追加する。"
    assert item["effects"] == [
        {"labels": ["【カウンター】"], "text": "【カウンター】パワー+4000。"}
    ]
    assert item["raw_text"] == "【カウンター】パワー+4000。\n【トリガー】ドン‼1枚までを追加する。"
