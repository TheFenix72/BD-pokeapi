import os
from uuid import uuid4

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, flash, redirect, render_template, request, url_for
from pymongo.errors import DuplicateKeyError, PyMongoError
from werkzeug.utils import secure_filename

from config import Config
from services.mongo_service import MongoService
from services.translations import translate_types


app = Flask(__name__)
app.config.from_object(Config)
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def get_mongo():
    mongo = MongoService()
    mongo.create_indexes()
    return mongo


def parse_csv_field(value):
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def parse_type_field(value):
    return translate_types(parse_csv_field(value))


def parse_bool(value):
    return value == "on"


def parse_int(value, field_name, min_value=0):
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"El campo {field_name} debe ser un numero entero.") from exc

    if number < min_value:
        raise ValueError(f"El campo {field_name} no puede ser menor que {min_value}.")
    return number


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_image(file_storage):
    if not file_storage or not file_storage.filename:
        return ""
    if not allowed_image(file_storage.filename):
        raise ValueError("La imagen debe ser png, jpg, jpeg, gif o webp.")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    filename = secure_filename(file_storage.filename)
    extension = filename.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid4().hex}.{extension}"
    file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_filename))
    return url_for("static", filename=f"uploads/{unique_filename}")


def pokemon_from_form(form, files=None, existing=None):
    """Valida y transforma datos del formulario en un documento MongoDB."""
    existing = existing or {}
    name = form.get("name", "").strip().lower()
    description = form.get("description", "").strip()
    types = parse_type_field(form.get("types", ""))
    abilities = parse_csv_field(form.get("abilities", ""))
    image = form.get("image", "").strip() or existing.get("image", "")
    shiny_image = form.get("shiny_image", "").strip() or existing.get("shiny_image", "")
    if files:
        uploaded_image = save_uploaded_image(files.get("image_file"))
        if uploaded_image:
            image = uploaded_image
        uploaded_shiny = save_uploaded_image(files.get("shiny_image_file"))
        if uploaded_shiny:
            shiny_image = uploaded_shiny

    mega_name = form.get("mega_name", "").strip().lower()
    mega_image = form.get("mega_image", "").strip()
    mega_shiny_image = form.get("mega_shiny_image", "").strip()
    mega_evolutions = existing.get("mega_evolutions", [])
    if mega_name or mega_image or mega_shiny_image:
        mega_evolutions = [
            {
                "name": mega_name or f"{name}-mega",
                "image": mega_image,
                "shiny_image": mega_shiny_image,
            }
        ]

    locations = parse_csv_field(form.get("locations", ""))
    weaknesses = parse_type_field(form.get("weaknesses", ""))
    strengths = parse_type_field(form.get("strengths", ""))

    if not name:
        raise ValueError("El nombre es obligatorio.")
    if not description:
        raise ValueError("La descripcion es obligatoria.")
    if not types:
        raise ValueError("Debe indicar al menos un tipo.")

    return {
        "name": name,
        "pokedex_number": parse_int(form.get("pokedex_number"), "numero Pokédex", 1),
        "is_legendary": parse_bool(form.get("is_legendary")),
        "types": types,
        "stats": {
            "hp": parse_int(form.get("hp"), "HP"),
            "attack": parse_int(form.get("attack"), "ataque"),
            "defense": parse_int(form.get("defense"), "defensa"),
            "special_attack": parse_int(form.get("special_attack"), "ataque especial"),
            "special_defense": parse_int(form.get("special_defense"), "defensa especial"),
            "speed": parse_int(form.get("speed"), "velocidad"),
        },
        "description": description,
        "height": parse_int(form.get("height"), "altura"),
        "weight": parse_int(form.get("weight"), "peso"),
        "image": image,
        "shiny_image": shiny_image,
        "abilities": abilities,
        "mega_evolutions": mega_evolutions,
        "locations": locations,
        "weaknesses": weaknesses,
        "strengths": strengths,
        "evolution_line": existing.get("evolution_line", [name]),
        "evolution_details": existing.get(
            "evolution_details",
            [{"name": name, "image": image, "method": "Pokemon creado manualmente"}],
        ),
        "previous_evolutions": existing.get("previous_evolutions", []),
        "next_evolutions": existing.get("next_evolutions", []),
    }


def safe_object_id(value):
    try:
        return ObjectId(value)
    except InvalidId:
        return None

