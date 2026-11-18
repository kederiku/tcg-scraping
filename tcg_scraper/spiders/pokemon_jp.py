"""Catalogue japonais officiel du JCC Pokémon."""

import re
from copy import deepcopy
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import scrapy
from scrapy.exceptions import CloseSpider

from tcg_scraper.item_pokemon import ItemPokemon

SEARCH_URL = (
    "https://www.pokemon-card.com/card-search/index.php?keyword=&se_ta="
    "&regulation_sidebar_form=all&pg=&illust=&sm_and_keyword=true"
)
ENERGY_ICONS = {
    "grass": "Grass",
    "fire": "Fire",
    "water": "Water",
    "electric": "Lightning",
    "psychic": "Psychic",
    "fighting": "Fighting",
    "dark": "Darkness",
    "steel": "Metal",
    "fairy": "Fairy",
    "dragon": "Dragon",
    "none": "Colorless",
}
TRAINER_HEADINGS = {
    "グッズ",
    "サポート",
    "サポーター",
    "スタジアム",
    "ポケモンのどうぐ",
    "トレーナー",
    "トレーナーズ",
}
ABILITY_HEADINGS = {"特性", "ポケパワー", "ポケボディー", "ポケモンパワー", "特殊能力"}


def icon_names(node):
    """Repeated symbols matter; icon-void is the explicit zero-energy symbol."""
    names = []
    for icon in node.css(".icon"):
        for cls in icon.attrib.get("class", "").split():
            if cls.startswith("icon-") and cls != "icon-void":
                names.append(ENERGY_ICONS.get(cls[5:], cls))
    return names


def card_text(node, *, hide_damage=False, hide_icons=False):
    """Keep inline pictograms instead of silently losing their meaning."""
    if node is None:
        return ""
    root = deepcopy(node.root)
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue  # Comments have no attributes and itertext already excludes their text.
        classes = element.get("class", "").split()
        icons = [cls[5:] for cls in classes if cls.startswith("icon-")]
        if (hide_damage and "f_right" in classes) or (hide_icons and icons):
            element.text = ""
            for child in list(element):
                element.remove(child)
        elif icons:
            element.text = "".join("{" + ENERGY_ICONS.get(icon, icon) + "}" for icon in icons)
        elif element.tag == "br":
            element.text = "\n"
    return " ".join("".join(root.itertext()).split())


def first_text(node, selector):
    return next((card_text(match) for match in node.css(selector)), "")


