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
    # options.add_argument("--headless") # Poti decomenta daca vrei sa ruleze in fundal
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
    time.sleep(5) # Asteptam incarcarea initiala

    # --- LOGICA SCROLL ---
    # Imobiliare incarca anunturile pe masura ce dai scroll. Trebuie sa fortam incarcarea.
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3) # Asteptam sa incarce noile carduri
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    # ---------------------

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    results_excel = []
    results_db = []
    
    # Set pentru a asigura unicitatea in timpul rularii curente
    seen_links = set()

    cards = soup.select('div[id^="listing-"]')
    print(f"Carduri gasite (brut): {len(cards)}")

    for card in cards:
        try:
            link_el = card.select_one('a[data-cy="listing-information-link"]')
            link = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://www.imobiliare.ro" + link
            
            # 1. VERIFICARE UNICITATE
            if not link or link in seen_links:
                continue
            
            # Adaugam link-ul in set pentru a nu-l mai procesa a doua oara
            seen_links.add(link)

            title = clean(card.select_one("span.relative").get_text(strip=True))
            price_str = clean(card.select_one('[data-cy="card-price"]').get_text(strip=True))
            
            zona_el = card.select_one("p.w-full.truncate.font-normal.capitalize")
            zona = clean(zona_el.get_text(strip=True)) if zona_el else ""

            surface_val = None # Parsarea suprafetei e complexa pe Imobiliare, lasam None momentan
            p_val = extract_first_price(price_str)
            
            # Filtrare suplimentara de siguranta pentru pret
            if p_val is None or (p_val >= price_min and p_val <= price_max):
                
                # Lista pentru Excel
                results_excel.append([title, price_str, link, zona])
                
                # Lista pentru DB
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
                results_db.append(db_item)

        except Exception as e:
            print(f"Eroare parsing card Imobiliare: {e}")
            continue

    # Acum salvam doar listele unice
    print(f"Se salveaza {len(results_db)} anunturi UNICE in baza de date...")
    database.insert_batch_apartments(results_db)

    # Generare Excel
    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"imobiliare_s{sector}_{int(time.time())}.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.append(["titlu", "pret", "link", "zona"])
    for r in results_excel:
        ws.append(r)

    wb.save(file_path)
    return file_path