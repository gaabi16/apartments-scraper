from selenium import webdriver
from bs4 import BeautifulSoup
from openpyxl import Workbook
import tempfile
import os
import time
import re

# TODO
# Filter apartments based on their description paragraph

URL_ROMIMO = "https://www.romimo.ro/apartamente/apartamente-2-camere/vanzare/bucuresti/sector-1/?minprice=10000&maxprice=81000"

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=options)


def clean(text):
    if not text:
        return ""
    return " ".join(text.replace("\n", " ").split())


def extract_price(price_text):
    """Extract numeric price from text like '73 000 EUR'"""
    if not price_text:
        return ""
    # Remove EUR and clean up
    text = price_text.replace("EUR", "").replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
    match = re.search(r"\d+(\.\d+)?", text)
    return match.group() if match else price_text


def extract_surface(short_info_text):
    """Extract surface area from text like '50 m²'"""
    if not short_info_text:
        return ""
    match = re.search(r"(\d+)\s*m", short_info_text)
    return match.group(1) if match else ""


def extract_price_per_sqm(short_info_text):
    """Extract price per square meter from text like '1460 EUR/m²'"""
    if not short_info_text:
        return ""
    match = re.search(r"(\d+)\s*EUR/m", short_info_text)
    return match.group(1) if match else ""


def extract_all_pages(soup):
    """Extract all page numbers from pagination"""
    pagination = soup.select_one("ul.pagination")
    if not pagination:
        return [1]
    
    # Find all page links
    page_numbers = []
    for li in pagination.find_all("li"):
        a = li.find("a")
        if a and a.text.strip().isdigit():
            page_numbers.append(int(a.text.strip()))
    
    if not page_numbers:
        return [1]
    
    # Return range from 1 to max page number
    return list(range(1, max(page_numbers) + 1))


def scrape_page(driver, page_number):
    """Scrape all apartments from current page"""
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    article_list = soup.select_one("div.article-list")
    if not article_list:
        print(f"Nu s-a găsit article-list pe pagina {page_number}")
        return []
    
    articles = article_list.select("div.article-item")
    results = []
    
    for article in articles:
        try:
            # Extract title
            title_el = article.select_one("h2.article-title a")
            title = clean(title_el.get_text()) if title_el else ""
            link = title_el["href"] if title_el and title_el.has_attr("href") else ""
            
            # Extract description
            desc_el = article.select_one("p.article-description")
            description = clean(desc_el.get_text()) if desc_el else ""
            
            # Extract location
            loc_el = article.select_one("p.article-location span")
            location = clean(loc_el.get_text()) if loc_el else ""
            
            # Extract price
            price_el = article.select_one("span.article-price")
            price_raw = clean(price_el.get_text()) if price_el else ""
            price = extract_price(price_raw)
            
            # Extract surface and price per sqm
            short_info_el = article.select_one("p.article-short-info span.article-lbl-txt")
            short_info_text = short_info_el.get_text() if short_info_el else ""
            
            surface = extract_surface(short_info_text)
            price_per_sqm = extract_price_per_sqm(short_info_text)
            
            # Extract date
            date_el = article.select_one("p.article-date span")
            date = clean(date_el.get_text()) if date_el else ""
            
            results.append([
                title,
                price,
                price_per_sqm,
                surface,
                location,
                description,
                date,
                link,
                page_number
            ])
            
        except Exception as e:
            print(f"Eroare la procesarea articolului: {e}")
            continue
    
    return results


def scrape_romimo():
    """Main scraper function"""
    driver = get_driver()
    driver.get(URL_ROMIMO)
    time.sleep(4)
    
    # Get all page numbers
    soup = BeautifulSoup(driver.page_source, "html.parser")
    pages = extract_all_pages(soup)
    
    print(f"Pagini găsite: {pages}")
    
    all_results = []
    
    # Scrape each page
    for page_number in pages:
        if page_number == 1:
            url = URL_ROMIMO
        else:
            url = URL_ROMIMO + f"&pag={page_number}"
        
        print(f"Scraping pagina {page_number}: {url}")
        driver.get(url)
        page_results = scrape_page(driver, page_number)
        all_results.extend(page_results)
        print(f"  → Găsite {len(page_results)} apartamente")
    
    driver.quit()
    
    # Save to Excel
    tmp = tempfile.gettempdir()
    file_path = os.path.join(tmp, f"romimo_{int(time.time())}.xlsx")
    
    wb = Workbook()
    ws = wb.active
    ws.append([
        "Titlu",
        "Pret (EUR)",
        "Pret/mp (EUR)",
        "Suprafata (mp)",
        "Locatie",
        "Descriere",
        "Data",
        "Link",
        "Pagina"
    ])
    
    for r in all_results:
        ws.append(r)
    
    wb.save(file_path)
    print(f"Fișier Romimo salvat: {file_path}")
    print(f"Total apartamente: {len(all_results)}")
    
    return file_path


if __name__ == "__main__":
    scrape_romimo()