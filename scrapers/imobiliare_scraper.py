from selenium import webdriver
from bs4 import BeautifulSoup
from openpyxl import Workbook
import tempfile
import os
import time
import re
import sys

# Adaugam calea parinte pentru a putea importa database.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Database.database as database

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_argument("--headless") 
    return webdriver.Chrome(options=options)

def clean(text):
    if not text:
        return ""
    return " ".join(text.replace("\n", " ").split())

def extract_first_price(price_text):
    if not price_text:
        return None
    text = price_text.replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
    match = re.search(r"\d+(\.\d+)?", text)
    return float(match.group()) if match else None

def scrape_imobiliare(rooms, price_min, price_max, sector):
    driver = get_driver()
    
    room_str = f"{rooms}-camere" if rooms > 1 else "1-camera"
    base_url = f"https://www.imobiliare.ro/vanzare-apartamente/bucuresti/sector-{sector}/{room_str}"
    params = f"?price={price_min}-{price_max}&floor=1%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%2Cabove-10%2Cexcluded-last-floor"
    
    full_url = base_url + params
    print(f"Accessing Imobiliare URL: {full_url}")
    
    driver.get(full_url)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    results = []
    db_data = [] # Lista pentru baza de date
    
    cards = soup.select('div[id^="listing-"]')

    for card in cards:
        try:
            title = clean(card.select_one("span.relative").get_text(strip=True))
            price_str = clean(card.select_one('[data-cy="card-price"]').get_text(strip=True))
            link_el = card.select_one('a[data-cy="listing-information-link"]')
            link = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://www.imobiliare.ro" + link

            zona_el = card.select_one("p.w-full.truncate.font-normal.capitalize")
            zona = clean(zona_el.get_text(strip=True)) if zona_el else ""

            # Extragere suprafata pentru DB (incercare simpla)
            # Imobiliare are specificatiile in diverse span-uri, e mai complex, lasam None momentan sau parsam generic
            surface_val = None
            
            p_val = extract_first_price(price_str)
            
            if p_val is None or (p_val >= price_min and p_val <= price_max):
                # 1. Adaugam pentru Excel
                results.append([title, price_str, link, zona])
                
                # 2. Pregatim pentru DB
                db_item = {
                    'source_website': 'Imobiliare.ro',
                    'title': title,
                    'price': p_val,
                    'location': zona,
                    'surface': surface_val,
                    'rooms': rooms,
                    'description': '',
                    'link': link
                }
                db_data.append(db_item)

        except Exception as e:
            print(f"Eroare parsing card Imobiliare: {e}")
            continue

    # Salvare in DB
    print(f"Se salveaza {len(db_data)} anunturi in baza de date...")
    database.insert_batch_apartments(db_data)

    # Generare Excel
    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"imobiliare_s{sector}_{int(time.time())}.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.append(["titlu", "pret", "link", "zona"])
    for r in results:
        ws.append(r)

    wb.save(file_path)
    return file_path