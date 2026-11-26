"""Serve the Georgian–Spanish phrasebook with FastAPI."""

from html import escape
from pathlib import Path
from threading import Lock
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, StringConstraints

from dictionary.dictionary import Dictionary, Entry
from dictionary.storage import JsonStore

STARTER_DATA = Path(__file__).resolve().parents[1] / "data" / "starter.json"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EntryInput(BaseModel):
    """Validate the submitted phrase and any tags."""

    georgian: Text
    spanish: Text
    ipa: Text
    pronunciation: Text
    tags: tuple[Text, ...] = ()


def create_app(path: Path = Path("entries.json")) -> FastAPI:
    """Create an API backed by the given dictionary file."""
    api = FastAPI(title="Georgian–Spanish IPA Dictionary")
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
    def index() -> str:
        """Display the dictionary as a plain HTML list."""
        items = []
        for entry in load_dictionary().entries:
            tags = f" ({escape(', '.join(entry.tags))})" if entry.tags else ""
            items.append(
                f'<li><strong lang="ka">{escape(entry.georgian)}</strong>'
                f" — {escape(entry.spanish)} — /{escape(entry.ipa)}/"
                f" — {escape(entry.pronunciation)}{tags}</li>"
            )
        return (
            '<!doctype html><html lang="es"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>Diccionario georgiano–español</title></head><body>"
            "<main><h1>Diccionario georgiano–español</h1>"
            "<ul>" + "\n".join(items) + "</ul></main></body></html>"
        )

    @api.get("/entries", response_model=list[Entry])
    def list_entries(
        q: Annotated[str | None, Query(max_length=200)] = None,
        tag: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    ):
        """Filter entries by Georgian text, Spanish meaning, or tag."""
        return list(load_dictionary().search(q, tag))

    @api.get("/tags")
    def list_tags() -> list[str]:
        """List the available tags."""
        return load_dictionary().tags()

    @api.post("/entries", status_code=201, response_model=Entry)
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

    return api


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
