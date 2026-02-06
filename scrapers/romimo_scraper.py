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

def clean_text(text):
    if not text: return None
    cleaned = " ".join(text.replace("\n", " ").split())
    return cleaned if cleaned else None

def extract_price(text):
    if not text: return None
    digits = re.sub(r'[^\d]', '', text)
    return int(digits) if digits else None

def extract_surface(text):
    if not text: return None
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:m|mp)', text, re.IGNORECASE)
    if match:
        return float(match.group(1).replace(',', '.'))
    return None

def extract_all_pages(soup):
    pagination = soup.select_one("ul.pagination")
    if not pagination: return [1]
    page_numbers = []
    for li in pagination.find_all("li"):
        a = li.find("a")
        if a and a.text.strip().isdigit():
            page_numbers.append(int(a.text.strip()))
    return list(range(1, max(page_numbers) + 1)) if page_numbers else [1]

def scrape_page(driver, page_number, rooms, seen_fingerprints):
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    article_list = soup.select_one("div.article-list")
    if not article_list: return [], []
    
    articles = article_list.select("div.article-item")
    excel_results = []
    db_results = []
    
    for article in articles:
        try:
            # 1. LINK & TITLU
            title_el = article.select_one("h2.article-title a")
            link = title_el["href"] if title_el and title_el.has_attr("href") else ""
            title = clean_text(title_el.get_text()) if title_el else None
            
            # 2. DESCRIERE
            desc_el = article.select_one("p.article-description")
            description = clean_text(desc_el.get_text()) if desc_el else None
            
            # 3. LOCATIE
            loc_el = article.select_one("p.article-location span")
            location = clean_text(loc_el.get_text()) if loc_el else None
            
            # 4. PRET
            price_el = article.select_one("span.article-price")
            price_raw = price_el.get_text() if price_el else ""
            price_val = extract_price(price_raw)
            
            # 5. SUPRAFATA
            short_info_el = article.select_one("p.article-short-info span.article-lbl-txt")
            short_info_text = short_info_el.get_text() if short_info_el else ""
            surface_val = extract_surface(short_info_text)
            
            # --- UNICITATE ---
            fingerprint = f"{title}_{location}_{price_val}_{surface_val}"
            if fingerprint in seen_fingerprints:
                continue
            seen_fingerprints.add(fingerprint)
            
            # Lista Excel
            excel_results.append([
                title, 
                description, 
                price_val, 
                location, 
                surface_val, 
                link
            ])
            
            # Obiect DB
            db_results.append({
                'source_website': 'Romimo',
                'title': title,
                'price': price_val,
                'location': location,
                'surface': surface_val,
                'rooms': rooms,
                'description': description,
                'link': link
            })
            
        except Exception as e:
            continue
    
    return excel_results, db_results

def scrape_romimo(rooms, price_min, price_max, sector):
    driver = get_driver()
    
    room_slug = f"apartamente-{rooms}-camere" if rooms > 1 else "apartamente-1-camera"
    base_url = f"https://www.romimo.ro/apartamente/{room_slug}/vanzare/bucuresti/sector-{sector}/"
    query_params = f"?minprice={price_min}&maxprice={price_max}"
    
    start_url = base_url + query_params
    print(f"Accessing Romimo: {start_url}")
    
    driver.get(start_url)
    time.sleep(4)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    # Vizitare toate paginile
    pages = extract_all_pages(soup)
    print(f"Pagini găsite: {pages}")
    
    all_excel = []
    all_db = []
    seen_fingerprints = set()
    
    for page_number in pages:
        current_url = start_url if page_number == 1 else start_url + f"&pag={page_number}"
        
        print(f"Scraping pagina {page_number}")
        driver.get(current_url)
        ex_res, db_res = scrape_page(driver, page_number, rooms, seen_fingerprints)
        all_excel.extend(ex_res)
        all_db.extend(db_res)
    
    driver.quit()
    
    print(f"Se salveaza {len(all_db)} anunturi UNICE Romimo in DB...")
    database.insert_batch_apartments(all_db)
    
    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"romimo_s{sector}_{int(time.time())}.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.append(["Titlu", "Descriere", "Pret", "Locatie", "Suprafata", "Link"])
    for r in all_excel:
        ws.append(r)
    wb.save(file_path)
    
    return file_path