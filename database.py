import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv  # Import nou

# Incarca variabilele din fisierul .env
load_dotenv()

# --- CONFIGURARE BAZA DE DATE (citite din mediu) ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS", "") # Default string gol daca nu exista
DB_PORT = os.getenv("DB_PORT", "5432")

def get_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Eroare la conectarea DB: {e}")
        return None

def insert_apartment(data):
    """
    data trebuie sa fie un dictionar cu cheile:
    source_website, title, price, location, surface, rooms, description, link
    """
    conn = get_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        
        # Folosim ON CONFLICT (link) DO UPDATE pentru a actualiza pretul daca anuntul exista deja
        insert_query = """
        INSERT INTO scraped_apartments 
        (source_website, title, price, location, surface, rooms, description, link)
        VALUES (%(source)s, %(title)s, %(price)s, %(loc)s, %(surf)s, %(rooms)s, %(desc)s, %(link)s)
        ON CONFLICT (link) DO UPDATE SET
            price = EXCLUDED.price,
            scraped_at = CURRENT_TIMESTAMP;
        """
        
        # Pregatire date
        params = {
            'source': data.get('source_website'),
            'title': data.get('title'),
            'price': data.get('price'), 
            'loc': data.get('location'),
            'surf': data.get('surface'), 
            'rooms': data.get('rooms'),
            'desc': data.get('description', ''),
            'link': data.get('link')
        }
        
        cur.execute(insert_query, params)
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Eroare la inserare in DB: {e}")
    finally:
        if conn:
            conn.close()

def insert_batch_apartments(apartments_list):
    """Insereaza o lista de dictionare."""
    for apt in apartments_list:
        insert_apartment(apt)