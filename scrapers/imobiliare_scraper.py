from selenium import webdriver
from bs4 import BeautifulSoup
from openpyxl import Workbook
import tempfile
import os
import time
import re

# TODO
# Filter apartments based on their description paragraph

URL_IMOBILIARE = "https://www.imobiliare.ro/vanzare-apartamente/bucuresti/sector-1/2-camere?price=50000-80000&floor=1%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%2Cabove-10%2Cexcluded-last-floor"


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


def scrape_imobiliare():
    driver = get_driver()
    driver.get(URL_IMOBILIARE)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    results = []
    cards = soup.select('div[id^="listing-"]')

    for card in cards:
        try:
            title = clean(card.select_one("span.relative").get_text(strip=True))
            price = clean(card.select_one('[data-cy="card-price"]').get_text(strip=True))
            link_el = card.select_one('a[data-cy="listing-information-link"]')
            link = "https://www.imobiliare.ro" + link_el["href"] if link_el else ""

            zona_el = card.select_one("p.w-full.truncate.font-normal.capitalize")
            zona = clean(zona_el.get_text(strip=True)) if zona_el else ""

            p_val = extract_first_price(price)
            if p_val is None or p_val <= 80000:
                results.append([title, price, link, zona])

        except:
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
