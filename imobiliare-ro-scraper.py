from flask import Flask, render_template, send_file, jsonify
from selenium import webdriver
from bs4 import BeautifulSoup
from openpyxl import Workbook
import tempfile
import os
import threading
import re
import time

app = Flask(__name__)
URL = "https://www.imobiliare.ro/vanzare-apartamente/bucuresti/sector-1/2-camere?price=50000-80000&floor=1%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%2Cabove-10%2Cexcluded-last-floor"

# Status global
scraping_status = {
    "running": False,
    "finished": False,
    "file_path": None
}

# ----------------- Functii scraper -----------------
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=options)

def load_full_page(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def clean(text):
    if not text:
        return ""
    text = text.replace("‚Ç¨", "€").replace("»õ", "î").replace("√Ç", "ă").replace("ƒÇ", "ă")
    return " ".join(text.replace("\n", " ").split())

def extract_first_price(price_text):
    if not price_text:
        return None
    text = price_text.replace("€", "").replace("+ TVA", "").replace(" ", "").replace(".", "").replace(",", ".")
    match = re.search(r"\d+(\.\d+)?", text)
    return float(match.group()) if match else None

def scrape_and_save():
    global scraping_status
    scraping_status["running"] = True
    scraping_status["finished"] = False
    scraping_status["file_path"] = None

    driver = get_driver()
    driver.get(URL)
    time.sleep(4)
    load_full_page(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.select('div[id^="listing-"]')
    driver.quit()

    results = []

    for card in cards:
        try:
            title = card.select_one("span.relative")
            title = title.get_text(strip=True) if title else None

            price = card.select_one('[data-cy="card-price"]')
            price = price.get_text(strip=True) if price else None

            link = card.select_one('a[data-cy="listing-information-link"]')
            link = "https://www.imobiliare.ro" + link["href"] if link else None

            zona = card.select_one("p.w-full.truncate.font-normal.capitalize")
            zona = zona.get_text(strip=True) if zona else None

            first_price = extract_first_price(price)
            if first_price is None or first_price <= 80000:
                results.append({
                    "titlu": clean(title),
                    "pret": clean(price),
                    "link": clean(link),
                    "zona": clean(zona)
                })

        except Exception as e:
            print("Error", e)

    # --------------- Salvare în director temporar -------------------
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, f"anunturi_{int(time.time())}.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.append(["titlu", "pret", "link", "zona"])

    for ad in results:
        ws.append([ad["titlu"], ad["pret"], ad["link"], ad["zona"]])

    wb.save(file_path)
    print("Fisier creat:", file_path)

    scraping_status["file_path"] = file_path
    scraping_status["running"] = False
    scraping_status["finished"] = True

# ----------------- Rute Flask -----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/scrape")
def scrape_route():
    if not scraping_status["running"]:
        thread = threading.Thread(target=scrape_and_save)
        thread.start()
    return jsonify({"status": "started"})

@app.route("/status")
def status_route():
    return jsonify(scraping_status)

@app.route("/download")
def download():
    file_path = scraping_status.get("file_path")

    if not file_path or not os.path.exists(file_path):
        return "Fisierul nu exista sau scraping-ul nu s-a terminat."

    # trimite fisierul la user
    response = send_file(file_path, as_attachment=True)

    # stergem fisierul dupa ce a fost trimis
    try:
        os.remove(file_path)
        scraping_status["file_path"] = None
    except:
        pass

    return response

if __name__ == "__main__":
    app.run(debug=True)
