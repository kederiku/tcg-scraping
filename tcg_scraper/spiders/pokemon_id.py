"""Indonesian TCG Collector cards, discovered through its permitted public sitemaps."""

import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from urllib.parse import urlsplit

import scrapy
from lxml import etree
from scrapy.exceptions import CloseSpider

from tcg_scraper.item_pokemon import ItemPokemon

SITEMAP_PATH = re.compile(r"/sitemaps/sitemap-cards-id([1-9]\d*)\.xml")
CARD_PATH = re.compile(r"/cards/([1-9]\d*)/[^/?#]+")
TRAINER_TYPES = {"Trainer", "Item", "Supporter", "Stadium", "Pokémon Tool", "Technical Machine"}
ABILITY_TYPES = {"Ability", "Pokémon Power", "Poké-Power", "Poké-Body"}
MISSING = {"", "—", "–", "-"}


def text_of(node):
    root = deepcopy(node.root)
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        if element.tag == "img" and "energy-type-symbol" in element.get("class", "").split():
            label = element.get("alt") or element.get("title")
            element.text = "{" + label + "}" if label else ""
        elif element.tag == "br":
            element.text = "\n"
    return " ".join("".join(root.itertext()).split())


def first_text(node, selector):
    return next((text_of(match) for match in node.css(selector)), "")


def energies(node):
    return [
        name
        for image in node.css("img.energy-type-symbol")
        if (name := image.attrib.get("alt") or image.attrib.get("title")) and name != "No Energy"
    ]


def attack_cost(block):
    container = block.css(".card-attack-energies")
    if container:
        images = container.css("img")
        # An unreadable symbol or an unusual textual cost is unknown, not free.
        if (
            len(images) != len(container.css("img.energy-type-symbol"))
            or any(not (image.attrib.get("alt") or image.attrib.get("title")) for image in images)
            or container.css("svg")
            or "".join(container.xpath(".//text()").getall()).strip()
        ):
            return None
        return energies(container)
    # Observed on Alolan Rattata 79650: the normal attack header is present,
    # but a zero-cost attack has no energy container at all.
    if first_text(block, ".card-attack-header .card-attack-header-text .card-attack-name"):
        return []
    return None


def app_state(response):
    """Decode only the public JSON payload; never evaluate the page's scripts."""
    for script in response.css("script::text").getall():
        match = re.search(r"\bappState\s*:\s*(\{)", script)
        if match:
            return json.JSONDecoder().raw_decode(script[match.start(1) :])[0]
    raise ValueError("Missing public card state")


