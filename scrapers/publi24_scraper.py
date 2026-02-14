import time
import random
import re
import os
import sys
import tempfile
import concurrent.futures
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

def scrape_detail_worker(url):
    """
    Worker pentru multithreading.
    Deschide o instanță nouă de Playwright per thread pentru siguranță și procesează detaliile.
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
        "surface": 0.0,
        "link": url
    }
    
    # Fiecare thread își deschide propriul context Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(random.randint(1000, 2000))

            # 1. Titlu
            try:
                title_el = page.locator("h1").first
                if title_el.is_visible():
                    data["title"] = clean_text(title_el.inner_text())
            except: pass
            
            # 2. Pret
            try:
                price_el = page.locator(".product-price span").first
                if price_el.is_visible():
                    data["price"] = extract_price(price_el.inner_text())
            except: pass
            
            # 3. Locatie
            try:
                loc_el = page.locator(".detail-info a[href*='sector']").first
                if loc_el.is_visible():
                    data["location"] = f"Bucuresti, {clean_text(loc_el.inner_text())}"
                else:
                    data["location"] = "Bucuresti"
            except: pass

            # 4. Telefon
            try:
                phone_btn = page.locator(".btn-show-phone").first
                if phone_btn.is_visible():
                    phone_btn.click()
                    page.wait_for_timeout(1000)
                    
                    phone_box = page.locator(".telnumber").first
                    txt = phone_box.inner_text()
                    if txt and len(txt) > 5:
                        data["phone_number"] = clean_text(txt)
            except: pass

            # 5. Descriere
            try:
                desc_el = page.locator(".article-description").first
                if desc_el.is_visible():
                    data["description"] = clean_text(desc_el.inner_text())
            except: pass

            # 6. Specificatii
            try:
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
            except: pass

            # 7. Contact
            try:
                user_el = page.locator(".user-profile-name").first
                if user_el.is_visible():
                    data["contact_name"] = clean_text(user_el.inner_text())
            except: pass

        except Exception as e:
            print(f"   [!] Eroare pe pagina {url}: {e}")
        finally:
            browser.close()

    return data

def scrape_publi24(rooms, price_min, price_max, sector):
    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"publi24_s{sector}_{int(time.time())}.xlsx")
    
    results_to_save = []
    unique_links = set()

    # ========================================================
    # PARTEA 1: Colectare link-uri cu Infinite Scroll
    # ========================================================
    with sync_playwright() as p:
        print("Lansare browser principal Publi24 (Infinite Scroll)...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()

        try:
            room_slug = f"apartamente-{rooms}-camere" if rooms > 1 else "apartamente-1-camera"
            base_url = f"https://www.publi24.ro/anunturi/imobiliare/de-vanzare/apartamente/{room_slug}/bucuresti/sector-{sector}/"
            start_url = f"{base_url}?minprice={price_min}&maxprice={price_max}"
            
            print(f"1. Accesare URL: {start_url}")
            page.goto(start_url, timeout=60000)
            
            try:
                page.locator("button#onetrust-accept-btn-handler").click(timeout=3000)
            except:
                pass

            print("2. Derulare pagină pentru încărcare anunțuri...")
            last_height = page.evaluate("document.body.scrollHeight")
            no_change_count = 0
            
            while True:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(3000)
                new_height = page.evaluate("document.body.scrollHeight")
                
                if new_height == last_height:
                    no_change_count += 1
                    try:
                        load_more_btn = page.locator("a.btn-load-more, button.btn-load-more").first
                        if load_more_btn.is_visible():
                            load_more_btn.click()
                            page.wait_for_timeout(3000)
                            no_change_count = 0
                            new_height = page.evaluate("document.body.scrollHeight")
                    except:
                        pass
                    
                    if no_change_count >= 3:
                        print("   -> S-a atins finalul listei.")
                        break
                else:
                    no_change_count = 0
                    count = page.locator("h2.article-title, h3.article-title").count()
                    print(f"   -> Anunțuri încărcate vizual: {count}")
                
                last_height = new_height

            print("3. Colectare link-uri unice...")
            links_elements = page.locator("h2.article-title a, h3.article-title a").all()
            if not links_elements:
                links_elements = page.locator("ul.listing-blocks li h3 a").all()

            for link_el in links_elements:
                href = link_el.get_attribute("href")
                if href:
                    if not href.startswith("http"):
                        href = "https://www.publi24.ro" + href
                    unique_links.add(href)

        except Exception as e:
            print(f"Eroare Generala la listare: {e}")
        finally:
            browser.close()

    print(f"4. Încep procesarea a {len(unique_links)} anunțuri unice în PARALEL (Multithreading)...")

    # ========================================================
    # PARTEA 2: Deep Scraping folosind Multithreading
    # ========================================================
    # Folosim 5 thread-uri pentru a nu sugruma sistemul cu browsere
    max_threads = 5 
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        # Pregatim lista de task-uri
        future_to_url = {executor.submit(scrape_detail_worker, url): url for url in unique_links}
        
        # Procesam rezultatele pe masura ce fiecare thread termina treaba
        for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
            url = future_to_url[future]
            try:
                details = future.result()
                
                if details["title"]:
                    final_obj = {
                        'source_website': 'Publi24',
                        'title': details['title'],
                        'price': details['price'],
                        'location': details['location'],
                        'surface': details['surface'],
                        'link': details['link'], # preluat direct din data returnata de worker
                        'description': details['description'],
                        'floor': details['floor'],
                        'contact_name': details['contact_name'],
                        'phone_number': details['phone_number'],
                        'rooms': details['rooms'] if details['rooms'] else rooms
                    }
                    results_to_save.append(final_obj)
                    
                print(f"   [{i+1}/{len(unique_links)}] Terminat: {url}")
            except Exception as exc:
                print(f"   Eroare la procesarea {url}: {exc}")

    # ========================================================
    # PARTEA 3: Salvare
    # ========================================================
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