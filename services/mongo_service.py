from pymongo import ASCENDING, TEXT, MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

from config import Config


class MongoService:
    """Capa de acceso a MongoDB para aislar PyMongo de las rutas Flask."""

    def __init__(self):
        if not Config.MONGO_URI:
            raise ValueError("Falta MONGO_URI en las variables de entorno.")

        self.client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
        self.db = self.client[Config.DATABASE_NAME]
        self.collection = self.db[Config.POKEMON_COLLECTION]

    def check_connection(self):
        try:
            self.client.admin.command("ping")
        except ConnectionFailure as exc:
            raise ConnectionFailure("No se pudo conectar con MongoDB Atlas.") from exc

    def create_indexes(self):
        """Crea indices necesarios para busquedas y control de duplicados."""
        self.collection.create_index([("name", ASCENDING)], unique=True)
        self.collection.create_index([("pokedex_number", ASCENDING)], unique=True)
        self.collection.create_index([("description", TEXT)])
        self.collection.create_index([("types", ASCENDING)])

    def insert_one(self, pokemon):
        return self.collection.insert_one(pokemon)

    def insert_many(self, pokemon_list):
        if not pokemon_list:
            return None
        return self.collection.insert_many(pokemon_list, ordered=False)

    def find_all(self):
        return self.collection.find().sort("pokedex_number", ASCENDING)

    def find_by_id(self, object_id):
        return self.collection.find_one({"_id": object_id})

    def find_by_name_or_number(self, name, pokedex_number):
        return self.collection.find_one(
            {
                "$or": [
                    {"name": name},
                    {"pokedex_number": pokedex_number},
                ]
            }
        )

    def find_by_names(self, names):
        return self.collection.find({"name": {"$in": names}})

    def update_one(self, object_id, data):
        return self.collection.update_one({"_id": object_id}, {"$set": data})

    def delete_one(self, object_id):
        return self.collection.delete_one({"_id": object_id})

    def search_text(self, text):
        return self.collection.find(
            {"$text": {"$search": text}},
            {"score": {"$meta": "textScore"}},
        ).sort([("score", {"$meta": "textScore"})])

    def find_by_filters(self, filter_query, use_text_score=False):
        """Ejecuta una busqueda combinando todos los filtros recibidos."""
        if use_text_score:
            return self.collection.find(
                filter_query,
                {"score": {"$meta": "textScore"}},
            ).sort([("score", {"$meta": "textScore"})])

        return self.collection.find(filter_query).sort("pokedex_number", ASCENDING)

    def filter_attack_gt(self, min_attack):
        return self.collection.find({"stats.attack": {"$gt": min_attack}}).sort(
            "stats.attack", ASCENDING
        )

    def filter_attack_lt(self, max_attack):
        return self.collection.find({"stats.attack": {"$lt": max_attack}}).sort(
            "stats.attack", ASCENDING
        )

    def filter_defense_gt(self, min_defense):
        return self.collection.find({"stats.defense": {"$gt": min_defense}}).sort(
            "stats.defense", ASCENDING
        )

    def filter_types_in(self, types):
        return self.collection.find({"types": {"$in": types}}).sort(
            "pokedex_number", ASCENDING
        )

    def regex_name(self, pattern):
        return self.collection.find({"name": {"$regex": pattern, "$options": "i"}})

    def height_lt(self, max_height):
        return self.collection.find({"height": {"$lt": max_height}})

    def height_gt(self, min_height):
        return self.collection.find({"height": {"$gt": min_height}})

    def with_image_exists(self):
        return self.collection.find({"image": {"$exists": True, "$ne": ""}})

    def types_size(self, size):
        return self.collection.find({"types": {"$size": size}})

    def avg_attack_by_type(self):
        return self.collection.aggregate(
            [
                {"$unwind": "$types"},
                {
                    "$group": {
                        "_id": "$types",
                        "average_attack": {"$avg": "$stats.attack"},
                    }
                },
                {"$sort": {"average_attack": -1}},
            ]
        )

    def count_by_type(self):
        return self.collection.aggregate(
            [
                {"$unwind": "$types"},
                {"$group": {"_id": "$types", "total": {"$sum": 1}}},
                {"$sort": {"total": -1}},
            ]
        )

    def close(self):
        try:
            self.client.close()
        except PyMongoError:
            pass
