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
    return webdriver.Chrome(options=options)

def clean(text):
    if not text: return ""
    return " ".join(text.replace("\n", " ").split())

def extract_numeric_price(price_text):
    if not price_text: return None
    clean_txt = price_text.replace(".", "").replace(",", ".").replace("EUR", "").replace("€", "")
    match = re.search(r"(\d+)", clean_txt)
    return float(match.group(1)) if match else None

def extract_all_pages(soup):
    pagination = soup.select_one("ul.pagination")
    if not pagination: return [1]
    visible_pages = []
    for li in pagination.find_all("li"):
        a = li.find("a")
        if a and a.text.strip().isdigit():
            visible_pages.append(int(a.text.strip()))
    return list(range(1, max(visible_pages) + 1)) if visible_pages else [1]

def scrape_page_data(driver, page_number, rooms, seen_fingerprints):
    """
    Folosim seen_fingerprints pentru a identifica unicitatea anuntului dupa continut, nu dupa link.
    """
    time.sleep(3) 
    soup = BeautifulSoup(driver.page_source, "html.parser")
    articles = soup.select("div.article-list > div.article-item")
    
    excel_results = []
    db_results = []

    for article in articles:
        try:
            title_el = article.select_one("h2.article-title a")
            link = title_el["href"] if title_el else ""
            
            title = clean(title_el.get_text()) if title_el else ""
            desc_el = article.select_one("p.article-description")
            descriere = clean(desc_el.get_text()) if desc_el else ""
            loc_el = article.select_one("p.article-location span")
            zona = clean(loc_el.get_text()) if loc_el else ""
            price_el = article.select_one("div.article-info span.article-price")
            pret_str = clean(price_el.get_text()) if price_el else ""
            pret_val = extract_numeric_price(pret_str)

            short_info_el = article.select_one("p.article-short-info span.article-lbl-txt")
            suprafata_str = ""
            suprafata_val = None
            if short_info_el:
                txt = short_info_el.get_text()
                match = re.search(r"(\d+)\s*m", txt)
                if match:
                    suprafata_str = match.group(1)
                    suprafata_val = float(match.group(1))

            # --- LOGICA DE UNICITATE BAZATA PE CONTINUT ---
            # Cream o amprenta unica: titlu + pret + zona + suprafata
            fingerprint = f"{title}_{pret_val}_{zona}_{suprafata_val}"
            
            if fingerprint in seen_fingerprints:
                continue # Este duplicat de continut, ignoram
            
            seen_fingerprints.add(fingerprint)
            # ----------------------------------------------

            excel_results.append([title, link, descriere, zona, suprafata_str, pret_str, page_number])
            
            db_results.append({
                'source_website': 'Publi24',
                'title': title,
                'price': pret_val,
                'location': zona,
                'surface': suprafata_val,
                'rooms': rooms,
                'description': descriere,
                'link': link
            })

        except Exception as e:
            continue

    return excel_results, db_results

def scrape_publi24(rooms, price_min, price_max, sector):
    driver = get_driver()
    
    room_slug = f"apartamente-{rooms}-camere" if rooms > 1 else "apartamente-1-camera"
    base_url = f"https://www.publi24.ro/anunturi/imobiliare/de-vanzare/apartamente/{room_slug}/bucuresti/sector-{sector}/"
    query_params = f"?minprice={price_min}&maxprice={price_max}"
    start_url = base_url + query_params
    
    print(f"Accessing Publi24: {start_url}")
    driver.get(start_url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    pages = extract_all_pages(soup)
    print("Pagini găsite:", pages)

    all_excel = []
    all_db = []
    
    # Set pentru amprente unice de continut
    seen_fingerprints = set()

    for page_number in pages:
        if page_number == 1:
            url = start_url
        else:
            url = start_url + f"&pag={page_number}"

        print(f"Scraping pagina {page_number}")
        driver.get(url)
        ex_res, db_res = scrape_page_data(driver, page_number, rooms, seen_fingerprints)
        all_excel.extend(ex_res)
        all_db.extend(db_res)

    driver.quit()

    print(f"Se salveaza {len(all_db)} anunturi UNICE (continut) Publi24 in DB...")
    database.insert_batch_apartments(all_db)

    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"publi24_s{sector}_{int(time.time())}.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.append(["Titlu", "Link", "Descriere", "Zona", "Suprafata(mp)", "Pret", "Pagina"])
    for r in all_excel:
        ws.append(r)
    wb.save(file_path)
    
    return file_path