def origin(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Expected an absolute HTTP(S) URL without credentials")
    return parsed.scheme, parsed.netloc


def sitemap_locations(response, expected):
    try:
        root = etree.fromstring(
            response.body, parser=etree.XMLParser(resolve_entities=False, no_network=True)
        )
        if etree.QName(root).localname != expected:
            raise ValueError("Unexpected sitemap root")
        child = "sitemap" if expected == "sitemapindex" else "url"
        entries = root.xpath(f'./*[local-name()="{child}"]')
        urls = []
        for entry in entries:
            locs = entry.xpath('./*[local-name()="loc"]/text()')
            if len(locs) != 1 or not locs[0].strip():
                raise ValueError("Missing sitemap location")
            urls.append(locs[0].strip())
        if not urls:
            raise ValueError("Empty sitemap")
        return urls
    except (etree.XMLSyntaxError, ValueError, TypeError) as exc:
        raise CloseSpider("invalid_catalogue") from exc


class PokemonIdSpider(scrapy.Spider):
    name = "pokemon_id"
    custom_settings = {"CLOSESPIDER_ERRORCOUNT": 1}

    def __init__(
        self,
        start_url="https://static.tcgcollector.com/sitemaps/sitemap.xml",
        card_base_url="https://www.tcgcollector.com",
        max_cards="0",
        max_sitemaps="0",
        max_pages=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if max_pages is not None:
            raise ValueError("pokemon_id uses max_cards / max_sitemaps, not max_pages")
        for name, value in (("max_cards", max_cards), ("max_sitemaps", max_sitemaps)):
            try:
                number = int(str(value))
                if number < 0:
                    raise ValueError
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{name} must be an integer >= 0") from exc
            setattr(self, name, number)
        self.sitemap_origin = origin(start_url)
        self.card_origin = origin(card_base_url)
        if urlsplit(start_url).query or urlsplit(start_url).fragment:
            raise ValueError("start_url must point to a sitemap index without query or fragment")
        self.start_url = start_url
        self.allowed_domains = list(
            {urlsplit(start_url).hostname, urlsplit(card_base_url).hostname}
        )
        self.state = {}  # Persisted by Scrapy's SpiderState when JOBDIR is enabled.

    @property
    def scheduled_ids(self):
        return self.state.setdefault("scheduled_ids", set())

    async def start(self):
        yield scrapy.Request(
            self.start_url, callback=self.parse_index, errback=self.on_request_error
        )

    def parse_index(self, response):
        maps = set()
        for url in sitemap_locations(response, "sitemapindex"):
            parsed = urlsplit(url)
            if (
                (parsed.scheme, parsed.netloc) == self.sitemap_origin
                and not parsed.query
                and not parsed.fragment
                and SITEMAP_PATH.fullmatch(parsed.path)
            ):
                maps.add(url)
        if not maps:
            raise CloseSpider("invalid_catalogue")
        ordered = sorted(maps, key=lambda url: int(SITEMAP_PATH.fullmatch(urlsplit(url).path)[1]))
        if self.max_sitemaps:
            ordered = ordered[: self.max_sitemaps]
        self.logger.info("Discovered %s Indonesian card sitemaps", len(ordered))
        yield self.sitemap_request(ordered)

    def sitemap_request(self, urls):
        return scrapy.Request(
            urls[0],
            callback=self.parse_sitemap,
            errback=self.on_request_error,
            cb_kwargs={"remaining": urls[1:]},
            priority=-10,
        )

    def parse_sitemap(self, response, remaining):
        cards = []
        # Validate the whole file before scheduling any request from it.
        for url in sitemap_locations(response, "urlset"):
            parsed = urlsplit(url)
            match = CARD_PATH.fullmatch(parsed.path)
            if (
                (parsed.scheme, parsed.netloc) != self.card_origin
                or parsed.query
                or parsed.fragment
                or not match
            ):
                raise CloseSpider("invalid_catalogue")
            cards.append((match[1], url))
        self.logger.info("Sitemap %s: %s card links", response.url, len(cards))
        for card_id, url in cards:
            if card_id in self.scheduled_ids:
                continue
            if self.max_cards and len(self.scheduled_ids) >= self.max_cards:
                return
            self.scheduled_ids.add(card_id)
            yield scrapy.Request(
                url,
                callback=self.parse_detail,
                errback=self.on_request_error,
                cb_kwargs={"card_id": card_id},
                priority=10,
            )
        if remaining and (not self.max_cards or len(self.scheduled_ids) < self.max_cards):
            yield self.sitemap_request(remaining)

    def parse_detail(self, response, card_id):
        try:
            state = app_state(response)
            region_id = next(
                region["id"] for region in state["tcgRegionDtos"] if region["slug"] == "id"
            )
            if state["cardIdToTcgRegionIdMap"][card_id] != region_id:
                raise ValueError("Not an Indonesian card")
            main = response.css("#card-info")[0]
            name = first_text(main, "#card-info-title")
            categories = [text_of(node).rstrip(", ") for node in main.css(".card-type-container")]
            if not name or not categories or not all(categories):
                raise ValueError("Missing card identity")
        except (ValueError, TypeError, KeyError, IndexError, StopIteration, AttributeError) as exc:
            self.logger.error("Invalid Indonesian card detail: %s", response.url)
            raise CloseSpider("invalid_card_detail") from exc
        item = ItemPokemon(
            card_id=f"tcgcollector.com:{card_id}",
            name=name,
            language="id",
            region="ID",
            external_ids={"tcgcollector.com": card_id},
            source_name="tcgcollector.com",
            source_url=response.url,
            scraped_at=datetime.now(UTC).isoformat(),
            raw_text=text_of(main),
            additional_attributes={},
        )
        attributes = item["additional_attributes"]
        if lang := response.css("html::attr(lang)").get():
            attributes["text_language"] = lang
        image = response.css("#card-image-container > img")
        src = image.css("::attr(src)").get() if image else None
        if src and "default-card-image" not in urlsplit(src).path:
            item["images"] = {"front": response.urljoin(src)}
            sizes = []
            for candidate in image.attrib.get("srcset", "").split(","):
                match = re.fullmatch(r"\s*(\S+)\s+(\d+)w\s*", candidate)
                if match and "default-card-image" not in urlsplit(match[1]).path:
                    sizes.append((int(match[2]), response.urljoin(match[1])))
            if sizes:
                item["images"]["large"] = max(sizes)[1]
        else:
            attributes["image_status"] = "missing"
        variants = []
        for variant_id in state.get("cardIdToCardVariantTypeIdsMap", {}).get(card_id, []):
            variant = state.get("idToCardVariantTypeDtoMap", {}).get(str(variant_id), {})
            if variant.get("name"):
                variants.append({"id": str(variant_id), "name": variant["name"]})
        if variants:
            attributes["available_variants"] = variants

        trainer = next((label for label in categories if label in TRAINER_TYPES), None)
        energy = next(
            (
                label
                for label in categories
                if label in {"Energy", "Basic Energy", "Special Energy"}
            ),
            None,
        )
        if trainer:
            item.update(supertype="Trainer", trainer_type=trainer)
        elif energy:
            item.update(supertype="Energy", energy_type=energy)
        else:
            item["supertype"] = (
                "Pokémon" if any("Pokémon" in label for label in categories) else categories[0]
            )
        subtypes = [label for label in categories if label != item["supertype"]]
        for label, selector in (
            ("hp", "#card-hit-points-value"),
            ("stage", '#card-evolution-status a[href*="pokemonStages="]'),
            ("evolves_from", '#card-evolution-status a[href*="nameSearch="]'),
            ("evolution_text", "#card-evolution-status"),
        ):
            if value := first_text(main, selector):
                item[label] = value
        if types := energies(main.css("#card-energy-types")):
            item["types"] = types
        self.parse_footer(response, main, item, subtypes)
        if subtypes:
            item["subtypes"] = list(dict.fromkeys(subtypes))
        self.parse_body(main, item)
        return item

    def parse_footer(self, response, main, item, subtypes):
        for field in main.css(".card-info-footer-item"):
            label = first_text(field, ".card-info-footer-item-title")
            value = first_text(field, ".card-info-footer-item-text")
            if label == "Expansion":
                expansion = {}
                for key, selector in (
                    ("name", "#card-info-footer-item-text-expansion-name"),
                    ("code", "#card-info-footer-item-text-expansion-code"),
                ):
                    if text := first_text(field, selector):
                        expansion[key] = text
                href = field.css('a[href^="/sets/"]::attr(href)').get("")
                if match := re.match(r"/sets/(\d+)/", href):
                    expansion["id"] = match[1]
                if symbol := field.css("img.set-symbol::attr(src)").get():
                    expansion["symbol_url"] = response.urljoin(symbol)
                if expansion:
                    item["set"] = expansion
            elif label == "Card number" and value not in MISSING:
                item["printed_number"] = value
                item["number"] = value.split("/", 1)[0]
                if "/" in value and value.split("/", 1)[1].isdigit():
                    item.setdefault("set", {})["printed_total"] = int(value.split("/", 1)[1])
            elif label in {"Rarity", "Regulation mark"} and value not in MISSING:
                item["rarity" if label == "Rarity" else "regulation_mark"] = value
            elif label == "Illustrators":
                artists = [text_of(node) for node in field.css("a") if text_of(node) not in MISSING]
                if artists:
                    item["illustrators"] = list(dict.fromkeys(artists))
            elif label in {"Weakness", "Resistance"}:
                entries = []
                for entry in field.css(".card-info-footer-item-entry"):
                    for energy in energies(entry):
                        pair = {"type": energy}
                        if modifier := first_text(entry, ".card-info-footer-item-entry-text"):
                            pair["value"] = modifier
                        entries.append(pair)
                if entries or value == "—":
                    item["weaknesses" if label == "Weakness" else "resistances"] = entries
            elif label == "Retreat Cost" and field.css(".card-info-footer-item-entries"):
                item["retreat_cost"] = energies(field)
                item["converted_retreat_cost"] = len(item["retreat_cost"])
            elif label == "Pokédex":
                numbers = [
                    int(match[1])
                    for a in field.css('a[href^="/pokedex/"]')
                    if (match := re.fullmatch(r"#(\d+)", text_of(a)))
                ]
                if numbers:
                    item["pokemon"] = [{"national_pokedex_number": number} for number in numbers]
            elif label == "Additional card types":
                subtypes.extend(text_of(a) for a in field.css("a") if text_of(a))
            elif label == "Provides" and (types := energies(field)):
                item["provided_energy"] = [{"types": types}]

    def parse_body(self, main, item):
        blocks = []
        for block in main.css("#card-description, .card-effect, .card-attack, .card-rule"):
            classes = block.attrib.get("class", "").split()
            if "card-attack" in classes:
                entry = {"name": first_text(block, ".card-attack-name")}
                if (cost := attack_cost(block)) is not None:
                    entry["cost"] = cost
                    entry["converted_energy_cost"] = len(cost)
                elif cost_text := first_text(block, ".card-attack-energies"):
                    entry["cost_text"] = cost_text
                for key, selector in (
                    ("damage", ".card-attack-damage"),
                    ("text", ".card-attack-description"),
                ):
                    if value := first_text(block, selector):
                        entry[key] = value
                item.setdefault("attacks", []).append(entry)
                blocks.append(
                    {
                        "kind": "attack",
                        "title": entry["name"],
                        "text": entry.get("text", ""),
                        "position": len(blocks),
                    }
                )
            elif "card-effect" in classes:
                entry = {}
                for key, selector in (
                    ("kind", ".card-effect-badge"),
                    ("name", ".card-effect-name"),
                    ("text", ".card-effect-description"),
                ):
                    if value := first_text(block, selector):
                        entry[key] = value
                kind = entry.get("kind")
                field = (
                    "abilities"
                    if kind in ABILITY_TYPES
                    else "ancient_traits"
                    if kind == "Ancient Trait"
                    else "effects"
                )
                item.setdefault(field, []).append(entry)
                blocks.append(
                    {
                        "kind": "effect",
                        "title": entry.get("name", ""),
                        "text": entry.get("text", ""),
                        "position": len(blocks),
                    }
                )
            elif "card-rule" in classes:
                if value := first_text(block, ".card-rule-description"):
                    item.setdefault("rules", []).append(value)
                    blocks.append(
                        {
                            "kind": "rule",
                            "title": first_text(block, ".card-rule-badge"),
                            "text": value,
                            "position": len(blocks),
                        }
                    )
            elif value := text_of(block):
                blocks.append(
                    {"kind": "description", "title": "", "text": value, "position": len(blocks)}
                )
        if blocks:
            item["text_blocks"] = blocks
        if item["supertype"] in {"Trainer", "Energy"}:
            text = "\n".join(block["text"] for block in blocks if block.get("text"))
            if text:
                item["trainer_text" if item["supertype"] == "Trainer" else "energy_text"] = text

    def on_request_error(self, failure):
        if str(failure.value).startswith("blocked_"):
            return
        self.logger.error("Request failed: %s (%s)", failure.request.url, failure.value)
        raise CloseSpider("request_failed")
