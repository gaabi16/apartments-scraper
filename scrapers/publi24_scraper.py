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
    # Curata spatii multiple si caractere invizibile
    cleaned = " ".join(text.replace("\n", " ").split())
    return cleaned.strip() if cleaned else None

def extract_price(text):
    if not text: return 0
    # Publi24: "78 900 EUR" -> 78900
    text = text.replace(" ", "").replace(".", "")
    digits = re.sub(r'[^\d]', '', text)
    if not digits: return 0
    return int(digits)

def extract_surface(text):
    if not text: return 0.0
    # Format: "50 m2" sau "50,5 mp"
    text = text.replace(",", ".")
    match = re.search(r'(\d+(?:[.]\d+)?)\s*(?:m|mp)', text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except:
            return 0.0
    # Fallback doar cifre
    digits = re.search(r'(\d+)', text)
    if digits:
        return float(digits.group(1))
    return 0.0

def scrape_detail_page(context, url):
    """
    Intră pe pagina anunțului și ia toate detaliile.
    """
    data = {
        "title": None,
        "price": 0,
        "location": None,
        "description": None,
        "floor": None,
        "contact_name": None,
        "phone_number": None,
        "rooms": None,
        "surface": 0.0
    }
    
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(random.randint(1000, 2000))

        # 1. Titlu & Pret & Locatie (Le luam direct din pagina detaliu pt siguranta)
        try:
            # Titlu
            title_el = page.locator("h1").first
            if title_el.is_visible():
                data["title"] = clean_text(title_el.inner_text())
            
            # Pret
            price_el = page.locator(".product-price span").first
            if price_el.is_visible():
                data["price"] = extract_price(price_el.inner_text())
            
            # Locatie (Breadcrumbs sau text locatie)
            # Cautam in .detail-info sau breadcrumbs
            loc_el = page.locator(".detail-info a[href*='sector']").first
            if loc_el.is_visible():
                data["location"] = f"Bucuresti, {clean_text(loc_el.inner_text())}"
            else:
                data["location"] = "Bucuresti"
        except:
            pass

        # 2. Telefon
        try:
            phone_btn = page.locator(".btn-show-phone").first
            if phone_btn.is_visible():
                phone_btn.click()
                page.wait_for_timeout(1000)
                
                # Verificam daca e text
                phone_box = page.locator(".telnumber").first
                # Pe Publi24 telefonul e des imagine (background-image). 
                # Playwright nu poate citi text din imagine. 
                # Luam textul doar daca exista fizic.
                txt = phone_box.inner_text()
                if txt and len(txt) > 5:
                    data["phone_number"] = clean_text(txt)
        except:
            pass

        # 3. Descriere
        try:
            desc_el = page.locator(".article-description").first
            if desc_el.is_visible():
                data["description"] = clean_text(desc_el.inner_text())
        except:
            pass

        # 4. Specificatii (Etaj, Camere, Suprafata)
        try:
            # Iteram prin randurile din tabelul de specificatii
            specs = page.locator(".article-attributes .attribute-item").all()
            for spec in specs:
                label = spec.locator(".attribute-label").inner_text().lower()
                val = spec.locator(".attribute-value").inner_text()
                
                if "etaj" in label:
                    data["floor"] = clean_text(val)
                elif "camere" in label:
                    nums = re.search(r'\d+', val)
                    if nums:
                        data["rooms"] = int(nums.group(0))
                elif "suprafata" in label:
                    data["surface"] = extract_surface(val)
        except:
            pass

        # 5. Contact
        try:
            user_el = page.locator(".user-profile-name").first
            if user_el.is_visible():
                data["contact_name"] = clean_text(user_el.inner_text())
        except:
            pass

    except Exception as e:
        print(f"Eroare pe pagina {url}: {e}")
    finally:
        page.close()

    return data

def scrape_publi24(rooms, price_min, price_max, sector):
    # Setup Fisier Excel
    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"publi24_s{sector}_{int(time.time())}.xlsx")
    
    results_to_save = []

    with sync_playwright() as p:
        print("Lansare browser Publi24 (Infinite Scroll)...")
        # Headless=True recomandat pentru stabilitate, False pentru debug
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()

        try:
            # 1. Navigare la lista
            room_slug = f"apartamente-{rooms}-camere" if rooms > 1 else "apartamente-1-camera"
            base_url = f"https://www.publi24.ro/anunturi/imobiliare/de-vanzare/apartamente/{room_slug}/bucuresti/sector-{sector}/"
            start_url = f"{base_url}?minprice={price_min}&maxprice={price_max}"
            
            print(f"1. Accesare URL: {start_url}")
            page.goto(start_url, timeout=60000)
            
            # Accept cookie
            try:
                page.locator("button#onetrust-accept-btn-handler").click(timeout=3000)
            except:
                pass

            # 2. INFINITE SCROLL LOGIC
            print("2. Derulare pagină pentru încărcare anunțuri...")
            
            last_height = page.evaluate("document.body.scrollHeight")
            no_change_count = 0
            
            while True:
                # Scroll până jos
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
                # Așteptăm să se încarce conținutul (Publi24 poate fi lent)
                page.wait_for_timeout(3000)
                
                new_height = page.evaluate("document.body.scrollHeight")
                
                # Verificăm dacă s-a modificat înălțimea paginii
                if new_height == last_height:
                    no_change_count += 1
                    
                    # Încercăm să vedem dacă există buton de "Vezi mai multe"
                    try:
                        load_more_btn = page.locator("a.btn-load-more, button.btn-load-more").first
                        if load_more_btn.is_visible():
                            print("   -> Click pe butonul 'Vezi mai multe'...")
                            load_more_btn.click()
                            page.wait_for_timeout(3000)
                            no_change_count = 0 # Resetăm contorul dacă am găsit buton
                            new_height = page.evaluate("document.body.scrollHeight")
                    except:
                        pass
                    
                    if no_change_count >= 3:
                        print("   -> S-a atins finalul listei (fără modificări de 3 ori).")
                        break
                else:
                    no_change_count = 0
                    # Afișăm progresul vizual
                    count = page.locator("h2.article-title, h3.article-title").count()
                    print(f"   -> Anunțuri încărcate vizual: {count}")
                
                last_height = new_height

            # 3. Colectare Link-uri
            print("3. Colectare link-uri unice...")
            unique_links = set()
            
            # Selectori posibili pentru carduri
            links_elements = page.locator("h2.article-title a, h3.article-title a").all()
            
            if not links_elements:
                # Varianta Grid view
                links_elements = page.locator("ul.listing-blocks li h3 a").all()

            for link_el in links_elements:
                href = link_el.get_attribute("href")
                if href:
                    if not href.startswith("http"):
                        href = "https://www.publi24.ro" + href
                    unique_links.add(href)

            print(f"4. Incep procesarea a {len(unique_links)} anunturi unice...")

            # 4. Deep Scraping
            for idx, link in enumerate(unique_links):
                print(f"   [{idx+1}/{len(unique_links)}] Procesare: {link}")
                
                details = scrape_detail_page(context, link)
                
                if not details["title"]:
                    continue 

                final_obj = {
                    'source_website': 'Publi24',
                    'title': details['title'],
                    'price': details['price'],
                    'location': details['location'],
                    'surface': details['surface'],
                    'link': link,
                    'description': details['description'],
                    'floor': details['floor'],
                    'contact_name': details['contact_name'],
                    'phone_number': details['phone_number'],
                    'rooms': details['rooms'] if details['rooms'] else rooms
                }
                results_to_save.append(final_obj)

        except Exception as e:
            print(f"Eroare Generala: {e}")
        finally:
            browser.close()

    # 5. Salvare
    if results_to_save:
        print(f"Se salveaza {len(results_to_save)} anunturi in DB...")
        try:
            database.insert_batch_apartments(results_to_save)
        except Exception as e:
            print(f"Eroare la salvare DB: {e}")

        wb = Workbook()
        ws = wb.active
        ws.append(["Titlu", "Descriere", "Pret", "Locatie", "Suprafata", "Etaj", "Camere", "Nume Contact", "Telefon", "Link"])
        
        for r in results_to_save:
            ws.append([
                r['title'], r['description'], r['price'], r['location'], r['surface'],
                r['floor'], r['rooms'], r['contact_name'], r['phone_number'], r['link']
            ])
        
        wb.save(file_path)
        print(f"Excel salvat: {file_path}")
    else:
        print("Nu au fost gasite rezultate.")
        wb = Workbook()
        ws = wb.active
        ws.append(["Nu au fost gasite rezultate."])
        wb.save(file_path)

    return file_path