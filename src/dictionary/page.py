"""Render the dictionary as a server-side HTML page."""

from html import escape
from typing import Literal
from urllib.parse import urlencode

from .audio import AUDIO_DIR, clip_name
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
        "listen": "Escuchar",
        "boost": "Amplificar audio",
        "audio_error": "No se pudo reproducir el audio.",
        "entry": "entrada",
        "entries": "entradas",
        "empty": "No se encontraron entradas.",
        "reset": "Ver todas",
        "language": "Idioma de la interfaz",
    },
    "en": {
        "title": "Georgian dictionary",
        "search_label": "Search in Georgian or English",
        "placeholder": "e.g. thank you",
        "search": "Search",
        "categories": "Categories",
        "all": "All",
        "sound": "English pronunciation",
        "listen": "Listen",
        "boost": "Boost audio",
        "audio_error": "The audio could not be played.",
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


def render_audio_button(entry: Entry, lang: str) -> str:
    """Offer playback when the local WAV exists."""
    filename = clip_name(entry.georgian)
    if not (AUDIO_DIR / filename).is_file():
        return ""

    label = COPY[lang]["listen"]
    return (
        f'<button class="listen" type="button" data-audio="/static/audio/{filename}" '
        f'aria-label="{label}: {escape(entry.georgian)}" aria-pressed="false">{label}</button>'
    )


def render_pronunciation(label: str, pronunciation: str, lang: str) -> str:
    """Render a phonetic guide as syllable tiles."""
    words = []
    for word in pronunciation.split():
        syllables = (f'<span class="syllable">{escape(syllable)}</span>' for syllable in word.split("-") if syllable)
        words.append(f'<span class="word">{"".join(syllables)}</span>')

    return f"""
            <div>
              <dt>{label}</dt>
              <dd class="syllables" lang="{lang}" aria-label="{escape(pronunciation)}">
                <span class="words" aria-hidden="true">{" ".join(words)}</span>
              </dd>
            </div>
    """


def render_card(entry: Entry, show_tags: bool, lang: str) -> str:
    """Render an entry with its pronunciation and categories."""
    tags = "".join(f'<span class="tag">{escape(tag_label(tag, lang))}</span>' for tag in entry.tags if show_tags)
    tag_row = f'<div class="tags">{tags}</div>' if tags else ""

    meaning = entry.english if lang == "en" else entry.spanish
    pronunciation = entry.english_pronunciation if lang == "en" else entry.pronunciation
    meaning_markup = f'<p class="meaning" lang="{lang}">{escape(meaning)}</p>' if meaning else ""
    guide = render_pronunciation(COPY[lang]["sound"], pronunciation, lang) if pronunciation else ""

    return f"""
      <li>
        <article class="card">
          {tag_row}
          <div class="card-title">
            <div class="card-text">
              <h3 lang="ka">{escape(entry.georgian)}</h3>
              {meaning_markup}
            </div>
            {render_audio_button(entry, lang)}
          </div>
          <dl>
            {guide}
            <div>
              <dt>IPA</dt>
              <dd class="ipa">/{escape(entry.ipa)}/</dd>
            </div>
          </dl>
        </article>
      </li>
    """


def render_page(dictionary: Dictionary, query: str, selected_tag: str, lang: Literal["es", "en"]) -> str:
    """Render search controls and the matching entries."""
    copy = COPY[lang]
    entries = list(dictionary.search(query or None, selected_tag or None, lang=lang))

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

    cards = "".join(render_card(entry, show_tags=not selected_tag, lang=lang) for entry in entries)
    count_label = copy["entry"] if len(entries) == 1 else copy["entries"]
    result_text = f"{len(entries)} {count_label}"
    category_name = tag_label(selected_tag, lang) or copy["all"]
    results = (
        f'<ul class="cards">{cards}</ul>'
        if entries
        else (f'<p class="empty">{copy["empty"]} <a href="{escape(page_url(lang))}">{copy["reset"]}</a></p>')
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
  <script src="/static/audio.js" defer></script>
</head>
<body>
  <main>
    <header>
      <h1>{copy["title"]}</h1>
      <nav class="languages" aria-label="{copy["language"]}">{"".join(languages)}</nav>
    </header>

    <div class="lookup">
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

      <nav class="categories" aria-label="{copy["categories"]}">{"".join(filters)}</nav>
    </div>

    <section aria-labelledby="results-title">
      <div class="results-header">
        <h2 id="results-title">{escape(category_name)} <span>· {result_text}</span></h2>
        <button class="audio-boost" type="button" aria-pressed="false" hidden>{copy["boost"]}</button>
      </div>
      <p class="audio-status" role="status" data-error="{copy["audio_error"]}"></p>
      {results}
    </section>
  </main>
</body>
</html>"""
