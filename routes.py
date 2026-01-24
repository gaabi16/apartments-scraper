from flask import Blueprint, jsonify, send_file, request
from scrapers.runner import status, start_scraper
from flask_cors import CORS
import os

routes = Blueprint("routes", __name__)
CORS(routes)

@routes.route("/scrape/<site>")
def scrape(site):
    if site not in status:
        return jsonify({"error": "Unknown site"})

    # Preluam parametrii din URL (trimisi de frontend)
    # Default: 2 camere, 10k - 81k EUR daca nu sunt specificati
    try:
        rooms = int(request.args.get('rooms', 2))
        price_min = int(request.args.get('price_min', 10000))
        price_max = int(request.args.get('price_max', 81000))
    except ValueError:
        return jsonify({"error": "Parametrii de filtrare invalizi"}), 400

    print(f"Request scrape {site}: Camere={rooms}, Pret={price_min}-{price_max}")

    # Trimitem filtrele catre runner
    started = start_scraper(site, rooms, price_min, price_max)
    return jsonify({"started": started})


@routes.route("/status/<site>")
def get_status(site):
    if site not in status:
        return jsonify({"error": "Unknown site"})
    return jsonify(status[site])


@routes.route("/download/<site>")
def download(site):
    if site not in status:
        return "Unknown site"

    file_path = status[site]["file"]

    if not file_path or not os.path.exists(file_path):
        return "Fisier indisponibil."

    response = send_file(file_path, as_attachment=True)

    try:
        os.remove(file_path)
        status[site]["file"] = None
    except:
        pass

    return response