def build_search_query(params):
    """Construye una consulta MongoDB combinando todos los filtros activos."""
    clauses = []
    applied_filters = []
    use_text_score = False

    if params["query"]:
        clauses.append({"$text": {"$search": params["query"]}})
        applied_filters.append("texto en descripcion ($text)")
        use_text_score = True

    if params["min_attack"]:
        clauses.append(
            {"stats.attack": {"$gt": parse_int(params["min_attack"], "ataque minimo")}}
        )
        applied_filters.append("ataque mayor que ($gt)")

    if params["max_attack"]:
        clauses.append(
            {"stats.attack": {"$lt": parse_int(params["max_attack"], "ataque maximo")}}
        )
        applied_filters.append("ataque menor que ($lt)")

    if params["min_defense"]:
        clauses.append(
            {"stats.defense": {"$gt": parse_int(params["min_defense"], "defensa minima")}}
        )
        applied_filters.append("defensa mayor que ($gt)")

    if params["types_raw"]:
        clauses.append({"types": {"$in": parse_type_field(params["types_raw"])}})
        applied_filters.append("tipos incluidos ($in)")

    if params["regex"]:
        clauses.append({"name": {"$regex": params["regex"], "$options": "i"}})
        applied_filters.append("nombre por patron ($regex)")

    if params["max_height"]:
        clauses.append({"height": {"$lt": parse_int(params["max_height"], "altura maxima")}})
        applied_filters.append("altura menor que ($lt)")

    if params["min_height"]:
        clauses.append({"height": {"$gt": parse_int(params["min_height"], "altura minima")}})
        applied_filters.append("altura mayor que ($gt)")

    if params["has_image"]:
        clauses.append({"image": {"$exists": True, "$ne": ""}})
        applied_filters.append("imagen existente ($exists)")

    if params["types_count"]:
        clauses.append({"types": {"$size": parse_int(params["types_count"], "cantidad de tipos")}})
        applied_filters.append("cantidad exacta de tipos ($size)")

    if not clauses:
        return None, [], use_text_score

    if len(clauses) == 1:
        return clauses[0], applied_filters, use_text_score

    return {"$and": clauses}, applied_filters, use_text_score


@app.route("/")
def index():
    mongo = None
    try:
        mongo = get_mongo()
        pokemon = list(mongo.find_all())
        return render_template("index.html", pokemon=pokemon)
    except (PyMongoError, ValueError) as error:
        flash(f"Error al leer la base de datos: {error}", "error")
        return render_template("index.html", pokemon=[])
    finally:
        if mongo:
            mongo.close()


@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        mongo = None
        try:
            mongo = get_mongo()
            data = pokemon_from_form(request.form, request.files)
            if mongo.find_by_name_or_number(data["name"], data["pokedex_number"]):
                flash("Ya existe un Pokémon con ese nombre o numero Pokédex.", "error")
                return render_template("create.html", form=request.form)

            mongo.insert_one(data)
            flash("Pokémon creado correctamente.", "success")
            return redirect(url_for("index"))
        except (ValueError, DuplicateKeyError) as error:
            flash(str(error), "error")
        except PyMongoError as error:
            flash(f"Error al guardar: {error}", "error")
        finally:
            if mongo:
                mongo.close()

    return render_template("create.html", form={})


@app.route("/pokemon/<pokemon_id>")
def detail(pokemon_id):
    object_id = safe_object_id(pokemon_id)
    if not object_id:
        flash("Identificador no valido.", "error")
        return redirect(url_for("index"))

    mongo = None
    try:
        mongo = get_mongo()
        pokemon = mongo.find_by_id(object_id)
        if not pokemon:
            flash("Pokemon no encontrado.", "error")
            return redirect(url_for("index"))
        evolution_details = pokemon.get("evolution_details", [])
        evolution_names = [item.get("name") for item in evolution_details if item.get("name")]
        if evolution_names:
            linked_pokemon = {
                item["name"]: item["_id"] for item in mongo.find_by_names(evolution_names)
            }
            for evolution in evolution_details:
                evolution["pokemon_id"] = linked_pokemon.get(evolution.get("name"))
        return render_template("detail.html", pokemon=pokemon)
    except (PyMongoError, ValueError) as error:
        flash(f"Error al leer el Pokemon: {error}", "error")
        return redirect(url_for("index"))
    finally:
        if mongo:
            mongo.close()


