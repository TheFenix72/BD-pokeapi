import requests

from config import Config
from services.translations import REVERSE_TYPE_TRANSLATIONS, describe_types, translate_type


def fetch_first_generation(limit=151):
    """Descarga la primera generacion desde el endpoint obligatorio de PokeAPI."""
    response = requests.get(Config.POKEAPI_URL, params={"limit": limit}, timeout=20)
    response.raise_for_status()
    return response.json().get("results", [])


def fetch_pokemon_detail(url):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def fetch_species_detail(url):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def fetch_evolution_chain(url):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def fetch_type_detail(type_name):
    response = requests.get(f"https://pokeapi.co/api/v2/type/{type_name}/", timeout=20)
    response.raise_for_status()
    return response.json()


def fetch_location_area_encounters(url):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def extract_pokedex_description(species_data):
    """Obtiene una descripcion oficial de Pokedex, preferiblemente en espanol."""
    entries = species_data.get("flavor_text_entries", [])
    preferred_languages = ("es", "en")

    for language in preferred_languages:
        for entry in entries:
            if entry.get("language", {}).get("name") == language:
                return clean_flavor_text(entry.get("flavor_text", ""))

    return ""


def clean_flavor_text(text):
    return " ".join(text.replace("\n", " ").replace("\f", " ").split())


def extract_stats(api_data):
    stats_by_name = {
        item["stat"]["name"]: item["base_stat"] for item in api_data.get("stats", [])
    }

    return {
        "hp": stats_by_name.get("hp", 0),
        "attack": stats_by_name.get("attack", 0),
        "defense": stats_by_name.get("defense", 0),
        "special_attack": stats_by_name.get("special-attack", 0),
        "special_defense": stats_by_name.get("special-defense", 0),
        "speed": stats_by_name.get("speed", 0),
    }


def extract_evolution_names(chain_data):
    names, _ = extract_evolution_data(chain_data)
    return names


def extract_evolution_data(chain_data):
    names = []
    methods = {}

    def walk(node, parent_name=None):
        species_name = node.get("species", {}).get("name")
        if species_name:
            names.append(species_name)
            if parent_name:
                methods[species_name] = format_evolution_method(
                    node.get("evolution_details", [])
                )
        for child in node.get("evolves_to", []):
            walk(child, species_name)

    walk(chain_data.get("chain", {}))
    return names, methods


def format_evolution_method(evolution_details):
    if not evolution_details:
        return "Pokemon base"

    detail = evolution_details[0]
    trigger = detail.get("trigger", {}).get("name", "")
    level = detail.get("min_level")
    item = (detail.get("item") or {}).get("name")
    held_item = (detail.get("held_item") or {}).get("name")
    known_move = (detail.get("known_move") or {}).get("name")
    happiness = detail.get("min_happiness")
    time_of_day = detail.get("time_of_day")

    parts = []
    if trigger == "level-up":
        parts.append(f"Nivel {level}" if level else "Subiendo de nivel")
    elif trigger == "use-item":
        parts.append(f"Usando {item}" if item else "Usando un objeto")
    elif trigger == "trade":
        parts.append("Intercambio")
    else:
        parts.append(trigger.replace("-", " ") if trigger else "Metodo especial")

    if held_item:
        parts.append(f"con {held_item}")
    if known_move:
        parts.append(f"con movimiento {known_move}")
    if happiness:
        parts.append(f"amistad {happiness}")
    if time_of_day:
        parts.append(f"durante {time_of_day}")

    return ", ".join(parts)


def build_evolution_details(evolution_line, evolution_methods=None):
    evolution_methods = evolution_methods or {}
    details = []
    for name in evolution_line:
        try:
            pokemon_data = fetch_pokemon_detail(f"https://pokeapi.co/api/v2/pokemon/{name}/")
        except requests.RequestException:
            details.append({"name": name, "image": ""})
            continue

        sprites = pokemon_data.get("sprites", {})
        official_artwork = (
            sprites.get("other", {})
            .get("official-artwork", {})
            .get("front_default", "")
        )
        details.append(
            {
                "name": name,
                "image": official_artwork or sprites.get("front_default", ""),
                "method": evolution_methods.get(name, "Pokemon base"),
            }
        )
    return details


def split_evolutions(current_name, evolution_line):
    if current_name not in evolution_line:
        return [], evolution_line

    current_index = evolution_line.index(current_name)
    return evolution_line[:current_index], evolution_line[current_index + 1 :]


