import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Încarcă variabilele din fișierul .env aflat în rădăcina proiectului
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

# Preluare date din .env
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "apartments_vatty")
DB_USER = os.getenv("DB_USER", "gabriel")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", "5432")

# Construire URL conexiune
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
    # Calea relativa catre init_db.sql
    sql_path = os.path.join(os.path.dirname(__file__), 'init_db.sql')
    if os.path.exists(sql_path):
        with open(sql_path, 'r') as f:
            cur.execute(f.read())
        conn.commit()
        print("Database initialized (checked schema).")
    else:
        print("Warning: init_db.sql not found, skipping init.")
    cur.close()
    conn.close()

def insert_batch_apartments(apartments_list):
    """
    Insereaza date in scraped_apartments. 
    Gestioneaza cheile lipsa prin .get() care returneaza None default.
    """
    if not apartments_list:
        print("Lista de apartamente este goala. Nimic de inserat în DB.")
        return

    conn = get_connection()
    cur = conn.cursor()

    # Query-ul trebuie sa se potriveasca cu coloanele din DB
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

    try:
        execute_values(cur, query, values)
        conn.commit()
        print(f"DB Success: {len(values)} randuri procesate/inserate.")
    except Exception as e:
        print(f"DB Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()