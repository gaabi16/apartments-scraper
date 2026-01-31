from flask import Blueprint, jsonify, send_file, request
from scrapers.runner import status, start_scraper
from flask_cors import CORS
import os

routes = Blueprint("routes", __name__)
CORS(routes)

@routes.route("/scrape/<site>")
def scrape(site):
    if site not in status:
        return jsonify({"error": "Unknown site"}), 404

    # Preluam parametrii din URL (trimisi de frontend)
    try:
        rooms = int(request.args.get('rooms', 2))
        price_min = int(request.args.get('price_min', 10000))
        price_max = int(request.args.get('price_max', 81000))
        # Adaugam preluarea sectorului (default Sector 1)
        sector = int(request.args.get('sector', 1))
    except ValueError:
        return jsonify({"error": "Parametrii de filtrare invalizi"}), 400

    # VALIDARE BACKEND: Verificam logica preturilor
    if price_min > price_max:
        return jsonify({"error": "Prețul minim nu poate fi mai mare decât prețul maxim."}), 400

    print(f"Request scrape {site}: Camere={rooms}, Sector={sector}, Pret={price_min}-{price_max}")

    # Trimitem filtrele (inclusiv sectorul) catre runner
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

    # MODIFICARE: Nu mai stergem fisierul imediat dupa trimitere.
    # Astfel, utilizatorul poate apasa "Descarca" de mai multe ori.
    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        print(f"Eroare la download: {e}")
        return "Eroare server la descarcare", 500