import time
import random
import re
import os
import sys
import tempfile
from openpyxl import Workbook
from playwright.sync_api import sync_playwright

# Import Database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Database.database as database

def clean_text(text):
    if not text: return None
    cleaned = " ".join(text.replace("\n", " ").split())
    return cleaned if cleaned else None

def extract_price(text):
    if not text: return None
    digits = re.sub(r'[^\d]', '', text)
    if not digits: return None
    return int(digits)

def extract_surface(text):
    if not text: return None
    # Cautam pattern: 50 mp, 50.5 m2 etc.
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:mp|m2|metri)', text, re.IGNORECASE)
    if match:
        val_str = match.group(1).replace(',', '.')
        try:
            return float(val_str)
        except:
            return None
    return None

def scrape_detail_page(context, url):
    """
    Deschide o pagină nouă (tab) pentru detaliile anunțului,
    extrage datele și o închide.
    """
    data = {
        "description": None,
        "floor": None,
        "contact_name": None,
        "phone_number": None,
        "rooms": None,
        "surface": None
    }
    
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        # Pauza mica
        page.wait_for_timeout(random.randint(500, 1500))

        # --- 1. Extragere Telefon ---
        try:
            # Selector buton telefon Publi24
            # <div class="show-phone-number" data-action="phone">
            phone_btn_sel = ".show-phone-number button.btn-show-phone"
            if page.is_visible(phone_btn_sel):
                # Verificam daca e deja afisat sau trebuie click
                if not page.locator(".telnumber").is_visible():
                    page.click(phone_btn_sel)
                    page.wait_for_timeout(1000)
                
                # Telefonul apare uneori ca imagine de fundal (base64) sau text
                # Daca e text:
                phone_text = page.locator(".telnumber").inner_text()
                if not phone_text:
                    # Daca e imagine, incercam sa luam atributul style sau valoarea din input hidden
                    # Publi24 are un input hidden cu telefonul criptat uneori, dar greu de decodat.
                    # Ne bazam pe text vizibil momentan.
                    pass
                else:
                    extracted = re.search(r'(\d{10}|\d{3}\s\d{3}\s\d{3})', phone_text)
                    if extracted:
                        data["phone_number"] = extracted.group(0).replace(" ", "")
        except:
            pass

        # --- 2. Descriere ---
        try:
            desc_loc = page.locator(".article-description").first
            if desc_loc.is_visible():
                data["description"] = clean_text(desc_loc.inner_text())
        except:
            pass

        # --- 3. Detalii din tabel (Specificatii) ---
        # <div class="attribute-item"> <div class="attribute-label">...</div> <div class="attribute-value">...</div> </div>
        try:
            attributes = page.locator(".article-attributes .attribute-item").all()
            for attr in attributes:
                label = clean_text(attr.locator(".attribute-label").inner_text()).lower()
                value = clean_text(attr.locator(".attribute-value").inner_text())
                
                if "etaj" in label:
                    data["floor"] = value
                elif "camere" in label:
                    try:
                        # "2 camere" -> 2
                        data["rooms"] = int(re.sub(r'[^\d]', '', value))
                    except:
                        pass
                elif "suprafata" in label:
                    data["surface"] = extract_surface(value)
        except:
            pass

        # --- 4. Contact ---
        try:
            # <h2 class="user-profile-name">
            contact_loc = page.locator(".user-profile-name a").first
            if contact_loc.is_visible():
                data["contact_name"] = clean_text(contact_loc.inner_text())
        except:
            pass

    except Exception as e:
        print(f"Eroare la pagina de detaliu {url}: {e}")
    finally:
        page.close()

    return data

