from pymongo.errors import BulkWriteError, PyMongoError
from requests import RequestException

from services.mongo_service import MongoService
from services.pokemon_service import (
    fetch_first_generation,
    fetch_pokemon_detail,
    transform_pokemon,
)


def import_pokemon():
    """Importa 151 Pokémon desde PokéAPI evitando duplicados en MongoDB."""
    mongo = MongoService()
    mongo.check_connection()
    mongo.create_indexes()

    pokemon_documents = []
    results = fetch_first_generation(limit=151)

    for item in results:
        detail = fetch_pokemon_detail(item["url"])
        pokemon_documents.append(transform_pokemon(detail))

    try:
        result = mongo.insert_many(pokemon_documents)
        inserted = len(result.inserted_ids) if result else 0
        print(f"Importacion completada. Documentos insertados: {inserted}")
    except BulkWriteError as exc:
        inserted = exc.details.get("nInserted", 0)
        print(f"Importacion parcial. Insertados: {inserted}. Algunos registros ya existian.")
    finally:
        mongo.close()


if __name__ == "__main__":
    try:
        import_pokemon()
    except (RequestException, PyMongoError, ValueError) as error:
        print(f"Error durante la importacion: {error}")

