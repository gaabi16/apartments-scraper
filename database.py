import psycopg2
from psycopg2 import sql
import os

# Configurare conexiune - MODIFICA AICI cu datele tale din pgAdmin4
DB_HOST = "localhost"
DB_NAME = "postgres"  # sau numele bazei tale, ex: apartments_db
DB_USER = "postgres"
DB_PASS = "parola_ta_pgadmin" # <-- Pune parola ta aici
DB_PORT = "5432"

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
        
        insert_query = """
        INSERT INTO scraped_apartments 
        (source_website, title, price, location, surface, rooms, description, link)
        VALUES (%(source)s, %(title)s, %(price)s, %(loc)s, %(surf)s, %(rooms)s, %(desc)s, %(link)s)
        ON CONFLICT (link) DO NOTHING;
        """
        
        # Mapping date dictionar la parametri query
        params = {
            'source': data.get('source_website'),
            'title': data.get('title'),
            'price': data.get('price'), # Trebuie sa fie float sau None
            'loc': data.get('location'),
            'surf': data.get('surface'), # Trebuie sa fie float sau None
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