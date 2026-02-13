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
    # Romimo format: "74 500 EUR" -> 74500
    # Eliminam spatiile si punctele
    text = text.replace(" ", "").replace(".", "")
    digits = re.sub(r'[^\d]', '', text)
    if not digits: return 0
    return int(digits)

def extract_surface_from_text(text):
    if not text: return 0.0
    text = text.replace(",", ".")
    match = re.search(r'(\d+(?:[.]\d+)?)\s*(?:m|mp)', text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except:
            return 0.0
    return 0.0

def scrape_detail_page(context, url):
    """
    Intră pe pagina anunțului și ia toate detaliile conform structurii HTML Romimo.
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
        # Timeout generos pentru incarcare
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        # Pauza aleatorie pentru a simula comportament uman
        page.wait_for_timeout(random.randint(1000, 2000))

        # 1. Titlu
        try:
            title_el = page.locator(".detail-title h1").first
            if title_el.is_visible():
                data["title"] = clean_text(title_el.inner_text())
        except:
            pass
            
        # 2. Pret
        try:
            price_el = page.locator(".product-price span").first
            if price_el.is_visible():
                data["price"] = extract_price(price_el.inner_text())
        except:
            pass
            
        # 3. Locatie (Breadcrumbs sau zona info)
        try:
            # Luam locatia din .detail-info
            loc_container = page.locator(".detail-info .medium-5 p").first
            if loc_container.is_visible():
                data["location"] = clean_text(loc_container.inner_text())
        except:
            pass

        # 4. Descriere
        try:
            desc_el = page.locator(".article-description").first
            if desc_el.is_visible():
                data["description"] = clean_text(desc_el.inner_text())
        except:
            pass

        # 5. Specificatii (Suprafata, Camere, Etaj) din tabelul .article-attributes
        try:
            attribute_items = page.locator(".article-attributes .attribute-item").all()
            for item in attribute_items:
                label = item.locator(".attribute-label").inner_text().lower()
                value = item.locator(".attribute-value").inner_text()
                
                if "suprafata" in label:
                    data["surface"] = extract_surface_from_text(value)
                elif "camere" in label:
                    nums = re.search(r'\d+', value)
                    if nums:
                        data["rooms"] = int(nums.group(0))
                elif "etaj" in label:
                    data["floor"] = clean_text(value)
        except:
            pass

        # 6. Contact Name (User Profile)
        try:
            user_el = page.locator(".user-profile-name a").first
            if user_el.is_visible():
                data["contact_name"] = clean_text(user_el.inner_text())
        except:
            pass

        # 7. Telefon (Incercam click pe buton)
        try:
            phone_btn = page.locator(".btn-show-phone").first
            if phone_btn.is_visible():
                phone_btn.click()
                page.wait_for_timeout(1000)
                
                # Pe Romimo telefonul poate veni ca text sau imagine
                phone_box = page.locator(".telnumber").first
                if phone_box.is_visible():
                    txt = phone_box.inner_text()
                    if txt and len(txt) > 3:
                        data["phone_number"] = clean_text(txt)
                    else:
                        # Daca e imagine, marcam ca exista
                        data["phone_number"] = "Telefon disponibil (imagine)"
        except:
            pass

    except Exception as e:
        print(f"Eroare parsing pagina detaliu {url}: {e}")
    finally:
        page.close()

    return data

def scrape_romimo(rooms, price_min, price_max, sector):
    # Setup Fisier Excel
    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"romimo_s{sector}_{int(time.time())}.xlsx")
    
    results_to_save = []

    with sync_playwright() as p:
        print("Lansare browser Romimo (Playwright)...")
        # Headless=False pentru a vedea procesul (pune True pentru productie)
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        
        # Deschidem pagina principala de cautare
        page = context.new_page()

        try:
            # Constructie URL
            room_slug = f"apartamente-{rooms}-camere" if rooms > 1 else "apartamente-1-camera"
            base_url = f"https://www.romimo.ro/apartamente/{room_slug}/vanzare/bucuresti/sector-{sector}/"
            start_url = f"{base_url}?minprice={price_min}&maxprice={price_max}"
            
            print(f"1. Accesare URL Lista: {start_url}")
            page.goto(start_url, timeout=60000)
            
            # Acceptam cookies daca apar
            try:
                page.locator("button#onetrust-accept-btn-handler").click(timeout=3000)
            except:
                pass

            # --- PARTEA 1: Colectare Link-uri Unice ---
            unique_links = set()
            
            # Iterează prin pagini pentru a colecta link-uri
            # Pentru demo, limităm la primele 5 pagini, dar poți crește numărul
            max_pages_scan = 5
            
            for i in range(1, max_pages_scan + 1):
                if i > 1:
                    current_url = f"{start_url}&pag={i}"
                    print(f"   -> Navigare pagina {i}: {current_url}")
                    page.goto(current_url, timeout=30000)
                    page.wait_for_timeout(2000)

                # Scroll usor pentru a incarca lazy images/elements
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(500)
                
                # Selectori link-uri (h2 sau h3 in functie de design)
                # Pe Romimo titlurile sunt de obicei in h2.article-title sau h3 a
                links_elements = page.locator("h2.article-title a, h3 a.maincolor").all()
                
                found_on_page = 0
                for link_el in links_elements:
                    href = link_el.get_attribute("href")
                    if href and "anunt" in href: # Filtru simplu sa fim siguri ca e anunt
                        if not href.startswith("http"):
                            href = "https://www.romimo.ro" + href
                        unique_links.add(href)
                        found_on_page += 1
                
                print(f"   -> Pagina {i}: gasite {found_on_page} anunturi.")
                
                # Dacă nu găsim nimic pe pagină, ne oprim
                if found_on_page == 0:
                    print("   Nu s-au mai gasit anunturi. Stop paginatie.")
                    break

            print(f"Total anunturi unice colectate: {len(unique_links)}")

            # --- PARTEA 2: Procesare Fiecare Anunt (Deep Scraping) ---
            print("2. Incep procesarea detaliata a anunturilor...")
            
            for idx, link in enumerate(unique_links):
                print(f"   [{idx+1}/{len(unique_links)}] Scraping detaliu: {link}")
                
                details = scrape_detail_page(context, link)
                
                # Validare minima (măcar titlu să aibă)
                if not details["title"]:
                    continue

                # Construim obiectul final
                # Daca scraperul nu a gasit camere in detaliu, folosim ce am cerut in filtru
                final_rooms = details['rooms'] if details['rooms'] else rooms

                final_obj = {
                    'source_website': 'Romimo',
                    'title': details['title'],
                    'price': details['price'],
                    'location': details['location'],
                    'surface': details['surface'],
                    'link': link,
                    'description': details['description'],
                    'floor': details['floor'],
                    'contact_name': details['contact_name'],
                    'phone_number': details['phone_number'],
                    'rooms': final_rooms
                }
                results_to_save.append(final_obj)

        except Exception as e:
            print(f"Eroare Generala Romimo Scraper: {e}")
        finally:
            browser.close()

    # Salvare Rezultate
    if results_to_save:
        print(f"Se salveaza {len(results_to_save)} anunturi in DB...")
        try:
            database.insert_batch_apartments(results_to_save)
        except Exception as e:
            print(f"Eroare la salvare DB: {e}")

        # Generare Excel
        wb = Workbook()
        ws = wb.active
        ws.append(["Titlu", "Descriere", "Pret", "Locatie", "Suprafata", "Etaj", "Camere", "Nume Contact", "Telefon", "Link"])
        
        for r in results_to_save:
            ws.append([
                r['title'], 
                r['description'], 
                r['price'], 
                r['location'], 
                r['surface'],
                r['floor'], 
                r['rooms'], 
                r['contact_name'], 
                r['phone_number'], 
                r['link']
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