import os
import psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlparse

# Configurare conexiune (presupunem URL-ul din environment sau default)
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/apartments_db")

def get_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # Citim fisierul SQL, calea relativa
    sql_path = os.path.join(os.path.dirname(__file__), 'init_db.sql')
    with open(sql_path, 'r') as f:
        cur.execute(f.read())
    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized.")

def insert_batch_apartments(apartments_list):
    """
    Insereaza o lista de dictionare in baza de date.
    Foloseste ON CONFLICT DO UPDATE pentru a evita duplicatele,
    dar actualizeaza timestamp-ul si link-ul.
    """
    if not apartments_list:
        return

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
            phone_number = EXCLUDED.phone_number
    """

    # Pregatim valorile pentru executie in batch
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
        print(f"Successfully inserted/updated {len(values)} records.")
    except Exception as e:
        print(f"Database Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()