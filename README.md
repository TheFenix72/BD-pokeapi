# Pokémon CRUD con Flask, MongoDB Atlas y PokéAPI

Aplicación web CRUD para una práctica de MongoDB. Permite importar los 151 primeros Pokémon desde PokéAPI, guardarlos en MongoDB Atlas y gestionarlos desde una interfaz Flask con Jinja2.

## Tecnologías

- Python 3.12+
- Flask
- Jinja2
- MongoDB Atlas
- PyMongo
- Requests
- PokéAPI Pokemon Endpoint: `https://pokeapi.co/api/v2/pokemon`

## Estructura

```text
project/
├── app.py
├── import_pokemon.py
├── requirements.txt
├── .env.example
├── README.md
├── config.py
├── templates/
│   ├── index.html
│   ├── create.html
│   ├── edit.html
│   ├── stats.html
│   └── search.html
├── static/
│   └── style.css
└── services/
    ├── mongo_service.py
    └── pokemon_service.py
```

## Instalación

1. Crear un entorno virtual:

```bash
python -m venv .venv
```

2. Activar el entorno virtual:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Crear el archivo `.env` a partir de `.env.example`:

```bash
cp .env.example .env
```

En Windows también puedes copiarlo manualmente.

5. Configurar las variables:

```env
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=pokemon_db
SECRET_KEY=change-this-secret
```

## Importar Pokémon desde PokéAPI

Ejecuta:

```bash
python import_pokemon.py
```

El script:

- Consume `https://pokeapi.co/api/v2/pokemon`.
- Descarga 151 Pokémon.
- Obtiene el detalle individual de cada Pokémon usando su URL.
- Limpia y transforma los datos.
- Inserta los documentos en la colección `pokemon`.
- Crea índices para evitar duplicados y permitir búsqueda de texto.
- Traduce los tipos de PokéAPI al español, por ejemplo `water` se guarda como `agua`.

Cada documento contiene:

- Texto: `name`, `description`
- Número: `pokedex_number`, `height`, `weight`
- Booleano: `is_legendary`
- Array: `types`, `abilities`
- Documento incrustado: `stats`

## Ejecutar la aplicación

En Windows PowerShell, desde la carpeta del proyecto:

```powershell
cd "C:\Users\isard\Desktop\BD pokeapi"
.\.venv\Scripts\Activate.ps1
python app.py
```

Si PowerShell no deja activar el entorno virtual por permisos, puedes ejecutarla directamente sin activar:

```powershell
cd "C:\Users\isard\Desktop\BD pokeapi"
.\.venv\Scripts\python.exe app.py
```

Cuando aparezca el mensaje `Running on http://127.0.0.1:5000`, abre:

```text
http://127.0.0.1:5000
```

Para apagar la web, vuelve a la terminal donde está ejecutándose Flask y pulsa `Ctrl + C`.

También se puede ejecutar con Flask:

```bash
flask --app app run --debug
```

O con Python:

```bash
python app.py
```

Abre en el navegador:

```text
http://127.0.0.1:5000
```

## Funcionalidades CRUD

- Listado de Pokémon.
- Creación de Pokémon inventados.
- Edición de cualquier Pokémon.
- Imagen por URL o subiendo un archivo local desde el formulario.
- Sprite shiny por URL o subiendo archivo local.
- Megaevolución manual con nombre, sprite normal y sprite shiny.
- Localizaciones, debilidades y fortalezas editables en formularios.
- Altura y peso se introducen como enteros y se muestran con decimal automático: `10` se ve como `1,0 m` o `1,0 kg`.
- Modificación de arrays mediante campos separados por coma, por ejemplo `fire, flying`.
- Eliminación de Pokémon.
- Validación de formularios.
- Prevención de duplicados por `name` y `pokedex_number`.
- Vista individual de cada Pokémon con imagen, shiny, estadísticas, habilidades, preevoluciones, evoluciones y megaevoluciones si existen en PokéAPI.

## Consultas implementadas

En `/search` se incluyen:

- Texto completo sobre `description` con índice de texto MongoDB y `$text`.
- Ataque mayor que un valor con `$gt`.
- Ataque menor que un valor con `$lt`.
- Defensa mayor que un valor con `$gt`.
- Pokémon que tengan ciertos tipos con `$in`.
- Nombre por patrón con `$regex`.
- Altura menor que un valor con `$lt`.
- Altura mayor que un valor con `$gt`.
- Pokémon con campo `image` usando `$exists`.
- Cantidad exacta de tipos con `$size`.

Los filtros pueden combinarse en la misma busqueda, por ejemplo:

```text
/search?types=agua&max_height=10&min_defense=40
```

## Actualizar datos ya importados

Si ya habías importado Pokémon antes de añadir traducciones, ejecuta:

```bash
python update_spanish_data.py
```

Este script convierte los tipos guardados en inglés a español y regenera las descripciones en español.
También completa estadísticas extendidas, sprite shiny, línea evolutiva y megaevoluciones para documentos ya importados.

## Estadísticas

En `/stats` se usa Aggregation Framework:

- Promedio de ataque por tipo con `$unwind`, `$group`, `$avg` y `$sort`.
- Cantidad de Pokémon por tipo con `$unwind`, `$group`, `$sum` y `$sort`.

## Operaciones MongoDB usadas

El proyecto usa explícitamente:

- `insert_one`
- `insert_many`
- `find`
- `update_one`
- `delete_one`
- `aggregate`

## Notas

- No subas el archivo `.env` a repositorios públicos.
- MongoDB Atlas debe permitir la IP desde la que ejecutes la aplicación.
- Si cambias índices únicos en una colección con datos duplicados, MongoDB puede rechazar la creación del índice hasta limpiar esos duplicados.
