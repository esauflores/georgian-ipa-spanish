"""Tests for search, storage and the API."""

import pytest
from fastapi.testclient import TestClient

from dictionary.dictionary import Dictionary, Entry
from dictionary.storage import JsonStore
from main import create_app


@pytest.fixture
def coffee():
    return Entry("ყავა", "café", "qʼɑvɑ", "k’a-va")


def test_search_georgian(coffee):
    assert list(Dictionary([coffee]).search("ყა")) == [coffee]


def test_search_ignores_accents_case_and_padding(coffee):
    assert list(Dictionary([coffee]).search(" CAFE ")) == [coffee]


def test_search_preserves_enye():
    year = Entry("წელი", "año", "t͡sʼɛli", "ts’e-li")
    assert not list(Dictionary([year]).search("ano"))


@pytest.mark.parametrize("query", ["", "   ", "leche"])
def test_search_without_matches(coffee, query):
    assert not list(Dictionary([coffee]).search(query))


def test_entry_requires_all_fields():
    with pytest.raises(ValueError):
        Entry("ყავა", "café", " ", "k’a-va")


def test_json_round_trip(tmp_path, coffee):
    store = JsonStore(tmp_path / "entries.json")
    store.save([coffee])
    assert store.load() == [coffee]


def test_api_loads_starter_entries(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    response = client.get("/entries")
    assert response.status_code == 200
    assert len(response.json()) == 59
    assert all(entry["english"] and entry["english_pronunciation"] for entry in response.json())


def test_api_searches_in_spanish(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    response = client.get("/entries", params={"q": "cuanto"})
    assert response.status_code == 200
    assert response.json()[0]["georgian"] == "ეს რა ღირს?"


@pytest.mark.parametrize("contents", ["{", "{}", "[null]", '[{"ipa": 1}]'])
def test_broken_file_reports_error(tmp_path, contents):
    path = tmp_path / "entries.json"
    path.write_text(contents, encoding="utf-8")
    response = TestClient(create_app(path)).get("/entries")
    assert response.status_code == 500
    assert path.read_text(encoding="utf-8") == contents


def test_api_saves_and_reloads_a_new_entry(tmp_path):
    path = tmp_path / "entries.json"
    client = TestClient(create_app(path))
    entry = {
        "georgian": "რძე",
        "spanish": "Leche",
        "ipa": "rd͡zɛ",
        "pronunciation": "rdze",
    }
    assert client.post("/entries", json=entry).status_code == 201
    restarted = TestClient(create_app(path))
    assert restarted.get("/entries", params={"q": "leche"}).json() == [
        {**entry, "tags": [], "english": None, "english_pronunciation": None}
    ]


def test_api_rejects_missing_fields(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    assert client.post("/entries", json={"spanish": "Hola"}).status_code == 422


def test_api_combines_text_and_tag_filters(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    assert len(client.get("/entries", params={"tag": "curse"}).json()) == 17
    assert len(client.get("/entries", params={"tag": "numbers"}).json()) == 11
    matches = client.get("/entries", params={"q": "idiota", "tag": "curse"}).json()
    assert {entry["georgian"] for entry in matches} == {"ყლე", "ყლეო"}
    assert "curse" in client.get("/tags").json()


def test_api_saves_normalized_tags(tmp_path):
    path = tmp_path / "entries.json"
    entry = {
        "georgian": "რძე",
        "spanish": "Leche",
        "ipa": "rd͡zɛ",
        "pronunciation": "rdze",
        "tags": [" FOOD ", "food"],
    }
    assert TestClient(create_app(path)).post("/entries", json=entry).status_code == 201
    entries = TestClient(create_app(path)).get("/entries", params={"tag": "food"})
    assert {item["spanish"]: item["tags"] for item in entries.json()}["Leche"] == ["food"]


def test_homepage_lists_phrases_and_escapes_new_entries(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    entry = {
        "georgian": "რძე",
        "spanish": "<Leche>",
        "ipa": "rd͡zɛ",
        "pronunciation": "rdze",
    }
    assert client.post("/entries", json=entry).status_code == 201
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text.count("<li>") == 60
    assert "გამარჯობა" in response.text
    assert "&lt;Leche&gt;" in response.text
    assert "<Leche>" not in response.text


def test_homepage_combines_search_with_category(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    response = client.get("/", params={"q": "uno", "tag": "numbers"})
    assert response.status_code == 200
    assert "1 entrada" in response.text
    assert response.text.count("<li>") == 1
    assert "ერთი" in response.text
    assert 'aria-current="true">Números' in response.text
    assert client.get("/static/dictionary.css").status_code == 200


def test_homepage_shows_empty_state(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    response = client.get("/", params={"q": "sin coincidencias"})
    assert response.status_code == 200
    assert "No se encontraron entradas." in response.text


@pytest.mark.parametrize(
    "lang, query, meaning, guide, other_meaning, other_guide",
    [
        ("en", "zero", "Zero (0)", "noo-lee", "Cero (0)", "nu-li"),
        ("es", "cero", "Cero (0)", "nu-li", "Zero (0)", "noo-lee"),
    ],
)
def test_homepage_uses_selected_language(tmp_path, lang, query, meaning, guide, other_meaning, other_guide):
    client = TestClient(create_app(tmp_path / "entries.json"))
    response = client.get("/", params={"q": query, "tag": "numbers", "lang": lang})
    assert response.status_code == 200
    assert f'<html lang="{lang}">' in response.text
    assert response.text.count("<li>") == 1
    assert f'lang="{lang}">{meaning}</p>' in response.text
    assert f'aria-label="{guide}"' in response.text
    assert other_meaning not in response.text
    assert f'aria-label="{other_guide}"' not in response.text

    other_query = "cero" if lang == "en" else "zero"
    mismatched = client.get("/", params={"q": other_query, "tag": "numbers", "lang": lang})
    assert "<li>" not in mismatched.text
    assert client.get("/entries", params={"q": query}).json()[0]["georgian"] == "ნული"


def test_homepage_offers_audio_only_for_available_clips(tmp_path, monkeypatch):
    from dictionary import page
    from dictionary.audio import clip_name

    monkeypatch.setattr(page, "AUDIO_DIR", tmp_path)
    filename = clip_name("გამარჯობა")
    (tmp_path / filename).touch()

    client = TestClient(create_app(tmp_path / "entries.json"))
    english = client.get("/", params={"lang": "en"})
    spanish = client.get("/")
    assert english.text.count("data-audio=") == 1
    assert f'data-audio="/static/audio/{filename}"' in english.text
    assert ">Listen</button>" in english.text
    assert ">Escuchar</button>" in spanish.text
    assert client.get("/static/audio.js").status_code == 200


def test_shechema_has_searchable_bilingual_usage_guides(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    for lang, guide in (("es", "she-che-ma"), ("en", "sheh-cheh-mah")):
        response = client.get("/", params={"q": "შეჩემა", "lang": lang, "tag": "slang"})
        assert response.status_code == 200
        assert response.text.count("<article") == 1
        assert "vulgar" in response.text
        assert f'aria-label="{guide}"' in response.text


def test_strong_insults_replace_the_lighter_address_examples(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    assert client.get("/entries", params={"q": "სულელო"}).json() == []
    response = client.get("/", params={"q": "გააჯვი", "lang": "en", "tag": "curse"})
    assert response.status_code == 200
    assert response.text.count("<article") == 1
    assert "Fuck off! (very vulgar)" in response.text


def test_curse_category_excludes_soft_slang_and_includes_stronger_entries(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    curse = {row["georgian"] for row in client.get("/entries", params={"tag": "curse"}).json()}
    slang = {row["georgian"] for row in client.get("/entries", params={"tag": "slang"}).json()}
    soft = {"შეჩემა", "ცუღლუტო", "ჟმოტო", "წუწურაქო"}
    assert soft <= slang
    assert not soft & curse
    assert {"ყლეთაყლე", "შიგ ხომ არ გაქვს?"} <= curse
