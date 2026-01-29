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
    return webdriver.Chrome(options=options)

def clean(text):
    if not text:
        return ""
    return " ".join(text.replace("\n", " ").split())

# ----------------------------------------------------------
#   PAGINATION PARSER
# ----------------------------------------------------------

def extract_all_pages(soup):
    pagination = soup.select_one("ul.pagination")
    if not pagination:
        return [1]

    visible_pages = []
    for li in pagination.find_all("li"):
        a = li.find("a")
        if a and a.text.strip().isdigit():
            visible_pages.append(int(a.text.strip()))

    if not visible_pages:
        return [1]

    full_pages = []
    if visible_pages:
        for i in range(1, max(visible_pages) + 1):
            full_pages.append(i)
    return full_pages

# ----------------------------------------------------------
#   SCRAPE A PAGE
# ----------------------------------------------------------

def scrape_page(driver, page_number):
    time.sleep(3) 
    soup = BeautifulSoup(driver.page_source, "html.parser")
    articles = soup.select("div.article-list > div.article-item")
    results = []

    for article in articles:
        try:
            title_el = article.select_one("h2.article-title a")
            title = clean(title_el.get_text()) if title_el else ""
            link = title_el["href"] if title_el else ""

            desc_el = article.select_one("p.article-description")
            descriere = clean(desc_el.get_text()) if desc_el else ""

            loc_el = article.select_one("p.article-location span")
            zona = clean(loc_el.get_text()) if loc_el else ""

            short_info_el = article.select_one("p.article-short-info span.article-lbl-txt")
            suprafata = ""
            if short_info_el:
                match = re.search(r"(\d+)\s*m", short_info_el.get_text())
                if match:
                    suprafata = match.group(1)

            price_el = article.select_one("div.article-info span.article-price")
            pret = clean(price_el.get_text()) if price_el else ""

            results.append([title, link, descriere, zona, suprafata, pret, page_number])

        except Exception as e:
            continue

    return results

# ----------------------------------------------------------
#   MAIN SCRAPER
# ----------------------------------------------------------

def scrape_publi24(rooms, price_min, price_max, sector):
    driver = get_driver()
    
    room_slug = f"apartamente-{rooms}-camere" if rooms > 1 else "apartamente-1-camera"
    
    # Modificare: Inseram sectorul dinamic in URL
    base_url = f"https://www.publi24.ro/anunturi/imobiliare/de-vanzare/apartamente/{room_slug}/bucuresti/sector-{sector}/"
    
    query_params = f"?minprice={price_min}&maxprice={price_max}"
    
    start_url = base_url + query_params
    print(f"Accessing Publi24: {start_url}")

    driver.get(start_url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    pages = extract_all_pages(soup)

    print("Pagini găsite:", pages)

    all_results = []

    for page_number in pages:
        if page_number == 1:
            url = start_url
        else:
            url = start_url + f"&pag={page_number}"

        print(f"Scraping pagina {page_number}")
        driver.get(url)
        page_results = scrape_page(driver, page_number)
        all_results.extend(page_results)

    driver.quit()

    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"publi24_s{sector}_{int(time.time())}.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.append(["Titlu", "Link", "Descriere", "Zona", "Suprafata(mp)", "Pret", "Pagina"])

    for r in all_results:
        ws.append(r)

    wb.save(file_path)
    print("Fișier Publi24 salvat:", file_path)
    return file_path