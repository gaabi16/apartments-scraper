from selenium import webdriver
from bs4 import BeautifulSoup
from openpyxl import Workbook
import tempfile
import os
import time
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Database.database as database

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_argument("--headless") # Poți decomenta pentru rulare fără interfață grafică
    return webdriver.Chrome(options=options)

def clean_text(text):
    """Elimină spațiile multiple și caracterele nedorite."""
    if not text:
        return None
    cleaned = " ".join(text.replace("\n", " ").split())
    return cleaned if cleaned else None

def extract_price(text):
    """
    Extrage doar valoarea numerică a prețului.
    Ex: '67.000 EUR' -> 67000
    """
    if not text:
        return None
    # Păstrăm doar cifrele
    digits = re.sub(r'[^\d]', '', text)
    if digits:
        return int(digits)
    return None

def extract_surface(text):
    """
    Caută un pattern de suprafață în textul cardului.
    Ex: '50 mp' -> 50.0
    """
    if not text:
        return None
    # Căutăm numere urmate de mp, m2, metri
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:mp|m2|metri)', text, re.IGNORECASE)
    if match:
        val_str = match.group(1).replace(',', '.')
        return float(val_str)
    return None

def scrape_imobiliare(rooms, price_min, price_max, sector):
    driver = get_driver()
    
    room_str = f"{rooms}-camere" if rooms > 1 else "1-camera"
    base_url = f"https://www.imobiliare.ro/vanzare-apartamente/bucuresti/sector-{sector}/{room_str}"
    # Parametrii URL standard pentru Imobiliare.ro
    params = f"?price={price_min}-{price_max}&floor=1%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%2Cabove-10%2Cexcluded-last-floor"
    
    full_url = base_url + params
    print(f"Accessing Imobiliare URL: {full_url}")
    
    driver.get(full_url)
    time.sleep(5)

    # --- LOGICA INFINITE SCROLL PENTRU A VIZITA TOATE PAGINILE (LISTA COMPLETA) ---
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    results_excel = []
    results_db = []
    
    # Set pentru unicitate (titlu + locatie + pret + suprafata)
    seen_fingerprints = set()

    # Selectorii pot varia, folosim id-ul generic care apare pe carduri
    cards = soup.select('div[id^="listing-"]')
    print(f"Carduri gasite (brut): {len(cards)}")

    for card in cards:
        try:
            # 1. LINK
            link_el = card.select_one('a[data-cy="listing-information-link"]')
            link = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://www.imobiliare.ro" + link
            
            # 2. TITLU
            title_el = card.select_one("span.relative") or card.select_one("h2")
            title = clean_text(title_el.get_text(strip=True)) if title_el else None

            # 3. LOCATIE
            zona_el = card.select_one("p.w-full.truncate.font-normal.capitalize") or card.select_one(".location")
            location = clean_text(zona_el.get_text(strip=True)) if zona_el else None

            # 4. PRET
            price_el = card.select_one('[data-cy="card-price"]') or card.select_one(".price")
            price_raw = price_el.get_text(strip=True) if price_el else ""
            price_val = extract_price(price_raw)

            # 5. DESCRIERE & SUPRAFATA
            # Imobiliare nu arata descrierea full pe card, luam tot textul cardului pentru a extrage suprafata
            full_card_text = card.get_text(separator=" ")
            
            # Descrierea pe scurt (daca exista un snippet) sau Titlul ca fallback
            desc_el = card.select_one(".description") # Clasa generica, posibil sa nu existe mereu
            description = clean_text(desc_el.get_text()) if desc_el else clean_text(title)

            # Extragem suprafata din textul general al cardului
            surface_val = extract_surface(full_card_text)

            # --- FILTRU UNICITATE ---
            # Cheia unica ceruta: {titlu + locatie + pret + suprafata}
            fingerprint = f"{title}_{location}_{price_val}_{surface_val}"
            
            if fingerprint in seen_fingerprints:
                continue
            seen_fingerprints.add(fingerprint)
            
            # Verificare suplimentară de preț (deși URL-ul filtrează, e bine să fim siguri)
            if price_val and (price_min <= price_val <= price_max):
                
                # Lista pentru Excel: [titlu, descriere, pret, locatie, suprafata, link]
                results_excel.append([
                    title, 
                    description, 
                    price_val,   # Numeric
                    location, 
                    surface_val, # Numeric
                    link
                ])
                
                # Obiect pentru DB
                db_item = {
                    'source_website': 'Imobiliare.ro',
                    'title': title,
                    'price': price_val,
                    'location': location,
                    'surface': surface_val,
                    'rooms': rooms,
                    'description': description,
                    'link': link
                }
                results_db.append(db_item)

        except Exception as e:
            # print(f"Eroare parsing card: {e}")
            continue

    # Salvare în Baza de Date
    print(f"Se salveaza {len(results_db)} anunturi UNICE in baza de date...")
    database.insert_batch_apartments(results_db)

    # Generare Excel
    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"imobiliare_s{sector}_{int(time.time())}.xlsx")

    wb = Workbook()
    ws = wb.active
    # Header consistent
    ws.append(["Titlu", "Descriere", "Pret", "Locatie", "Suprafata", "Link"])
    
    for r in results_excel:
        ws.append(r)

    wb.save(file_path)
    return file_path