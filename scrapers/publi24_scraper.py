from selenium import webdriver
from bs4 import BeautifulSoup
from openpyxl import Workbook
import tempfile
import os
import time
import re

URL_PUBLI24 = "https://www.publi24.ro/anunturi/imobiliare/de-vanzare/apartamente/apartamente-2-camere/bucuresti/sector-1/?q=apartament+2+camere&maxprice=81000"


def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
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


def scrape_publi24():
    driver = get_driver()
    driver.get(URL_PUBLI24)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    ads = soup.select("div.listing")

    results = []

    for ad in ads:
        try:
            title_el = ad.select_one("h2 a")
            title = clean(title_el.get_text()) if title_el else ""

            link = "https://www.publi24.ro" + title_el["href"] if title_el else ""

            price_el = ad.select_one(".price")
            price = clean(price_el.get_text()) if price_el else ""

            zona_el = ad.select_one(".location span")
            zona = clean(zona_el.get_text()) if zona_el else ""

            price_val = extract_first_price(price)

            if price_val is None or price_val <= 81000:
                results.append([title, price, link, zona])

        except:
            continue

    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"publi24_{int(time.time())}.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.append(["titlu", "pret", "link", "zona"])

    for r in results:
        ws.append(r)

    wb.save(file_path)
    return file_path
