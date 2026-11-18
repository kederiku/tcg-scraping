"""Korean official catalogue: search, load-more batches and card details."""

import re
from copy import deepcopy
from datetime import UTC, datetime
from urllib.parse import parse_qs, unquote, urlencode, urlsplit, urlunsplit

import scrapy
from scrapy.exceptions import CloseSpider

from tcg_scraper.item_pokemon import ItemPokemon

ENERGY_TYPES = {
    "1": "Grass",
    "2": "Fire",
    "3": "Water",
    "4": "Lightning",
    "5": "Psychic",
    "6": "Fighting",
    "7": "Darkness",
    "8": "Metal",
    "9": "Colorless",
    "10": "Dragon",
    "11": "Fairy",
}
TRAINER_TYPES = {"아이템", "포켓몬의 도구", "서포트", "서포터", "스타디움", "트레이너스"}
ABILITY_LABELS = {"특성", "포켓파워", "포켓바디"}


def image_stem(src):
    url = urlsplit(src)
    path = parse_qs(url.query).get("key", [url.path])[0]
    return unquote(path).rsplit("/", 1)[-1].rsplit(".", 1)[0]


def energy_name(element):
    match = re.fullmatch(r"type(\d+)", image_stem(element.get("src", "")))
    return ENERGY_TYPES.get(match[1], f"type{match[1]}") if match else None


def energy_symbols(node):
    return [name for image in node.css("img") if (name := energy_name(image.root))]


def text_of(node):
    """Preserve inline pictograms, but exclude duplicate accessibility captions/comments."""
    root = deepcopy(node.root)
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        if "small_type_sm" in element.get("class", "").split():
            element.text = ""
            for child in list(element):
                element.remove(child)
        elif element.tag == "img":
            label = energy_name(element) or element.get("alt") or element.get("title")
            if not label:
                label = image_stem(element.get("src", ""))
            element.text = "{" + label + "}" if label else ""
        elif element.tag == "br":
            element.text = "\n"
    return " ".join("".join(root.itertext()).split())


def first_text(node, selector):
    return next((text_of(match) for match in node.css(selector)), "")


