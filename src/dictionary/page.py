"""Render the dictionary as a server-side HTML page."""

from html import escape
from urllib.parse import urlencode

from .dictionary import Dictionary, Entry

COPY = {
    "es": {
        "title": "Diccionario georgiano",
        "search_label": "Buscar en georgiano o español",
        "placeholder": "Ej. gracias",
        "search": "Buscar",
        "categories": "Categorías",
        "all": "Todas",
        "sound": "Cómo suena",
        "entry": "entrada",
        "entries": "entradas",
        "empty": "No se encontraron entradas.",
        "reset": "Ver todas",
        "language": "Idioma de la interfaz",
    },
    "en": {
        "title": "Georgian dictionary",
        "search_label": "Search in Georgian or Spanish",
        "placeholder": "e.g. gracias",
        "search": "Search",
        "categories": "Categories",
        "all": "All",
        "sound": "Spanish pronunciation",
        "entry": "entry",
        "entries": "entries",
        "empty": "No entries found.",
        "reset": "View all",
        "language": "Interface language",
    },
}

TAG_LABELS = {
    "basics": ("Básicos", "Basics"),
    "communication": ("Comunicación", "Communication"),
    "curse": ("Groserías", "Swear words"),
    "directions": ("Direcciones", "Directions"),
    "food": ("Comida", "Food"),
    "greetings": ("Saludos", "Greetings"),
    "introductions": ("Presentaciones", "Introductions"),
    "numbers": ("Números", "Numbers"),
    "shopping": ("Compras", "Shopping"),
    "slang": ("Coloquial", "Slang"),
}


def tag_label(tag: str, lang: str) -> str:
    """Translate a category label while allowing custom tags."""
    return TAG_LABELS.get(tag, (tag, tag))[lang == "en"]


def page_url(lang: str, query: str = "", tag: str = "") -> str:
    """Build a page link preserving the active controls."""
    params = urlencode(
        {
            key: value
            for key, value in {
                "lang": lang if lang != "es" else "",
                "q": query,
                "tag": tag,
            }.items()
            if value
        }
    )
    return f"/?{params}" if params else "/"


def render_card(entry: Entry, show_tags: bool, lang: str) -> str:
    """Render an entry with its pronunciation and categories."""
    tags = "".join(
        f'<span class="tag">{escape(tag_label(tag, lang))}</span>'
        for tag in entry.tags
        if show_tags
    )
    tag_row = f'<div class="tags">{tags}</div>' if tags else ""
    words = []
    for word in entry.pronunciation.split():
        tiles = "".join(
            f'<span class="syllable">{escape(syllable)}</span>'
            for syllable in word.split("-")
            if syllable
        )
        words.append(f'<span class="word">{tiles}</span>')
    return f"""
      <li>
        <article class="card">
          {tag_row}
          <h3 lang="ka">{escape(entry.georgian)}</h3>
          <p class="meaning" lang="es">{escape(entry.spanish)}</p>
          <dl>
            <div><dt>{COPY[lang]["sound"]}</dt><dd class="syllables" lang="es" aria-label="{escape(entry.pronunciation)}">
              <span class="words" aria-hidden="true">{" ".join(words)}</span>
            </dd></div>
            <div><dt>IPA</dt><dd class="ipa">/{escape(entry.ipa)}/</dd></div>
          </dl>
        </article>
      </li>
    """


def render_page(
    dictionary: Dictionary, query: str, selected_tag: str, lang: str
) -> str:
    """Render search controls and the matching entries."""
    copy = COPY[lang]
    entries = list(dictionary.search(query or None, selected_tag or None))
    tags = dictionary.tags()
    categories = [
        "",
        *(tag for tag in ("greetings", "basics", "numbers") if tag in tags),
    ]
    categories.extend(tag for tag in tags if tag not in categories)
    filters = []
    for tag in categories:
        selected = ' aria-current="true"' if tag == selected_tag else ""
        label = tag_label(tag, lang) if tag else copy["all"]
        url = page_url(lang, query, tag)
        filters.append(f'<a href="{escape(url)}"{selected}>{escape(label)}</a>')
    cards = "".join(
        render_card(entry, show_tags=not selected_tag, lang=lang) for entry in entries
    )
    count_label = copy["entry"] if len(entries) == 1 else copy["entries"]
    result_text = f"{len(entries)} {count_label}"
    category_name = tag_label(selected_tag, lang) or copy["all"]
    results = (
        f'<ul class="cards">{cards}</ul>'
        if entries
        else (
            f'<p class="empty">{copy["empty"]} '
            f'<a href="{escape(page_url(lang))}">{copy["reset"]}</a></p>'
        )
    )
    languages = []
    for code, name in (("es", "Español"), ("en", "English")):
        current = ' aria-current="true"' if code == lang else ""
        url = escape(page_url(code, query, selected_tag))
        languages.append(f'<a href="{url}" lang="{code}"{current}>{name}</a>')
    return f"""<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{copy["title"]}</title>
  <link rel="stylesheet" href="/static/dictionary.css">
</head>
<body>
  <main>
    <header>
      <h1>{copy["title"]}</h1>
      <nav class="languages" aria-label="{copy["language"]}">{"".join(languages)}</nav>
    </header>
    <form action="/" method="get" role="search">
      <label for="query">{copy["search_label"]}</label>
      <div class="search">
        <input id="query" name="q" type="search" value="{escape(query)}"
               placeholder="{copy["placeholder"]}" maxlength="200">
        <input type="hidden" name="tag" value="{escape(selected_tag)}">
        <input type="hidden" name="lang" value="{lang}">
        <button type="submit">{copy["search"]}</button>
      </div>
    </form>
    <nav aria-label="{copy["categories"]}">{"".join(filters)}</nav>
    <section aria-labelledby="results-title">
      <h2 id="results-title">{escape(category_name)} <span>· {result_text}</span></h2>
      {results}
    </section>
  </main>
</body>
</html>"""
