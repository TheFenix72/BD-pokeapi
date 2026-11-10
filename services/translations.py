TYPE_TRANSLATIONS = {
    "normal": "normal",
    "fire": "fuego",
    "water": "agua",
    "electric": "electrico",
    "grass": "planta",
    "ice": "hielo",
    "fighting": "lucha",
    "poison": "veneno",
    "ground": "tierra",
    "flying": "volador",
    "psychic": "psiquico",
    "bug": "bicho",
    "rock": "roca",
    "ghost": "fantasma",
    "dragon": "dragón",
    "dark": "siniestro",
    "steel": "acero",
    "fairy": "hada",
}

REVERSE_TYPE_TRANSLATIONS = {
    spanish: english for english, spanish in TYPE_TRANSLATIONS.items()
}
REVERSE_TYPE_TRANSLATIONS["dragon"] = "dragon"


def translate_type(value):
    """Devuelve el tipo en espanol, aceptando entrada en ingles o espanol."""
    normalized = value.strip().lower()
    if normalized in TYPE_TRANSLATIONS:
        return TYPE_TRANSLATIONS[normalized]
    if normalized in REVERSE_TYPE_TRANSLATIONS:
        return normalized
    return normalized


def translate_types(values):
    return [translate_type(value) for value in values if value.strip()]


def describe_types(types):
    if not types:
        return "tipo desconocido"
    if len(types) == 1:
        return f"tipo {types[0]}"
    return f"tipos {', '.join(types[:-1])} y {types[-1]}"