@app.route("/edit/<pokemon_id>", methods=["GET", "POST"])
def edit(pokemon_id):
    object_id = safe_object_id(pokemon_id)
    if not object_id:
        flash("Identificador no valido.", "error")
        return redirect(url_for("index"))

    mongo = None
    pokemon = None
    try:
        mongo = get_mongo()
        pokemon = mongo.find_by_id(object_id)
        if not pokemon:
            flash("Pokémon no encontrado.", "error")
            return redirect(url_for("index"))

        if request.method == "POST":
            data = pokemon_from_form(request.form, request.files, pokemon)
            duplicate = mongo.find_by_name_or_number(data["name"], data["pokedex_number"])
            if duplicate and duplicate["_id"] != object_id:
                flash("Ya existe otro Pokémon con ese nombre o numero Pokédex.", "error")
                return render_template("edit.html", pokemon=pokemon, form=request.form)

            mongo.update_one(object_id, data)
            flash("Pokémon actualizado correctamente.", "success")
            return redirect(url_for("index"))

        return render_template("edit.html", pokemon=pokemon, form=pokemon)
    except (ValueError, DuplicateKeyError) as error:
        flash(str(error), "error")
        return render_template("edit.html", pokemon=pokemon, form=request.form)
    except PyMongoError as error:
        flash(f"Error en MongoDB: {error}", "error")
        return redirect(url_for("index"))
    finally:
        if mongo:
            mongo.close()


@app.route("/delete/<pokemon_id>", methods=["POST"])
def delete(pokemon_id):
    object_id = safe_object_id(pokemon_id)
    if not object_id:
        flash("Identificador no valido.", "error")
        return redirect(url_for("index"))

    mongo = None
    try:
        mongo = get_mongo()
        result = mongo.delete_one(object_id)
        if result.deleted_count:
            flash("Pokémon eliminado.", "success")
        else:
            flash("Pokémon no encontrado.", "error")
    except (PyMongoError, ValueError) as error:
        flash(f"Error al eliminar: {error}", "error")
    finally:
        if mongo:
            mongo.close()

    return redirect(url_for("index"))


@app.route("/search")
def search():
    params = {
        "query": request.args.get("q", "").strip(),
        "min_attack": request.args.get("min_attack", "").strip(),
        "max_attack": request.args.get("max_attack", "").strip(),
        "min_defense": request.args.get("min_defense", "").strip(),
        "types_raw": request.args.get("types", "").strip(),
        "regex": request.args.get("regex", "").strip(),
        "max_height": request.args.get("max_height", "").strip(),
        "min_height": request.args.get("min_height", "").strip(),
        "has_image": request.args.get("has_image"),
        "types_count": request.args.get("types_count", "").strip(),
    }

    mongo = None
    results = []
    applied_filter = None

    try:
        mongo = get_mongo()
        filter_query, applied_filters, use_text_score = build_search_query(params)
        if filter_query:
            results = list(mongo.find_by_filters(filter_query, use_text_score))
            applied_filter = ", ".join(applied_filters)
    except (ValueError, PyMongoError) as error:
        flash(str(error), "error")
    finally:
        if mongo:
            mongo.close()

    return render_template(
        "search.html",
        results=results,
        query=params["query"],
        min_attack=params["min_attack"],
        max_attack=params["max_attack"],
        min_defense=params["min_defense"],
        types_raw=params["types_raw"],
        regex=params["regex"],
        max_height=params["max_height"],
        min_height=params["min_height"],
        has_image=params["has_image"],
        types_count=params["types_count"],
        applied_filter=applied_filter,
    )


@app.route("/stats")
def stats():
    mongo = None
    try:
        mongo = get_mongo()
        average_attack = list(mongo.avg_attack_by_type())
        count_by_type = list(mongo.count_by_type())
        return render_template(
            "stats.html",
            average_attack=average_attack,
            count_by_type=count_by_type,
        )
    except (PyMongoError, ValueError) as error:
        flash(f"Error calculando estadisticas: {error}", "error")
        return render_template("stats.html", average_attack=[], count_by_type=[])
    finally:
        if mongo:
            mongo.close()


if __name__ == "__main__":
    app.run(debug=True)
