import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    """Configuracion central de la aplicacion."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    MONGO_URI = os.getenv("MONGO_URI")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "pokemon_db")
    POKEMON_COLLECTION = "pokemon"
    POKEAPI_URL = "https://pokeapi.co/api/v2/pokemon"

