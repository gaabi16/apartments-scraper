from flask import Blueprint, jsonify, send_file, request
from scrapers.runner import status, start_scraper
from flask_cors import CORS
from Database.database import (
    get_active_filters, save_filters,
    query_apartments, query_new_today,
)
import os

routes = Blueprint("routes", __name__)
CORS(routes)

# ---------------------------------------------------------------------------
# Scraper manual (existent)
# ---------------------------------------------------------------------------

@routes.route("/scrape/<site>")
def scrape(site):
    if site not in status:
        return jsonify({"error": "Unknown site"}), 404

    try:
        rooms = int(request.args.get('rooms', 2))
        price_min = int(request.args.get('price_min', 10000))
        price_max = int(request.args.get('price_max', 81000))
        sector = int(request.args.get('sector', 1))
    except ValueError:
        return jsonify({"error": "Parametrii de filtrare invalizi"}), 400

    if price_min > price_max:
        return jsonify({"error": "Prețul minim nu poate fi mai mare decât prețul maxim."}), 400

    print(f"Request scrape {site}: Camere={rooms}, Sector={sector}, Pret={price_min}-{price_max}")
    started = start_scraper(site, rooms, price_min, price_max, sector)
    return jsonify({"started": started})


@routes.route("/status/<site>")
def get_status(site):
    if site not in status:
        return jsonify({"error": "Unknown site"}), 404
    return jsonify(status[site])


@routes.route("/download/<site>")
def download(site):
    if site not in status:
        return "Unknown site", 404

    file_path = status[site]["file"]
    if not file_path or not os.path.exists(file_path):
        return "Fisier indisponibil (posibil sters sau negenerat inca).", 404

    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        print(f"Eroare la download: {e}")
        return "Eroare server la descarcare", 500


# ---------------------------------------------------------------------------
# Filtre utilizator
# ---------------------------------------------------------------------------

@routes.route("/api/filters", methods=["GET"])
def get_filters():
    return jsonify(get_active_filters())


@routes.route("/api/filters", methods=["POST"])
def post_filters():
    data = request.get_json(force=True) or {}
    try:
        rooms = int(data.get("rooms", 2))
        sector = int(data.get("sector", 0))
        price_min = int(data.get("price_min", 10000))
        price_max = int(data.get("price_max", 150000))
    except (ValueError, TypeError):
        return jsonify({"error": "Parametrii invalizi"}), 400

    if price_min > price_max:
        return jsonify({"error": "price_min > price_max"}), 400

    new_id = save_filters(rooms, sector, price_min, price_max)
    return jsonify({"saved": True, "id": new_id}), 201


# ---------------------------------------------------------------------------
# GET /api/apartments — toate, cu filtre opționale + paginare
# ---------------------------------------------------------------------------

@routes.route("/api/apartments")
def api_apartments():
    try:
        rooms = int(request.args["rooms"]) if "rooms" in request.args else None
        sector = int(request.args["sector"]) if "sector" in request.args else None
        price_min = int(request.args["price_min"]) if "price_min" in request.args else None
        price_max = int(request.args["price_max"]) if "price_max" in request.args else None
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
        sort_by = request.args.get("sort_by", "scraped_at")
        sort_dir = request.args.get("sort_dir", "desc")
    except ValueError:
        return jsonify({"error": "Parametrii invalizi"}), 400

    result = query_apartments(
        rooms=rooms, sector=sector,
        price_min=price_min, price_max=price_max,
        page=page, per_page=per_page,
        sort_by=sort_by, sort_dir=sort_dir,
    )
    return jsonify(result)


# ---------------------------------------------------------------------------
# GET /api/apartments/new — doar cele apărute azi față de ieri
# ---------------------------------------------------------------------------

@routes.route("/api/apartments/new")
def api_apartments_new():
    try:
        rooms = int(request.args["rooms"]) if "rooms" in request.args else None
        sector = int(request.args["sector"]) if "sector" in request.args else None
        price_min = int(request.args["price_min"]) if "price_min" in request.args else None
        price_max = int(request.args["price_max"]) if "price_max" in request.args else None
    except ValueError:
        return jsonify({"error": "Parametrii invalizi"}), 400

    result = query_new_today(
        rooms=rooms, sector=sector,
        price_min=price_min, price_max=price_max,
    )
    return jsonify(result)
