# Georgian–Spanish IPA Dictionary

Diccionario de expresiones georgianas para hispanohablantes de América Latina.
Cada entrada incluye la escritura georgiana, el significado en español, la
transcripción en el Alfabeto Fonético Internacional (AFI/IPA) y una guía
aproximada dividida en sílabas.

## Ejecutar

Instala `uv` en Windows, macOS o Linux y abre una terminal en la carpeta
del proyecto. `uv` prepara el entorno con Python 3.12.

```sh
uv sync --locked
uv run python src/main.py
```

Abre [el diccionario](http://127.0.0.1:8000/) para ver todas las entradas.
Para buscar o agregar expresiones, abre [la interfaz interactiva de FastAPI](http://127.0.0.1:8000/docs).
En `GET /entries`, elige **Try it out**. Ejecuta sin una consulta para ver
las 36 entradas de `data/starter.json` o escribe `cuanto`, `cafe` o `მადლობა` en el campo `q`.
La búsqueda admite fragmentos, ignora mayúsculas y permite omitir las tildes.

Usa `GET /tags` para ver las etiquetas y el campo `tag` en
`GET /entries` para filtrar por `numbers`, `slang` o `curse`. Puedes
combinar `q` y `tag`. La etiqueta `curse` identifica expresiones vulgares.

En `POST /entries` puedes agregar una expresión con etiquetas opcionales. La API guarda los cambios
en `entries.json` en la carpeta actual y los carga al reiniciar.

## Clases

- `Entry` es una dataclass con los cuatro campos de una expresión.
- `Dictionary` contiene las entradas y usa un generador para la búsqueda.
- `JsonStore` carga y guarda entradas como JSON con `pathlib`.

## Pronunciación

Los guiones separan sílabas. `sh` representa /ʃ/, `dy` aproxima /d͡ʒ/,
`j` aproxima /x/, `gh` representa /ɣ/ y el apóstrofo marca las consonantes
eyectivas. La `v` se pronuncia con el labio inferior contra los dientes
superiores. Las guías son aproximadas.

Referencias

[Peace Corps Georgian lessons](https://files.peacecorps.gov/multimedia/audio/languagelessons/georgia/GE_Georgian_Language_Lessons.pdf)
y [Standard Georgian, de Shosted y Chikovani](https://linguistics.berkeley.edu/phonlab/documents/2006/shosted_chikovani_11-23.pdf).

## Pruebas

```sh
uv run python -m pytest
uv run ruff check .
```
