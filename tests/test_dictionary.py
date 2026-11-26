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
    assert len(response.json()) == 36


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
        {**entry, "tags": []}
    ]


def test_api_rejects_missing_fields(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    assert client.post("/entries", json={"spanish": "Hola"}).status_code == 422


def test_api_combines_text_and_tag_filters(tmp_path):
    client = TestClient(create_app(tmp_path / "entries.json"))
    assert len(client.get("/entries", params={"tag": "curse"}).json()) == 3
    assert len(client.get("/entries", params={"tag": "numbers"}).json()) == 10
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
    assert {item["spanish"]: item["tags"] for item in entries.json()}["Leche"] == [
        "food"
    ]


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
    assert response.text.count("<li>") == 37
    assert "გამარჯობა" in response.text
    assert "&lt;Leche&gt;" in response.text
    assert "<Leche>" not in response.text
