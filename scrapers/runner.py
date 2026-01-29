import threading
from scrapers.imobiliare_scraper import scrape_imobiliare
from scrapers.publi24_scraper import scrape_publi24
from scrapers.romimo_scraper import scrape_romimo

status = {
    "imobiliare": {"running": False, "finished": False, "file": None},
    "publi24": {"running": False, "finished": False, "file": None},
    "romimo": {"running": False, "finished": False, "file": None},
}


def run_imobiliare(rooms, price_min, price_max, sector):
    status["imobiliare"]["running"] = True
    status["imobiliare"]["finished"] = False
    status["imobiliare"]["file"] = None

    try:
        # Pasam sectorul catre scraper
        file = scrape_imobiliare(rooms, price_min, price_max, sector)
        status["imobiliare"]["file"] = file
    except Exception as e:
        print("EROARE IMOBILIARE:", e)

    status["imobiliare"]["running"] = False
    status["imobiliare"]["finished"] = True


def run_publi24(rooms, price_min, price_max, sector):
    status["publi24"]["running"] = True
    status["publi24"]["finished"] = False
    status["publi24"]["file"] = None

    try:
        # Pasam sectorul catre scraper
        file = scrape_publi24(rooms, price_min, price_max, sector)
        status["publi24"]["file"] = file
    except Exception as e:
        print("EROARE PUBLI24:", e)

    status["publi24"]["running"] = False
    status["publi24"]["finished"] = True


def run_romimo(rooms, price_min, price_max, sector):
    status["romimo"]["running"] = True
    status["romimo"]["finished"] = False
    status["romimo"]["file"] = None

    try:
        # Pasam sectorul catre scraper
        file = scrape_romimo(rooms, price_min, price_max, sector)
        status["romimo"]["file"] = file
    except Exception as e:
        print("EROARE ROMIMO:", e)

    status["romimo"]["running"] = False
    status["romimo"]["finished"] = True


def start_scraper(site_name, rooms=2, price_min=10000, price_max=81000, sector=1):
    if status[site_name]["running"]:
        return False  # deja rulează

    # Pornim thread-urile cu argumentele primite, inclusiv sectorul
    if site_name == "imobiliare":
        threading.Thread(target=run_imobiliare, args=(rooms, price_min, price_max, sector)).start()
    elif site_name == "publi24":
        threading.Thread(target=run_publi24, args=(rooms, price_min, price_max, sector)).start()
    elif site_name == "romimo":
        threading.Thread(target=run_romimo, args=(rooms, price_min, price_max, sector)).start()

    return True