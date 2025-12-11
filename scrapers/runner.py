import threading
from scrapers.imobiliare_scraper import scrape_imobiliare
from scrapers.publi24_scraper import scrape_publi24

status = {
    "imobiliare": {"running": False, "finished": False, "file": None},
    "publi24": {"running": False, "finished": False, "file": None},
}


def run_imobiliare():
    status["imobiliare"]["running"] = True
    status["imobiliare"]["finished"] = False
    status["imobiliare"]["file"] = None

    try:
        file = scrape_imobiliare()
        status["imobiliare"]["file"] = file
    except Exception as e:
        print("EROARE IMOBILIARE:", e)

    status["imobiliare"]["running"] = False
    status["imobiliare"]["finished"] = True


def run_publi24():
    status["publi24"]["running"] = True
    status["publi24"]["finished"] = False
    status["publi24"]["file"] = None

    try:
        file = scrape_publi24()
        status["publi24"]["file"] = file
    except Exception as e:
        print("EROARE PUBLI24:", e)

    status["publi24"]["running"] = False
    status["publi24"]["finished"] = True


def start_scraper(site_name):
    if status[site_name]["running"]:
        return False  # deja rulează

    if site_name == "imobiliare":
        threading.Thread(target=run_imobiliare).start()
    elif site_name == "publi24":
        threading.Thread(target=run_publi24).start()

    return True