def extract_mega_evolutions(api_data):
    mega_evolutions = []
    for variety in api_data.get("varieties", []):
        name = variety.get("pokemon", {}).get("name", "")
        if "mega" in name:
            try:
                pokemon_data = fetch_pokemon_detail(variety["pokemon"]["url"])
                sprites = pokemon_data.get("sprites", {})
                image = (
                    sprites.get("other", {})
                    .get("official-artwork", {})
                    .get("front_default", "")
                ) or sprites.get("front_default", "")
                shiny = sprites.get("front_shiny", "")
            except requests.RequestException:
                image = ""
                shiny = ""

            mega_evolutions.append(
                {
                    "name": name,
                    "image": image,
                    "shiny_image": shiny,
                }
            )
    return mega_evolutions


def extract_locations(api_data, limit=8):
    encounters_url = api_data.get("location_area_encounters")
    if not encounters_url:
        return []

    try:
        encounters = fetch_location_area_encounters(encounters_url)
    except requests.RequestException:
        return []

    locations = []
    for encounter in encounters[:limit]:
        name = encounter.get("location_area", {}).get("name", "")
        if name:
            locations.append(format_location_name(name))
    return locations


def format_location_name(name):
    return name.replace("-", " ").replace(" area", "").title()


def extract_type_relations(types):
    weaknesses = set()
    strengths = set()

    for type_name in types:
        english_type = REVERSE_TYPE_TRANSLATIONS.get(type_name, type_name)
        try:
            type_data = fetch_type_detail(english_type)
        except requests.RequestException:
            continue

        relations = type_data.get("damage_relations", {})
        for item in relations.get("double_damage_from", []):
            weaknesses.add(translate_type(item.get("name", "")))
        for item in relations.get("double_damage_to", []):
            strengths.add(translate_type(item.get("name", "")))

    return {
        "weaknesses": sorted(weaknesses),
        "strengths": sorted(strengths),
    }


def transform_pokemon(api_data):
    """Convierte la respuesta de PokeAPI en documentos limpios para MongoDB."""
    types = [
        translate_type(item["type"]["name"])
        for item in sorted(api_data.get("types", []), key=lambda type_item: type_item["slot"])
    ]

    abilities = [
        item["ability"]["name"].replace("-", " ")
        for item in api_data.get("abilities", [])
    ]

    sprite = api_data.get("sprites", {}).get("front_default", "")
    official_artwork = (
        api_data.get("sprites", {})
        .get("other", {})
        .get("official-artwork", {})
        .get("front_default", "")
    )
    shiny_sprite = api_data.get("sprites", {}).get("front_shiny", "")
    name = api_data.get("name", "").strip().lower()

    description = build_description(name, types)
    evolution_line = []
    evolution_methods = {}
    mega_evolutions = []
    species_url = api_data.get("species", {}).get("url")
    if species_url:
        species_data = fetch_species_detail(species_url)
        description = extract_pokedex_description(species_data) or description
        mega_evolutions = extract_mega_evolutions(species_data)
        evolution_url = species_data.get("evolution_chain", {}).get("url")
        if evolution_url:
            evolution_line, evolution_methods = extract_evolution_data(
                fetch_evolution_chain(evolution_url)
            )

    previous_evolutions, next_evolutions = split_evolutions(name, evolution_line)
    evolution_details = build_evolution_details(evolution_line, evolution_methods)
    type_relations = extract_type_relations(types)

    return {
        "name": name,
        "pokedex_number": api_data.get("id"),
        "is_legendary": False,
        "types": types,
        "stats": extract_stats(api_data),
        "description": description,
        "height": api_data.get("height", 0),
        "weight": api_data.get("weight", 0),
        "image": official_artwork or sprite,
        "shiny_image": shiny_sprite,
        "abilities": abilities,
        "evolution_line": evolution_line,
        "evolution_details": evolution_details,
        "evolution_methods": evolution_methods,
        "previous_evolutions": previous_evolutions,
        "next_evolutions": next_evolutions,
        "mega_evolutions": mega_evolutions,
        "locations": extract_locations(api_data),
        "weaknesses": type_relations["weaknesses"],
        "strengths": type_relations["strengths"],
    }


def build_description(name, types):
    return f"{name.capitalize()} es un Pokemon de {describe_types(types)} importado desde PokeAPI."
