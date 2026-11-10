from pymongo.errors import PyMongoError

from services.mongo_service import MongoService
from services.pokemon_service import (
    build_description,
    build_evolution_details,
    extract_evolution_data,
    extract_pokedex_description,
    extract_mega_evolutions,
    extract_stats,
    extract_locations,
    extract_type_relations,
    fetch_evolution_chain,
    fetch_pokemon_detail,
    fetch_species_detail,
    split_evolutions,
)
from services.translations import translate_types


def update_spanish_data():
    """Actualiza documentos ya importados para mostrar tipos y descripciones en espanol."""
    mongo = MongoService()
    mongo.check_connection()

    updated = 0
    try:
        for pokemon in mongo.find_all():
            spanish_types = translate_types(pokemon.get("types", []))
            species_url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon.get('pokedex_number')}/"
            pokemon_url = f"https://pokeapi.co/api/v2/pokemon/{pokemon.get('pokedex_number')}/"
            species_data = fetch_species_detail(species_url)
            pokemon_data = fetch_pokemon_detail(pokemon_url)
            description = (
                extract_pokedex_description(species_data)
                or build_description(pokemon.get("name", ""), spanish_types)
            )
            evolution_line = []
            evolution_methods = {}
            evolution_url = species_data.get("evolution_chain", {}).get("url")
            if evolution_url:
                evolution_line, evolution_methods = extract_evolution_data(
                    fetch_evolution_chain(evolution_url)
                )
            previous_evolutions, next_evolutions = split_evolutions(
                pokemon.get("name", ""), evolution_line
            )
            type_relations = extract_type_relations(spanish_types)
            sprites = pokemon_data.get("sprites", {})
            official_artwork = (
                sprites.get("other", {})
                .get("official-artwork", {})
                .get("front_default", "")
            )
            result = mongo.update_one(
                pokemon["_id"],
                {
                    "types": spanish_types,
                    "description": description,
                    "stats": extract_stats(pokemon_data),
                    "image": official_artwork or sprites.get("front_default", pokemon.get("image", "")),
                    "shiny_image": pokemon_data.get("sprites", {}).get("front_shiny", ""),
                    "evolution_line": evolution_line,
                    "evolution_details": build_evolution_details(
                        evolution_line, evolution_methods
                    ),
                    "evolution_methods": evolution_methods,
                    "previous_evolutions": previous_evolutions,
                    "next_evolutions": next_evolutions,
                    "mega_evolutions": extract_mega_evolutions(species_data),
                    "locations": extract_locations(pokemon_data),
                    "weaknesses": type_relations["weaknesses"],
                    "strengths": type_relations["strengths"],
                },
            )
            updated += result.modified_count
    finally:
        mongo.close()

    print(f"Documentos actualizados: {updated}")


if __name__ == "__main__":
    try:
        update_spanish_data()
    except (PyMongoError, ValueError) as error:
        print(f"Error actualizando datos: {error}")