def scrape_publi24(rooms, price_min, price_max, sector):
    # Setup path Excel
    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"publi24_s{sector}_{int(time.time())}.xlsx")
    results_to_save = []

    # Configurare Playwright
    with sync_playwright() as p:
        print("Lansare browser Playwright pentru Publi24...")
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        page = context.new_page()

        try:
            room_slug = f"apartamente-{rooms}-camere" if rooms > 1 else "apartamente-1-camera"
            base_url = f"https://www.publi24.ro/anunturi/imobiliare/de-vanzare/apartamente/{room_slug}/bucuresti/sector-{sector}/"
            # Publi24 foloseste parametri diferiti uneori, dar url-ul de baza e solid
            # Parametrii de pret se pun in URL de obicei
            query_params = f"?minprice={price_min}&maxprice={price_max}"
            start_url = base_url + query_params
            
            print(f"1. Accesare URL: {start_url}")
            page.goto(start_url, timeout=60000)
            
            # Gestionare Cookie (daca apare)
            try:
                page.click("#onetrust-accept-btn-handler", timeout=3000)
            except:
                pass

            # Detectare paginatie
            # Cautam ultima pagina
            last_page = 1
            try:
                pagination_items = page.locator("ul.pagination li a").all()
                numbers = []
                for item in pagination_items:
                    txt = item.inner_text()
                    if txt.isdigit():
                        numbers.append(int(txt))
                if numbers:
                    last_page = max(numbers)
            except:
                pass
            
            print(f"Total pagini detectate: {last_page}")

            unique_candidates = {}

            # Iterare prin pagini
            for page_num in range(1, last_page + 1):
                if page_num > 1:
                    current_url = f"{start_url}&pag={page_num}"
                    print(f"Navigare la pagina {page_num}...")
                    page.goto(current_url)
                    page.wait_for_timeout(2000)

                # Colectare carduri din pagina curenta
                cards = page.locator("div.article-item").all()
                print(f"   -> Pagina {page_num}: {len(cards)} anunturi gasite.")

                for card in cards:
                    try:
                        # Link & Titlu
                        title_el = card.locator("h2.article-title a").first
                        if not title_el.is_visible(): continue
                        
                        link = title_el.get_attribute("href")
                        if link and not link.startswith("http"):
                            link = "https://www.publi24.ro" + link
                        
                        title = clean_text(title_el.inner_text())

                        # Pret
                        price_el = card.locator(".article-price").first
                        price_val = 0
                        if price_el.is_visible():
                            price_val = extract_price(price_el.inner_text())

                        # Locatie
                        loc_el = card.locator(".article-location").first
                        location = clean_text(loc_el.inner_text()) if loc_el.is_visible() else ""

                        # Suprafata (din card, pentru cheia unica)
                        short_info = card.locator(".article-short-info").first
                        surface_val = extract_surface(short_info.inner_text()) if short_info.is_visible() else 0

                        # Fingerprint
                        fingerprint = f"{title}_{location}_{price_val}_{surface_val}"
                        
                        if fingerprint not in unique_candidates:
                            if price_val and (price_min <= price_val <= price_max):
                                unique_candidates[fingerprint] = {
                                    "title": title, "location": location, 
                                    "price": price_val, "surface": surface_val, 
                                    "link": link, "rooms_initial": rooms
                                }
                    except:
                        continue

            print(f"2. Începe extragerea detaliată pentru {len(unique_candidates)} anunțuri...")

            # Vizitare fiecare anunt
            items = list(unique_candidates.values())
            for idx, item in enumerate(items):
                print(f"   [{idx+1}/{len(items)}] Procesare: {item['link']}")
                
                details = scrape_detail_page(context, item['link'])
                
                # Combinare date (prioritate date din detaliu)
                final_obj = {
                    'source_website': 'Publi24',
                    'title': item['title'],
                    'price': item['price'],
                    'location': item['location'],
                    'surface': details['surface'] if details['surface'] else item['surface'],
                    'link': item['link'],
                    'description': details['description'] if details['description'] else item['title'],
                    'floor': details['floor'],
                    'contact_name': details['contact_name'],
                    'phone_number': details['phone_number'],
                    'rooms': details['rooms'] if details['rooms'] else item['rooms_initial']
                }
                results_to_save.append(final_obj)

        except Exception as e:
            print(f"Eroare generală Playwright Publi24: {e}")
        finally:
            browser.close()

    # Salvare
    if results_to_save:
        print(f"Se salvează {len(results_to_save)} rezultate în DB...")
        try:
            database.insert_batch_apartments(results_to_save)
        except Exception as e:
            print(f"Eroare DB: {e}")

        wb = Workbook()
        ws = wb.active
        ws.append(["Titlu", "Descriere", "Pret", "Locatie", "Suprafata", "Etaj", "Camere", "Nume Contact", "Telefon", "Link"])
        
        for r in results_to_save:
            ws.append([
                r.get('title'), r.get('description'), r.get('price'), 
                r.get('location'), r.get('surface'), r.get('floor'), 
                r.get('rooms'), r.get('contact_name'), r.get('phone_number'), 
                r.get('link')
            ])
        
        wb.save(file_path)
        print(f"Excel generat: {file_path}")
    else:
        wb = Workbook()
        ws = wb.active
        ws.append(["Nu au fost gasite rezultate"])
        wb.save(file_path)

    return file_path