"""
Scheduler zilnic: la 07:00 pornește toate scraperele cu filtrele salvate în DB.
"""
import threading
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from Database.database import (
    get_active_filters, log_run_start, log_run_finish,
    ensure_new_today_view
)
from scrapers.imobiliare_scraper import scrape_imobiliare
from scrapers.publi24_scraper import scrape_publi24
from scrapers.romimo_scraper import scrape_romimo

log = logging.getLogger(__name__)

SCRAPERS = {
    "imobiliare": scrape_imobiliare,
    "publi24": scrape_publi24,
    "romimo": scrape_romimo,
}


def _run_single(site, scraper_fn, filters):
    rooms = filters["rooms"]
    sector = filters["sector"]
    price_min = filters["price_min"]
    price_max = filters["price_max"]

    run_id = log_run_start(site)
    log.info(f"[scheduler] Start {site}: rooms={rooms}, sector={sector}, pret={price_min}-{price_max}")

    try:
        file_path = scraper_fn(rooms, price_min, price_max, sector)
        # Reconstruim view-ul după fiecare scraper finalizat
        ensure_new_today_view()

        # Citim câte apartamente noi au apărut (din view)
        from Database.database import get_connection
        from psycopg2.extras import RealDictCursor
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM scraped_apartments WHERE DATE(scraped_at) = CURRENT_DATE")
        found = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM new_today")
        new_c = cur.fetchone()[0]
        cur.close()
        conn.close()

        log_run_finish(run_id, found, new_c)
        log.info(f"[scheduler] Finished {site}: found={found}, new={new_c}, file={file_path}")
    except Exception as e:
        log.error(f"[scheduler] Eroare {site}: {e}")
        log_run_finish(run_id, 0, 0)


def run_all_scrapers():
    """Pornește toate scraperele în paralel cu filtrele active din DB."""
    filters = get_active_filters()
    log.info(f"[scheduler] Daily run — filtre: {filters}")

    ensure_new_today_view()

    threads = []
    for site, fn in SCRAPERS.items():
        t = threading.Thread(target=_run_single, args=(site, fn, filters), daemon=True)
        t.start()
        threads.append(t)

    # Nu blocăm Flask — thread-urile rulează în background


def create_scheduler():
    scheduler = BackgroundScheduler(timezone="Europe/Bucharest")
    scheduler.add_job(
        run_all_scrapers,
        trigger=CronTrigger(hour=7, minute=0, timezone="Europe/Bucharest"),
        id="daily_scrape",
        replace_existing=True,
    )
    return scheduler
