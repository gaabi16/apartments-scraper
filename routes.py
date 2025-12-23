from flask import Blueprint, jsonify, send_file
from scrapers.runner import status, start_scraper
from flask_cors import CORS
import os

routes = Blueprint("routes", __name__)
CORS(routes)

@routes.route("/scrape/<site>")
def scrape(site):
    if site not in status:
        return jsonify({"error": "Unknown site"})

    started = start_scraper(site)
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
