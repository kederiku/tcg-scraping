"""Lecture d'une fiche de l'encyclopédie du JCC Pokémon en français."""

import re
from datetime import UTC, datetime

from scrapy.exceptions import CloseSpider

from tcg_scraper.item_pokemon import ItemPokemon


def fragments(element):
    if not isinstance(element.tag, str):
        return
    if "energy-symbol" in element.get("class", "").split() and element.get("title"):
        yield "{" + element.get("title") + "}"
        return
    if element.tag in {"br", "p", "div", "h3", "h4", "li", "ul", "pre"}:
        yield " "
    yield element.text or ""
    for child in element:
        yield from fragments(child)
        yield child.tail or ""


def text_of(nodes):
    if not nodes:
        return ""
    root = nodes.root if hasattr(nodes, "root") else nodes[0].root
    return " ".join("".join(fragments(root)).split())


def card_item(response, expansion):
    card = response.css(".full-card-information[data-card-id]")
    key = card.attrib.get("data-card-id", "")
    name = text_of(card.css(".card-description h1"))
    category = text_of(card.css(".card-type h2"))
    if not name or not category or "/" not in key:
        raise CloseSpider("invalid_card_detail", error=True)
    item = ItemPokemon(
        card_id=f"pokemon.com:fr:{key}",
        external_ids={"pokemon.com": key},
        language="fr",
        region="FR",
        name=name,
        source_name="pokemon.com",
        source_url=response.url,
        scraped_at=datetime.now(UTC).isoformat(),
        raw_text=text_of(card),
    )
    image = response.css(".card-detail .card-image img::attr(src)").get()
    if image:
        item["images"] = {"front": response.urljoin(image)}
    artists = [text_of(a) for a in card.css(".illustrator a")]
    if artists:
        item["illustrators"] = artists
    printing(card, response, item, expansion, key)

    hp = re.sub(r"^PV\s*", "", text_of(card.css(".card-hp")))
    if hp or category.startswith("Pokémon"):
        item["supertype"] = "Pokémon"
        item["stage"] = category
        if hp:
            item["hp"] = hp
        types = card.css(".card-basic-info i.energy::attr(title)").getall()
        if types:
            item["types"] = types
        if ancestor := text_of(card.css(".card-type h4 a")):
            item["evolves_from"] = ancestor
            item["evolution_text"] = text_of(card.css(".card-type h4"))
        dex = response.css("#pokedex-find::attr(data-pokemon-number)").get()
        if dex and dex.isdecimal():
            item["pokemon"] = [{"national_pokedex_number": int(dex)}]
    elif category.startswith("Énergie") or category in {"De base", "Spéciale"}:
        item["supertype"] = "Energy"
        item["energy_type"] = category
    elif category.startswith("Dresseur") or category in {
        "Objet",
        "Stade",
        "Supporter",
        "Outil Pokémon",
        "Machine Technique",
        "Machine secrète des Rocket",
    }:
        item["supertype"] = "Trainer"
        item["trainer_type"] = category
    else:
        item["additional_attributes"] = {"card_type": category}
    gameplay(card, item)
    for link in response.css(".slider .card-name").xpath("parent::a[@href]"):
        related = item.setdefault("additional_attributes", {}).setdefault("related_cards", [])
        related.append(
            {
                "name": text_of(link.css("h5")),
                "number": text_of(link.css(".card-number")),
                "url": response.urljoin(link.attrib["href"]),
            }
        )
    return item


def printing(card, response, item, expansion, key):
    set_data = {k: v for k, v in expansion.items() if v}
    set_data["id"], item["number"] = key.rsplit("/", 1)
    if title := text_of(card.css(".stats-footer h3")):
        set_data["name"] = title
    symbol = card.css(".expansion i::attr(style)").get("")
    if match := re.search(r"url\(['\"]?([^)'\"]+)", symbol):
        set_data["symbol_url"] = response.urljoin(match[1])
    footer = text_of(card.css(".stats-footer span"))
    if footer:
        number, _, rarity = re.sub(r"\s*/\s*", "/", footer).partition(" ")
        item["printed_number"] = number
        numerator, _, denominator = number.partition("/")
        item["number"] = numerator
        if denominator.isdecimal():
            set_data["printed_total"] = int(denominator)
        if rarity:
            item["rarity"] = rarity
    item["set"] = set_data


def gameplay(card, item):
    for stat in card.css(".pokemon-stats .stat"):
        label = text_of(stat.css("h4"))
        energies = stat.css("li[title]")
        if label in {"Faiblesse", "Résistance"}:
            field = "weaknesses" if label == "Faiblesse" else "resistances"
            item[field] = [
                {"type": energy.attrib["title"], "value": text_of(energy)} for energy in energies
            ]
        elif "retraite" in label.lower() and stat.css("ul"):
            cost = [e.attrib["title"] for e in energies if not e.css(".icon-free")]
            item["retreat_cost"], item["converted_retreat_cost"] = cost, len(cost)
    texts = []
    for block in card.css(".pokemon-abilities .ability"):
        body = "\n".join(filter(None, (text_of(p) for p in block.xpath("./pre | ./p"))))
        if body:
            texts.append(body)
        title = text_of(block.css("h4.label"))
        if heading := block.css("h3"):
            kind = text_of(heading.css(".poke-ability"))
            name = text_of(heading.css("div:not(.poke-ability)")) or text_of(heading)
            field = "ancient_traits" if "antique" in kind.lower() else "abilities"
            item.setdefault(field, []).append(
                {k: v for k, v in {"kind": kind, "name": name, "text": body}.items() if v}
            )
        elif title:
            attack = {"name": title}
            if block.css("ul"):
                cost = [
                    li.attrib["title"] for li in block.css("li[title]") if not li.css(".icon-free")
                ]
                attack.update(cost=cost, converted_energy_cost=len(cost))
            if damage := text_of(block.css(".plus")):
                attack["damage"] = damage
            if body:
                attack["text"] = body
            item.setdefault("attacks", []).append(attack)
        elif body and item.get("supertype") == "Pokémon":
            item.setdefault("rules", []).append(body)
    if texts and item.get("supertype") in {"Trainer", "Energy"}:
        field = "trainer_text" if item["supertype"] == "Trainer" else "energy_text"
        item[field] = "\n".join(texts)