class PokemonKrSpider(scrapy.Spider):
    name = "pokemon_kr"
    custom_settings = {"CLOSESPIDER_ERRORCOUNT": 1}

    def __init__(
        self,
        start_url="https://pokemoncard.co.kr/cards",
        max_pages="0",
        max_cards="0",
        start_page="1",
        search_text=None,
        search_params="all",
        **kwargs,
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
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{name} must be an integer >= {minimum}") from exc
            setattr(self, name, number)
        url = urlsplit(start_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            raise ValueError("start_url must be an absolute HTTP(S) URL without credentials")
        if search_params not in {"all", "cardname", "cardtext"}:
            raise ValueError("search_params must be all, cardname or cardtext")
        self.base_url = urlunsplit((url.scheme, url.netloc, "", "", ""))
        self.allowed_domains = [url.hostname]
        self.search_text = (
            search_text if search_text is not None else parse_qs(url.query).get("s", [""])[0]
        )
        self.search_params = search_params
        self.state = {}  # Scrapy's SpiderState persists this dictionary with JOBDIR.

    @property
    def scheduled_ids(self):
        return self.state.setdefault("scheduled_ids", set())

    def page_request(self, cursor):
        return scrapy.Request(
            self.base_url + "/v2/ajax2_dev2",
            method="POST",
            body=urlencode(
                {
                    "action": "search_text_cards",
                    "search_text": self.search_text,
                    "search_params": self.search_params,
                    "limit": cursor,
                }
            ),
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": self.base_url + "/cards",
            },
            callback=self.parse,
            errback=self.on_request_error,
            cb_kwargs={"cursor": cursor},
            priority=-10,
        )

    async def start(self):
        yield self.page_request(self.start_page - 1)

    def parse(self, response, cursor):
        try:
            data = response.json()
            cards = data["result"]
            if isinstance(cards, dict):
                # Nonempty results are indexed from 1. Only an empty array is the
                # observed terminal response; an error object must not end a crawl.
                if not cards or set(cards) != {str(i) for i in range(1, len(cards) + 1)}:
                    raise ValueError
                cards = list(cards.values())
            if not isinstance(cards, list) or data["status"] is not True:
                raise ValueError
            count, next_cursor = int(str(data["count"])), int(str(data["limit"]))
            if count != len(cards) or next_cursor != cursor + 1:
                raise ValueError
            ids = [card["CardNum"] for card in cards]
            if any(
                not isinstance(card_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", card_id)
                for card_id in ids
            ):
                raise ValueError
            if len(ids) != len(set(ids)) or (ids and not set(ids) - self.scheduled_ids):
                raise ValueError
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            self.logger.error(
                "Invalid catalogue response at batch %s: %s", cursor + 1, response.url
            )
            raise CloseSpider("invalid_catalogue") from exc
        if not count:
            self.logger.info("End of search at batch %s (zero results).", cursor + 1)
            return
        self.logger.info("Catalogue batch %s: %s cards", cursor + 1, count)
        for card_id in ids:
            if card_id in self.scheduled_ids:
                continue
            if self.max_cards and len(self.scheduled_ids) >= self.max_cards:
                return
            self.scheduled_ids.add(card_id)
            yield scrapy.Request(
                self.base_url + "/cards/detail/" + card_id,
                callback=self.parse_detail,
                errback=self.on_request_error,
                cb_kwargs={"card_id": card_id},
                priority=10,
            )
        pages_read = cursor - self.start_page + 2
        if (not self.max_pages or pages_read < self.max_pages) and (
            not self.max_cards or len(self.scheduled_ids) < self.max_cards
        ):
            yield self.page_request(next_cursor)

    def parse_detail(self, response, card_id):
        main = response.css("#heaer_top")
        if not main:
            raise CloseSpider("invalid_card_detail")
        main = main[0]
        name = first_text(main, ".header .title")
        image = main.css("img.feature_image::attr(src)").get()
        category = first_text(main, ".pokemon-info")
        if not name or not image or not category:
            raise CloseSpider("invalid_card_detail")
        category = re.sub(r"^카드 종류\s*:\s*", "", category)
        item = ItemPokemon(
            card_id=f"pokemoncard.co.kr:{card_id}",
            name=name,
            language="ko",
            region="KR",
            external_ids={"pokemoncard.co.kr": card_id},
            source_name="pokemoncard.co.kr",
            source_url=response.url,
            scraped_at=datetime.now(UTC).isoformat(),
            images={"front": response.urljoin(image)},
        )
        artists = [" ".join(value.split()) for value in main.css(".illustrator ::text").getall()]
        artists = [value for value in artists if value and value != "일러스트"]
        if artists:
            item["illustrators"] = list(dict.fromkeys(artists))
        self.parse_printing(main, response, item)
        hp = first_text(main, ".hp_num")
        kinds = [value.strip() for value in category.split("|") if value.strip()]
        if not kinds:
            raise CloseSpider("invalid_card_detail")
        if len(kinds) > 1:
            item["subtypes"] = kinds[1:]
        if hp:
            item["supertype"] = "Pokémon"
            item["hp"] = re.sub(r"^HP\s*", "", hp)
            item["stage"] = kinds[0].removesuffix(" 포켓몬")
        elif "에너지" in kinds[0]:
            item["supertype"], item["energy_type"] = "Energy", kinds[0]
        elif kinds[0] in TRAINER_TYPES:
            item["supertype"], item["trainer_type"] = "Trainer", kinds[0]
        else:
            item.setdefault("additional_attributes", {})["card_type"] = category
        level = first_text(main, ".header .level")
        if level:
            item["level"] = level
        header = main.css(".header")
        if header and (types := energy_symbols(header[0])):
            item["types"] = types
        self.parse_stats(main, item)
        self.parse_blocks(main, item)
        flavor = [text_of(p) for p in main.css(".colsit > p") if text_of(p)]
        if flavor:
            item["flavor_text"] = "\n".join(flavor)
        links = [
            {"name": text_of(link), "url": response.urljoin(link.attrib["href"])}
            for link in main.css(".pokemon-detail a.search_href[href]")
        ]
        if links:
            item.setdefault("additional_attributes", {})["related_links"] = links
        raw = [name, category, item.get("printed_number", ""), hp, level]
        for block in item.get("text_blocks", []):
            raw.extend([block.get("title", ""), block["text"]])
        raw.extend(text_of(stat) for stat in main.css(".pokemon-stats .stat"))
        raw.extend(text_of(profile) for profile in main.css(".pokemon-detail .col-xs-5"))
        raw.append(item.get("flavor_text", ""))
        item["raw_text"] = "\n".join(part for part in raw if part)
        return item

    def parse_printing(self, main, response, item):
        number = " ".join(" ".join(main.css(".p_num::text").getall()).split())
        set_data = {}
        if number:
            number = re.sub(r"\s*/\s*", "/", number)
            item["printed_number"], item["number"] = number, number.split("/", 1)[0]
            if "/" in number and number.split("/", 1)[1].isdigit():
                set_data["printed_total"] = int(number.split("/", 1)[1])
        symbols = main.css(".pre_info_wrap > img::attr(src)").getall()
        if symbols:
            set_data["symbol_url"] = response.urljoin(symbols[0])
            code = image_stem(symbols[0])
            if code.lower() == "promo":
                code = number.split("/", 1)[1] if "/" in number else ""
            if code:
                set_data["code"] = code
        # On this site the second symbol is the regulation mark, distinct from the set logo.
        if len(symbols) > 1 and re.fullmatch(r"[A-Z]", image_stem(symbols[1])):
            item["regulation_mark"] = image_stem(symbols[1])
        rarity = first_text(main, ".p_num #no_wrap_by_admin")
        if rarity:
            item["rarity"] = rarity
        if set_data:
            item["set"] = set_data

    def parse_stats(self, main, item):
        for stat in main.css(".pokemon-stats .stat"):
            label = first_text(stat, "h4")
            symbols = energy_symbols(stat)
            if label in {"약점", "저항력"}:
                field = "weaknesses" if label == "약점" else "resistances"
                value = " ".join(text_of(span) for span in stat.css("span"))
                item[field] = [{"type": symbol, "value": value} for symbol in symbols]
            elif label == "후퇴":
                item["retreat_cost"] = symbols
                if all(symbol in ENERGY_TYPES.values() for symbol in symbols):
                    item["converted_retreat_cost"] = len(symbols)
        for dimensions in main.css(".pokemon-detail .col-xs-5"):
            profile = text_of(dimensions)
            match = re.search(r"키\s*:\s*(.*?)\s*몸무게\s*:\s*(.*)", profile)
            if match:
                item["height"], item["weight"] = match.groups()
            visible = re.search(r"No\.\s*(\d+)\s*(.*?)(?=키\s*:|$)", profile)
            if visible:
                item["pokemon"] = [{"national_pokedex_number": int(visible[1])}]
                if species := visible[2].strip():
                    item["species"] = species
                continue
            # The template retains the Pokédex number in a dedicated HTML comment.
            for comment in dimensions.xpath("./comment()").getall():
                match = re.fullmatch(r"<!--\s*No\.\s*(\d+)\s*-->", comment)
                if match:
                    item["pokemon"] = [{"national_pokedex_number": int(match[1])}]

    def parse_blocks(self, main, item):
        texts = []
        for node in main.css(".pokemon-abilities > .ability"):
            label = first_text(node, "#skill_label")
            name = first_text(node, ".skil_name")
            heading = name or first_text(node, "h4")
            body = "\n".join(text_of(p) for p in node.css("p") if text_of(p))
            kind = "effect"
            if heading.endswith("룰"):
                if body:
                    item.setdefault("rules", []).append(body)
                kind = "rule"
            elif label:
                field = (
                    "abilities"
                    if label in ABILITY_LABELS
                    else "ancient_traits"
                    if label == "고대능력"
                    else "effects"
                )
                item.setdefault(field, []).append({"kind": label, "name": name, "text": body})
                kind = field
            elif name and item.get("supertype") == "Pokémon" and node.css(".area-parent"):
                cost = energy_symbols(node.css(".area-parent")[0])
                attack = {"name": name, "cost": cost}
                if all(symbol in ENERGY_TYPES.values() for symbol in cost):
                    attack["converted_energy_cost"] = len(cost)
                if damage := first_text(node, ".plus"):
                    attack["damage"] = damage
                if body:
                    attack["text"] = body
                item.setdefault("attacks", []).append(attack)
                kind = "attack"
            elif item.get("supertype") not in {"Trainer", "Energy"} and (heading or body):
                item.setdefault("effects", []).append(
                    {"kind": label, "name": heading, "text": body}
                )
            if body:
                texts.append(body)
            if heading or body:
                blocks = item.setdefault("text_blocks", [])
                blocks.append(
                    {"kind": kind, "title": heading, "text": body, "position": len(blocks)}
                )
        if texts and item.get("supertype") in {"Trainer", "Energy"}:
            field = "trainer_text" if item["supertype"] == "Trainer" else "energy_text"
            item[field] = "\n".join(texts)

    def on_request_error(self, failure):
        if str(failure.value).startswith("blocked_"):
            return
        self.logger.error("Request failed: %s", failure.getErrorMessage())
        raise CloseSpider("request_failed")