class PokemonJpSpider(scrapy.Spider):
    name = "pokemon_jp"
    # Unexpected callback errors must not silently drop a card and finish successfully.
    custom_settings = {"CLOSESPIDER_ERRORCOUNT": 1}

    def __init__(
        self, start_url=SEARCH_URL, max_pages="0", max_cards="0", start_page="1", **kwargs
    ):
        super().__init__(**kwargs)
        for name, value, minimum in (
            ("max_pages", max_pages, 0),
            ("max_cards", max_cards, 0),
            ("start_page", start_page, 1),
        ):
            try:
                number = int(str(value))
                if number < minimum:
                    raise ValueError
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be an integer >= {minimum}") from exc
            setattr(self, name, number)
        url = urlsplit(start_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            raise ValueError("start_url must be an absolute HTTP(S) URL without credentials")
        self.base_url = urlunsplit((url.scheme, url.netloc, "", "", ""))
        self.filters = [
            (key, value)
            for key, value in parse_qsl(url.query, keep_blank_values=True)
            if key != "page"
        ]
        self.allowed_domains = [url.hostname]
        # Scrapy's SpiderState extension saves/restores this dictionary with JOBDIR.
        self.state = {}

    @property
    def scheduled_ids(self):
        return self.state.setdefault("scheduled_ids", set())

    def page_request(self, page_number):
        query = urlencode([*self.filters, ("page", page_number)])
        return scrapy.Request(
            f"{self.base_url}/card-search/resultAPI.php?{query}",
            callback=self.parse,
            errback=self.on_request_error,
            cb_kwargs={"page_number": page_number},
            priority=-10,
        )

    async def start(self):
        yield self.page_request(self.start_page)

    def parse(self, response, page_number):
        try:
            data = response.json()
            page, last, total = int(data["thisPage"]), int(data["maxPage"]), int(data["hitCnt"])
            cards, regulation = data["cardList"], str(data["regulation"])
            if (
                data["result"] != 1
                or page != page_number
                or total < 0
                or not isinstance(cards, list)
                or not re.fullmatch(r"[\w-]+", regulation)
            ):
                raise ValueError
            if not cards and total == 0 and page == 1 and last in {0, 1}:
                self.logger.info("No cards match the search.")
                return
            if last < page or not cards:
                raise ValueError
            ids = [str(card["cardID"]) for card in cards]
            if any(not re.fullmatch(r"[0-9]+", card_id) for card_id in ids):
                raise ValueError
            known_ids = self.scheduled_ids
            all_ids = known_ids | set(ids)
            pages = self.state.get("pages_seen", set()) | {page}
            if (
                not set(ids) - known_ids
                or len(set(ids)) != len(ids)
                or len(all_ids) > total
                or self.state.get("expected_total", total) != total
            ):
                raise ValueError
            if "cardStart" in data or "cardEnd" in data:
                start, end = int(data["cardStart"]), int(data["cardEnd"])
                if (
                    not 1 <= start <= end <= total
                    or end - start + 1 != len(cards)
                    or (page == 1 and start != 1)
                    or ("last_end" in self.state and start != self.state["last_end"] + 1)
                ):
                    raise ValueError
            if (
                page == last
                and self.start_page == 1
                and not self.max_cards
                and (pages != set(range(1, last + 1)) or len(all_ids) != total)
            ):
                raise ValueError
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            self.logger.error("Invalid catalogue response at %s", response.url)
            raise CloseSpider("invalid_catalogue") from exc

        self.state["pages_seen"] = pages
        self.state["expected_total"] = total
        if "cardEnd" in data:
            self.state["last_end"] = int(data["cardEnd"])
        self.logger.info("Catalogue page %s/%s (%s results)", page, last, total)
        for card_id in ids:
            if card_id in self.scheduled_ids:
                continue
            if self.max_cards and len(self.scheduled_ids) >= self.max_cards:
                return
            self.scheduled_ids.add(card_id)
            yield scrapy.Request(
                f"{self.base_url}/card-search/details.php/card/{card_id}/regu/{regulation}",
                callback=self.parse_detail,
                errback=self.on_request_error,
                cb_kwargs={"card_id": card_id},
                priority=10,
            )
        pages_read = page - self.start_page + 1
        if (
            page < last
            and (not self.max_pages or pages_read < self.max_pages)
            and (not self.max_cards or len(self.scheduled_ids) < self.max_cards)
        ):
            yield self.page_request(page + 1)

    def parse_detail(self, response, card_id):
        sections = response.css("section.Section")
        if not sections:
            raise CloseSpider("invalid_card_detail")
        section = sections[0]
        name = first_text(section, "h1")
        image = section.css(".LeftBox img.fit::attr(src)").get()
        right = section.css(".RightBox-inner")
        if not name or not image or not right:
            raise CloseSpider("invalid_card_detail")
        item = ItemPokemon(
            card_id=f"pokemon-card.com:{card_id}",
            name=name,
            language="ja",
            region="JP",
            external_ids={"pokemon-card.com": card_id},
            source_name="pokemon-card.com",
            source_url=response.url,
            scraped_at=datetime.now(UTC).isoformat(),
            images={"front": response.urljoin(image)},
        )
        artists = [card_text(link) for link in section.css(".author a") if card_text(link)]
        if artists:
            item["illustrators"] = list(dict.fromkeys(artists))
        self.parse_printing(response, section, item)
        self.parse_pokemon(section, item)
        self.parse_blocks(right[0], item)
        # The evolution widget links searches; it is not text printed on the card.
        raw_parts = [
            name,
            first_text(section, ".subtext"),
            first_text(section, ".LeftBox .card"),
            first_text(section, ".TopInfo"),
        ]
        raw_parts.extend(block["text"] for block in item.get("text_blocks", []))
        raw_parts.extend(card_text(table) for table in right.css("table"))
        item["raw_text"] = "\n".join(part for part in raw_parts if part)
        return item

    def parse_printing(self, response, section, item):
        set_data = {}
        logo = section.css(".subtext img.img-regulation")
        if logo:
            # This image identifies the set (MG, XY-P...), not the printed regulation mark.
            if logo.attrib.get("alt"):
                set_data["code"] = logo.attrib["alt"]
            if logo.attrib.get("src"):
                set_data["symbol_url"] = response.urljoin(logo.attrib["src"])
        number = first_text(section, ".subtext")
        if number:
            number = re.sub(r"\s*/\s*", "/", number)
            item["printed_number"] = number
            item["number"] = number.split("/", 1)[0]
            if "/" in number and number.split("/", 1)[1].isdigit():
                set_data["printed_total"] = int(number.split("/", 1)[1])
        related_links = [
            {"name": card_text(link), "url": response.urljoin(link.attrib["href"])}
            for link in response.css(".SubSection a.Link[href]")
        ]
        # This can be a product, promotion or prize: it does not name the set reliably.
        if related_links:
            item["additional_attributes"] = {"related_links": related_links}
        if set_data:
            item["set"] = set_data

    def parse_pokemon(self, section, item):
        hp = first_text(section, ".hp-num")
        if hp:
            item["supertype"] = "Pokémon"
            item["hp"] = hp
        stage = first_text(section, ".TopInfo .type")
        if stage:
            item["stage"] = stage
        top = section.css(".TopInfo")
        if top and (types := icon_names(top[0])):
            item["types"] = types
        for row in section.css(".RightBox-inner table tr"):
            cells = row.css("td")
            if len(cells) != 3:
                continue
            for field, cell in zip(("weaknesses", "resistances"), cells[:2], strict=True):
                item[field] = [
                    {"type": type_name, "value": card_text(cell, hide_icons=True)}
                    for type_name in icon_names(cell)
                ]
            item["retreat_cost"] = icon_names(cells[2])
            item["converted_retreat_cost"] = len(item["retreat_cost"])
        dex = first_text(section, ".LeftBox .card h4")
        match = re.search(r"No\.\s*(\d+)\s*(.*)", dex)
        if match:
            item["pokemon"] = [{"national_pokedex_number": int(match[1])}]
            if match[2]:
                item["species"] = match[2]
        paragraphs = section.css(".LeftBox .card p")
        if paragraphs:
            match = re.search(r"高さ[：:]\s*(.*?)\s*重さ[：:]\s*(.*)", card_text(paragraphs[0]))
            if match:
                item["height"], item["weight"] = match.groups()
            if len(paragraphs) > 1:
                item["flavor_text"] = card_text(paragraphs[-1])

    def parse_blocks(self, right, item):
        heading = ""
        current = None
        blocks, trainer_text, energy_text = [], [], []
        for node in right.xpath("./h2 | ./h3 | ./h4 | ./p"):
            tag, text = node.root.tag, card_text(node)
            if tag == "h2":
                heading, current = text, None
                if heading == "進化":
                    continue
                if heading in TRAINER_HEADINGS:
                    item["supertype"], item["trainer_type"] = "Trainer", heading
                elif heading in {"基本エネルギー", "特殊エネルギー", "エネルギー"}:
                    item["supertype"], item["energy_type"] = "Energy", heading
            if not text or heading == "進化":
                continue
            blocks.append({"kind": tag, "title": heading, "text": text, "position": len(blocks)})
            if tag in {"h3", "h4"}:
                if heading == "ワザ":
                    current = {
                        "name": card_text(node, hide_damage=True, hide_icons=True),
                        "cost": icon_names(node),
                    }
                    current["converted_energy_cost"] = len(current["cost"])
                    damage = first_text(node, ".f_right")
                    if damage:
                        current["damage"] = damage
                    field = "attacks"
                else:
                    current = {"name": text, "kind": heading}
                    field = (
                        "abilities"
                        if heading in ABILITY_HEADINGS
                        else "ancient_traits"
                        if heading == "古代能力"
                        else "effects"
                    )
                item.setdefault(field, []).append(current)
            elif tag == "p":
                if heading == "特別なルール":
                    item.setdefault("rules", []).append(text)
                elif heading in TRAINER_HEADINGS:
                    trainer_text.append(text)
                elif heading in {"基本エネルギー", "特殊エネルギー", "エネルギー"}:
                    energy_text.append(text)
                elif current is not None:
                    current["text"] = "\n".join(filter(None, [current.get("text"), text]))
                else:
                    item.setdefault("effects", []).append({"kind": heading, "text": text})
        if blocks:
            item["text_blocks"] = blocks
        if trainer_text:
            item["trainer_text"] = "\n".join(trainer_text)
        if energy_text:
            item["energy_text"] = "\n".join(energy_text)

    def on_request_error(self, failure):
        if str(failure.value).startswith("blocked_"):
            return
        self.logger.error("Request failed: %s", failure.getErrorMessage())
        raise CloseSpider("request_failed")
