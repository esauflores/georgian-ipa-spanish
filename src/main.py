"""Serve the Georgian–Spanish phrasebook with FastAPI."""

import os
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, StringConstraints

from dictionary.dictionary import Dictionary, Entry
from dictionary.page import render_page
from dictionary.storage import JsonStore

STARTER_DATA = Path(__file__).resolve().parents[1] / "data" / "starter.json"
STATIC_DIR = Path(__file__).resolve().parent / "static"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EntryInput(BaseModel):
    """Validate the submitted phrase and any tags."""

    georgian: Text
    spanish: Text
    ipa: Text
    pronunciation: Text
    tags: tuple[Text, ...] = ()
    english: Text | None = None
    english_pronunciation: Text | None = None


def create_app(path: Path = Path("entries.json"), *, read_only: bool = False) -> FastAPI:
    """Create an API backed by the given dictionary file."""
    api = FastAPI(title="Georgian–Spanish IPA Dictionary")
    api.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    store = JsonStore(path)
    write_lock = Lock()

    def load_dictionary() -> Dictionary:
        try:
            try:
                return Dictionary(store.load())
            except FileNotFoundError:
                return Dictionary(JsonStore(STARTER_DATA).load())
        except (OSError, ValueError, TypeError) as error:
            raise HTTPException(500, "No se pudo leer el diccionario.") from error

    @api.get("/", response_class=HTMLResponse)
    def index(
        q: Annotated[str, Query(max_length=200)] = "",
        tag: Annotated[str, Query(max_length=100)] = "",
        lang: Literal["es", "en"] = "es",
    ) -> str:
        """Display and filter the dictionary in a browser."""
        return render_page(load_dictionary(), q.strip(), tag.strip().lower(), lang)

    @api.get("/entries", response_model=list[Entry])
    def list_entries(
        q: Annotated[str | None, Query(max_length=200)] = None,
        tag: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    ):
        """Filter entries by Georgian text, translation, or tag."""
        return list(load_dictionary().search(q, tag))

    @api.get("/tags")
    def list_tags() -> list[str]:
        """List the available tags."""
        return load_dictionary().tags()

    def add_entry(data: EntryInput):
        """Add and save a phrase."""
        fields = data.model_dump()
        fields["ipa"] = fields["ipa"].strip("/").strip()

        try:
            entry = Entry(**fields)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

        try:
            with write_lock:
                dictionary = load_dictionary()
                store.save([*dictionary.entries, entry])
        except OSError as error:
            raise HTTPException(500, "No se pudo guardar el diccionario.") from error

        return entry

    if not read_only:
        api.add_api_route("/entries", add_entry, methods=["POST"], status_code=201, response_model=Entry)

    return api


app = create_app(read_only=os.environ.get("DICTIONARY_READ_ONLY") == "1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
