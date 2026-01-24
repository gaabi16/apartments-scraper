from selenium import webdriver
from bs4 import BeautifulSoup
from openpyxl import Workbook
import tempfile
import os
import time
import re

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    # Uncomment next line to run headless (without visible window)
    # options.add_argument("--headless") 
    return webdriver.Chrome(options=options)


def clean(text):
    if not text:
        return ""
    return " ".join(text.replace("\n", " ").split())


def extract_first_price(price_text):
    if not price_text:
        return None
    # Curatare formatare (ex: 75.000 EUR)
    text = price_text.replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
    match = re.search(r"\d+(\.\d+)?", text)
    return float(match.group()) if match else None


def scrape_imobiliare(rooms, price_min, price_max):
    driver = get_driver()
    
    # Constructie URL Dinamic
    # Logic: Daca rooms=1 -> url-ul e de obicei 'vanzare-garsoniere', altfel 'vanzare-apartamente' + nr camere
    # Totusi, pe Imobiliare.ro ruta /vanzare-apartamente/bucuresti/sector-1/1-camera functioneaza de obicei
    
    room_str = f"{rooms}-camere" if rooms > 1 else "1-camera"
    
    # URL de baza
    # floor param: pastram logica originala (fara parter si ultimul etaj)
    # price param: format min-max
    base_url = f"https://www.imobiliare.ro/vanzare-apartamente/bucuresti/sector-1/{room_str}"
    params = f"?price={price_min}-{price_max}&floor=1%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%2Cabove-10%2Cexcluded-last-floor"
    
    full_url = base_url + params
    print(f"Accessing Imobiliare URL: {full_url}")
    
    driver.get(full_url)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    results = []
    # Selectoarele CSS pot varia, pastram logica din fisierul original
    cards = soup.select('div[id^="listing-"]')

    for card in cards:
        try:
            title = clean(card.select_one("span.relative").get_text(strip=True))
            price = clean(card.select_one('[data-cy="card-price"]').get_text(strip=True))
            link_el = card.select_one('a[data-cy="listing-information-link"]')
            link = "https://www.imobiliare.ro" + link_el["href"] if link_el else ""

            zona_el = card.select_one("p.w-full.truncate.font-normal.capitalize")
            zona = clean(zona_el.get_text(strip=True)) if zona_el else ""

            # Filtrare suplimentara in Python pentru siguranta
            p_val = extract_first_price(price)
            
            # Verificam daca pretul e in range-ul cerut
            if p_val is None or (p_val >= price_min and p_val <= price_max):
                results.append([title, price, link, zona])

        except Exception as e:
            # print("Eroare parse card:", e)
            continue

    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"imobiliare_{int(time.time())}.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.append(["titlu", "pret", "link", "zona"])
    for r in results:
        ws.append(r)

    wb.save(file_path)
    return file_path