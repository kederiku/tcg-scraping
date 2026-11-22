import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

import pytest
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse
from scrapy.spiderloader import SpiderLoader
from scrapy.utils.project import get_project_settings

CATALOGUE = "https://www.pokemon.com/fr/jcc-pokemon/cartes-pokemon"
SET = {"id": "sv01", "name": "Écarlate et Violet", "series": "Écarlate et Violet"}
INDEX = """
<form id="filters" action="/fr/jcc-pokemon/cartes-pokemon">
 <input type="checkbox" name="card-grass">
 <div id="filterExpansions"><fieldset><h2>Écarlate et Violet</h2><ul>
 <li><input name="sv01" id="sv01" type="checkbox"><label for="sv01">
 <span>Écarlate et Violet</span></label></li>
 <li><input name="svp" id="svp" type="checkbox"><label for="svp">
 <span>Promos</span></label></li></ul></fieldset></div></form>
"""


def spider(**options):
    loader = SpiderLoader.from_settings(get_project_settings())
    assert "pokemon_fr" in loader.list()
    return loader.load("pokemon_fr")(**options)


def page(url, body):
    return HtmlResponse(url, body=body.encode(), encoding="utf-8")


def detail(category, blocks, stats="", hp=""):
    return page(
        CATALOGUE + "/series/sv01/201/",
        f"""<section class="card-detail"><div class="card-image"><img src="/images/201.png">
        </div><div class="full-card-information" data-card-id="sv01/201">
        <div class="card-description"><h1>Carte <em>ex</em></h1><div class="card-basic-info">
        <div class="card-type"><h2>{category}</h2></div>{hp}</div></div>
        <div class="pokemon-abilities">{blocks}</div><div class="pokemon-stats">{stats}
        <div class="stats-footer"><h3>Écarlate et Violet</h3><span>201/198 Illustration Rare</span>
        </div></div><div class="illustrator"><h4>Illustrateur : <a>L. Test</a></h4></div>
        </div></section><section class="card-detail visible-mobile"></section>""",
    )


def test_filters_and_forward_pagination():
    crawler = spider()
    sets = list(crawler.parse(page(CATALOGUE, INDEX)))
    assert {req.url for req in sets} == {CATALOGUE + "?sv01=on", CATALOGUE + "?svp=on"}
    request = next(req for req in sets if "sv01=" in req.url)
    results = page(
        request.url + "&page=2",
        """<section class="card-results"><ul id="cardResults">
        <li><a href="/fr/jcc-pokemon/cartes-pokemon/series/sv01/201/">Carte</a></li>
        <li><a href="/fr/jcc-pokemon/cartes-pokemon/series/sv01/201/">Carte</a></li></ul>
        <div id="cards-load-more"><div><a href="?sv01=on&amp;page=1">Résultats précédents</a>
        <span>2 sur 3</span><a href="?sv01=on&amp;page=3"><span>Résultats suivants</span></a>
        </div></div></section><a href="/fr/actualites">Autre</a>""",
    )
    follows = list(request.callback(results, **request.cb_kwargs))
    assert {r.url for r in follows} == {
        CATALOGUE + "/series/sv01/201/",
        CATALOGUE + "?sv01=on&page=3",
    }
    assert len(follows) == 2
    assert [r.url for r in spider(extension="svp").parse(page(CATALOGUE, INDEX))] == [
        CATALOGUE + "?svp=on"
    ]


def test_pokemon_printing_gameplay_and_symbols():
    response = detail(
        "Pokémon de Niveau 1",
        """<div class="ability"><h3><div class="poke-ability">Talent</div>
        <div>Étincelle</div></h3><p>Ajoutez une Énergie
        <span class="energy-symbol Lightning" title="Électrique">Lightning</span>.</p></div>
        <div class="ability"><ul><li title="Feu"></li><li title="Feu"></li></ul>
        <h4 class="label">Flamme</h4><span class="plus">30×</span>
        <pre>Effet de l’attaque.</pre></div><div class="ability"><p>Règle spéciale.</p></div>""",
        """<div class="stat"><h4>Faiblesse</h4><ul><li title="Eau">×2</li></ul></div>
        <div class="stat"><h4>Coût de Retraite</h4><ul class="card-energies"></ul></div>""",
        '<span class="card-hp"><span>PV</span>120</span><i class="energy" title="Feu"></i>',
    )
    item = spider().parse_card(response, SET)
    assert item["language"] == "fr"
    assert item["name"] == "Carte ex"
    assert item["set"] == {**SET, "printed_total": 198}
    assert item["card_id"] == "pokemon.com:fr:sv01/201"
    assert (item["printed_number"], item["rarity"]) == ("201/198", "Illustration Rare")
    assert item["images"]["front"] == "https://www.pokemon.com/images/201.png"
    assert item["illustrators"] == ["L. Test"]
    assert (item["hp"], item["types"]) == ("120", ["Feu"])
    assert item["abilities"] == [
        {"kind": "Talent", "name": "Étincelle", "text": "Ajoutez une Énergie {Électrique}."}
    ]
    assert item["attacks"][0]["cost"] == ["Feu", "Feu"]
    assert item["attacks"][0]["damage"] == "30×"
    assert item["weaknesses"] == [{"type": "Eau", "value": "×2"}]
    assert item["converted_retreat_cost"] == 0
    assert item["rules"] == ["Règle spéciale."]


