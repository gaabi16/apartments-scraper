import os
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "apartments_vatty")
DB_USER = os.getenv("DB_USER", "gabriel")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", "5432")

if DB_PASS:
    DB_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    print("WARNING: DB_PASS nu a fost găsit în .env. Se încearcă conexiune fără parolă.")
    DB_URL = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_connection():
    try:
        return psycopg2.connect(DB_URL)
    except Exception as e:
        print(f"Eroare critică la conectarea cu baza de date: {e}")
        raise e


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    sql_path = os.path.join(os.path.dirname(__file__), 'init_db.sql')
    migrate_path = os.path.join(os.path.dirname(__file__), 'migrate_v2.sql')
    for path in [sql_path, migrate_path]:
        if os.path.exists(path):
            with open(path, 'r') as f:
                cur.execute(f.read())
            conn.commit()
    print("Database initialized (checked schema).")
    cur.close()
    conn.close()


def insert_batch_apartments(apartments_list):
    if not apartments_list:
        print("Lista de apartamente este goala. Nimic de inserat în DB.")
        return 0

    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO scraped_apartments
        (source_website, title, price, location, surface, rooms, description, link, floor, contact_name, phone_number)
        VALUES %s
        ON CONFLICT (title, price, location, surface)
        DO UPDATE SET
            scraped_at = CURRENT_TIMESTAMP,
            link = EXCLUDED.link,
            description = EXCLUDED.description,
            contact_name = EXCLUDED.contact_name,
            phone_number = EXCLUDED.phone_number,
            floor = EXCLUDED.floor
    """

    values = []
    for app in apartments_list:
        values.append((
            app.get('source_website'),
            app.get('title'),
            app.get('price'),
            app.get('location'),
            app.get('surface'),
            app.get('rooms'),
            app.get('description'),
            app.get('link'),
            app.get('floor'),
            app.get('contact_name'),
            app.get('phone_number')
        ))

    inserted = 0
    try:
        execute_values(cur, query, values)
        inserted = cur.rowcount
        conn.commit()
        print(f"DB Success: {len(values)} randuri procesate/inserate.")
    except Exception as e:
        print(f"DB Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()
    return inserted


# ---------------------------------------------------------------------------
# user_filters
# ---------------------------------------------------------------------------

def get_active_filters():
    """Returnează cel mai recent set de filtre salvat de utilizator."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM user_filters ORDER BY created_at DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else {"rooms": 2, "sector": 0, "price_min": 10000, "price_max": 150000}


def save_filters(rooms, sector, price_min, price_max):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_filters (rooms, sector, price_min, price_max) VALUES (%s, %s, %s, %s) RETURNING id",
        (rooms, sector, price_min, price_max)
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return new_id


# ---------------------------------------------------------------------------
# run_log
# ---------------------------------------------------------------------------

def log_run_start(site):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO run_log (site) VALUES (%s) RETURNING id",
        (site,)
    )
    run_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return run_id


def log_run_finish(run_id, apartments_found, new_count):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE run_log SET finished_at = NOW(), apartments_found = %s, new_count = %s WHERE id = %s",
        (apartments_found, new_count, run_id)
    )
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# "nou azi" — VIEW-based diff
# ---------------------------------------------------------------------------

def ensure_new_today_view():
    """
    Creează/înlocuiește VIEW-ul new_today.
    Apartamente al căror scraped_at e azi ȘI nu aveau scraped_at ieri
    (adică sunt cu adevărat noi, nu simple re-scrape-uri).
    Strategia: comparăm pe cheia unică (title, price, location, surface).
    """
    ddl = """
    CREATE OR REPLACE VIEW new_today AS
    SELECT a.*
    FROM scraped_apartments a
    WHERE DATE(a.scraped_at) = CURRENT_DATE
      AND NOT EXISTS (
          SELECT 1 FROM scraped_apartments b
          WHERE b.title = a.title
            AND b.price = a.price
            AND b.location = a.location
            AND b.surface = a.surface
            AND DATE(b.scraped_at) < CURRENT_DATE
      )
    ORDER BY a.scraped_at DESC;
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(ddl)
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# Query-uri pentru endpoint-urile API
# ---------------------------------------------------------------------------

def query_apartments(rooms=None, sector=None, price_min=None, price_max=None,
                     page=1, per_page=20, sort_by="scraped_at", sort_dir="desc"):
    allowed_sort = {"scraped_at", "price", "surface", "rooms", "location"}
    if sort_by not in allowed_sort:
        sort_by = "scraped_at"
    sort_dir = "DESC" if sort_dir.lower() == "desc" else "ASC"

    conditions = []
    params = []

    if rooms is not None:
        conditions.append("rooms = %s")
        params.append(rooms)
    if sector is not None and sector != 0:
        conditions.append("location ILIKE %s")
        params.append(f"%sector {sector}%")
    if price_min is not None:
        conditions.append("price >= %s")
        params.append(price_min)
    if price_max is not None:
        conditions.append("price <= %s")
        params.append(price_max)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    offset = (page - 1) * per_page

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(f"SELECT COUNT(*) FROM scraped_apartments {where}", params)
    total = cur.fetchone()["count"]

    cur.execute(
        f"""SELECT id, source_website, title, price, location, surface, rooms,
                   floor, contact_name, phone_number, link, description, scraped_at
            FROM scraped_apartments {where}
            ORDER BY {sort_by} {sort_dir}
            LIMIT %s OFFSET %s""",
        params + [per_page, offset]
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()

    # scraped_at → string ISO
    for r in rows:
        if r.get("scraped_at"):
            r["scraped_at"] = r["scraped_at"].isoformat()

    return {"total": total, "page": page, "per_page": per_page, "apartments": rows}


def query_new_today(rooms=None, sector=None, price_min=None, price_max=None):
    conditions = []
    params = []

    if rooms is not None:
        conditions.append("rooms = %s")
        params.append(rooms)
    if sector is not None and sector != 0:
        conditions.append("location ILIKE %s")
        params.append(f"%sector {sector}%")
    if price_min is not None:
        conditions.append("price >= %s")
        params.append(price_min)
    if price_max is not None:
        conditions.append("price <= %s")
        params.append(price_max)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        f"""SELECT id, source_website, title, price, location, surface, rooms,
                   floor, contact_name, phone_number, link, description, scraped_at
            FROM new_today {where}""",
        params
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()

    for r in rows:
        if r.get("scraped_at"):
            r["scraped_at"] = r["scraped_at"].isoformat()

    return {"count": len(rows), "apartments": rows}
