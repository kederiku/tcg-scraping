"""Parse a printing from Bandai's Japanese or French ONE PIECE catalogue."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urldefrag, urlsplit

from tcg_scraper.item_one_piece import ItemOnePiece

MISSING = {"", "-", "－", "―", "—"}
FR_PRODUCT_CODE = re.compile(r"\[([A-Z]+-?\d+(?:-[A-Z]+-?\d+)*)\]")
# Some French effect texts contain literal <Tranche> written as an unescaped HTML tag.
FR_ATTRIBUTE_TAGS = {
    name.lower(): name for name in ("Tranche", "Frappe", "Spécial", "Sagesse", "Distance")
}


@dataclass(frozen=True)
class Catalogue:
    source: str
    region: str
    image_hosts: tuple[str, ...]
    fields: dict[str, str]
    product_code: re.Pattern
    label: re.Pattern
    keywords: set[str]
    trigger_label: str
    rule: re.Pattern


CATALOGUES = {
    "ja": Catalogue(
        source="onepiece-cardgame.com",
        region="JP",
        image_hosts=("onepiece-cardgame.com", "www.onepiece-cardgame.com"),
        fields={
            "ライフ": "life",
            "コスト": "cost",
            "パワー": "power",
            "カウンター": "counter",
            "ブロックアイコン": "block_icon",
            "色": "colors",
            "属性": "attributes",
            "特徴": "types",
        },
        product_code=re.compile(r"【([A-Z]+-[0-9]+)】"),
        label=re.compile(r"(【([^】]+)】)"),
        keywords={
            "ブロッカー",
            "速攻",
            "速攻：キャラ",
            "キャラ：速攻",
            "ダブルアタック",
            "バニッシュ",
            "ブロック不可",
        },
        trigger_label="【トリガー】",
        rule=re.compile(r"^ルール上"),
    ),
    "fr": Catalogue(
        source="fr.onepiece-cardgame.com",
        region="FR",
        image_hosts=("fr.onepiece-cardgame.com",),
        fields={
            "Vie": "life",
            "Coût": "cost",
            "Puissance": "power",
            "Contre": "counter",
            "Numéro de bloc": "block_icon",
            "Couleur": "colors",
            "Attribut": "attributes",
            "Type": "types",
        },
        product_code=FR_PRODUCT_CODE,
        label=re.compile(r"\s*(\[([^\]]+)\])"),
        keywords={
            "Bloqueur",
            "Initiative",
            "Initiative : Personnage",
            "Double attaque",
            "Exil",
            "Imblocable",
        },
        trigger_label="[Déclenchement]",
        rule=re.compile(r"\bselon les règles\b", re.I),
    ),
}


def _text(element, *, french_attributes=False):
    """Read inline content in order, including icon alternatives and explicit line breaks."""
    if element is None:
        return ""
    parts = []

    def visit(node):
        if node.tag == "br":
            parts.append("\n")
        elif node.tag == "img":
            parts.append(node.get("alt", ""))
        elif (
            isinstance(node.tag, str) and node.tag != "h3" and node.get("class") != "getInfoBtnCol"
        ):
            if french_attributes and node.tag in FR_ATTRIBUTE_TAGS:
                parts.append(f"<{FR_ATTRIBUTE_TAGS[node.tag]}>")
            parts.append(re.sub(r"[\t\r\n]+", " ", node.text or ""))
            for child in node:
                visit(child)
                parts.append(re.sub(r"[\t\r\n]+", " ", child.tail or ""))

    visit(element)
    return "\n".join(
        re.sub(r" +", " ", line).strip() for line in "".join(parts).split("\n")
    ).strip()


def _links(response, element):
    return [
        {"label": _text(anchor), "url": response.urljoin(anchor.get("href"))}
        for anchor in element.iter("a")
        if anchor.get("href")
    ]


def _read_text(item, sections, catalogue):
    blocks, effects, keywords, rules, triggers = [], [], [], [], []
    for section in sections:
        text = _text(section, french_attributes=item["language"] == "fr")
        if text in MISSING:
            continue
        kind = "trigger" if section.get("class") == "trigger" else "effect"
        blocks.append({"kind": kind, "title": section.findtext("h3"), "text": text})
        if kind == "trigger":
            triggers.append(text)
            continue
        for line in text.splitlines():
            if not line:
                continue
            if line.startswith(catalogue.trigger_label):
                triggers.append(line)
                continue
            if catalogue.rule.search(line):
                rules.append(line)
                continue
            effect = {"text": line}
            labels = []
            offset = 0
            # Mid-sentence mentions can describe other cards' keywords.
            while match := catalogue.label.match(line, offset):
                label, keyword = match.groups()
                labels.append(label)
                if " ".join(keyword.split()) in catalogue.keywords and keyword not in keywords:
                    keywords.append(keyword)
                offset = match.end()
            if labels:
                effect["labels"] = labels
            effects.append(effect)
    if blocks:
        item["text_blocks"] = blocks
        item["raw_text"] = "\n".join(block["text"] for block in blocks)
    if triggers:
        item["trigger"] = "\n".join(triggers)
    for key, values in (("effects", effects), ("keywords", keywords), ("rules", rules)):
        if values:
            item[key] = values


def _faq(response, modal):
    entries = []
    for column in modal.css(".cardFaqCol"):
        entry = {}
        for key, selector in (
            ("id", ".cardFaqNum"),
            ("question", ".cardFaqDataQ"),
            ("answer", ".cardFaqDataA"),
        ):
            if nodes := column.css(selector):
                if text := _text(nodes[0].root):
                    entry[key] = text
        if date := column.css("time::attr(datetime)").get():
            entry["updated_at"] = date
        if links := _links(response, column.root):
            entry["links"] = links
        if entry:
            entries.append(entry)
    return entries


def parse_card(response, modal, series_id, series_name, *, language="ja") -> ItemOnePiece:
    """Extract printed card data, product and FAQ information without making requests."""
    catalogue = CATALOGUES[language]
    modal_id = modal.attrib["id"]
    item = ItemOnePiece(
        card_id=f"{catalogue.source}:{series_id}:{modal_id}",
        language=language,
        region=catalogue.region,
        external_ids={"series": series_id, "card": modal_id},
        source_name=catalogue.source,
        source_url=f"{urldefrag(response.url).url}#{modal_id}",
        scraped_at=datetime.now(UTC).isoformat(),
    )
    if names := modal.css(".cardName"):
        item["name"] = _text(names[0].root)
    for key, node in zip(
        ("number", "rarity", "card_type"), modal.css(".infoCol > span"), strict=False
    ):
        if (value := _text(node.root)) not in MISSING:
            item[key] = value

    # The suffix comes from the catalogue's ID, which distinguishes even unnamed variants.
    number = item.get("number")
    if number and modal_id.startswith(number + "_"):
        item["printing"] = {"variant": modal_id[len(number) + 1 :]}

    if front := modal.css(".frontCol img::attr(data-src)").get():
        url = response.urljoin(front)
        location = urlsplit(url)
        if (
            location.scheme == "https"
            and location.hostname in catalogue.image_hosts
            and location.path.startswith("/images/cardlist/card/")
            and not location.path.rsplit("/", 1)[-1].lower().startswith("dummy.")
        ):
            item["images"] = {"front": url}

    sections = []
    for heading in modal.css(".backCol h3"):
        node = heading.root.getparent()
        if node.get("class") in {"text", "trigger"}:
            sections.append(node)
            continue
        separator = " " if language == "fr" else ""
        title = separator.join(heading.root.itertext()).strip()
        key = catalogue.fields.get(" ".join(title.split()))
        if not key:
            continue
        value = _text(node)
        if key == "attributes" and language == "fr":
            # The icon's alt and its visible caption both contain the same attributes.
            value = _text(node.find("i")) or value
        if value not in MISSING:
            if key in {"colors", "attributes", "types"}:
                item[key] = [s.strip() for s in re.split("[/／]", value) if s.strip()]
            else:
                item[key] = value
    _read_text(item, sections, catalogue)

    details = {}
    product = {"series": series_name} if series_name else {}
    if acquisition := modal.css(".getInfo:not(.remarks)"):
        node = acquisition[0].root
        if (name := _text(node)) not in MISSING:
            product["name"] = name
            if code := catalogue.product_code.search(name):
                product["code"] = code[1]
        if links := _links(response, node):
            details["product_links"] = links
    if product:
        item["set"] = product
    remarks = []
    for node in modal.css(".remarks"):
        remark = {}
        if text := _text(node.root):
            remark["text"] = text
        if links := _links(response, node.root):
            remark["links"] = links
        if remark:
            remarks.append(remark)
    if remarks:
        details["remarks"] = remarks
    if faq := _faq(response, modal):
        details["faq"] = faq
    if details:
        item["additional_attributes"] = details
    return item