@pytest.mark.parametrize(
    ("category", "field"),
    [
        ("Dresseur - Objet", "trainer_text"),
        ("Dresseur - Outil Pokémon", "trainer_text"),
        ("Spéciale", "energy_text"),
    ],
)
def test_trainer_and_energy_text(category, field):
    response = detail(
        category, '<div class="ability"><pre><p>Première phrase.</p><p>Deuxième.</p></pre></div>'
    )
    item = spider().parse_card(response, SET)
    assert item[field].split() == ["Première", "phrase.", "Deuxième."]
    assert "hp" not in item and "attacks" not in item


def test_challenge_and_incomplete_result_are_visible():
    crawler = spider()
    with pytest.raises(CloseSpider) as blocked:
        list(crawler.parse(page(CATALOGUE, '<iframe src="/_Incapsula_Resource?x=1"></iframe>')))
    assert blocked.value.reason == "blocked_captcha"
    assert blocked.value.error
    with pytest.raises(CloseSpider):
        list(
            crawler.parse_results(page(CATALOGUE, '<section class="card-results"></section>'), SET)
        )


def test_sample_continues_after_an_empty_expansion_and_stops_at_exact_limit():
    crawler = spider(max_cards=1)
    (first,) = crawler.parse(page(CATALOGUE, INDEX))
    empty = page(first.url, '<section class="card-results">Aucune carte trouvée.</section>')
    (second,) = first.callback(empty, **first.cb_kwargs)
    listing = page(
        second.url,
        '<section class="card-results"><ul id="cardResults">'
        '<li><a href="/fr/jcc-pokemon/cartes-pokemon/series/svp/1/">1</a></li>'
        '<li><a href="/fr/jcc-pokemon/cartes-pokemon/series/svp/2/">2</a></li></ul></section>',
    )
    (one,) = second.callback(listing, **second.cb_kwargs)
    assert one.url == CATALOGUE + "/series/svp/1/"
    assert one.cb_kwargs["expansion"]["id"] == "svp"


def test_scrapy_exports_every_page_and_extension_once(tmp_path):
    route = urlsplit(CATALOGUE).path
    visited = []

    class Catalogue(BaseHTTPRequestHandler):
        def do_GET(self):
            visited.append(self.path)
            status = 200
            if self.path == "/robots.txt":
                content = "User-agent: *\nAllow: /"
            elif self.path == route:
                content = INDEX
            elif self.path.startswith(route + "?"):
                pages = {
                    "sv01=on": (
                        ["sv01/201"],
                        '<a href="?sv01=on&amp;page=2">Résultats suivants</a>',
                    ),
                    "sv01=on&page=2": (["sv01/201", "sv01/202"], ""),
                    "svp=on": (["svp/SVP001"], ""),
                }
                keys, forward = pages[self.path.split("?", 1)[1]]
                links = "".join(
                    f'<li><a href="{route}/series/{key}/">Carte</a></li>' for key in keys
                )
                content = (
                    f'<section class="card-results"><ul id="cardResults">{links}</ul>'
                    f'<div id="cards-load-more">{forward}</div></section>'
                )
            elif self.path.startswith(route + "/series/"):
                key = self.path.split("/series/")[1].strip("/")
                content = f"""
                    <div class="full-card-information" data-card-id="{key}">
                    <div class="card-description"><h1>Carte {key}</h1>
                    <div class="card-type"><h2>Spéciale</h2></div></div>
                    <div class="pokemon-abilities"><div class="ability">
                    <pre>Texte propre à {key}.</pre></div></div></div>"""
            else:
                status, content = 404, ""
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Catalogue)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    output = tmp_path / "cartes.jsonl"
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scrapy",
                "crawl",
                "pokemon_fr",
                "-a",
                f"start_url=http://127.0.0.1:{server.server_port}{route}",
                "-O",
                str(output),
                "-s",
                "DOWNLOAD_DELAY=0",
                "-s",
                "AUTOTHROTTLE_ENABLED=False",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            encoding="utf-8",
            timeout=60,
        )
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
    assert result.returncode == 0, result.stderr
    items = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert sorted(item["energy_text"] for item in items) == [
        "Texte propre à sv01/201.",
        "Texte propre à sv01/202.",
        "Texte propre à svp/SVP001.",
    ]
    assert set(item["set"]["id"] for item in items) == {"sv01", "svp"}
    assert visited.count(route + "/series/sv01/201/") == 1
