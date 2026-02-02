-- TABEL: scraped_apartments
-- Structura actualizata: LINK este Primary Key (fara coloana ID)

CREATE TABLE IF NOT EXISTS scraped_apartments (
    link TEXT PRIMARY KEY, -- Link devine identificatorul unic principal
    source_website VARCHAR(50) NOT NULL, -- ex: 'Imobiliare', 'Publi24'
    title TEXT,
    price NUMERIC(10, 2),
    currency VARCHAR(10) DEFAULT 'EUR',
    location TEXT,
    surface NUMERIC(10, 2),
    rooms INTEGER,
    description TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexuri pentru performanta la filtrare
CREATE INDEX IF NOT EXISTS idx_price ON scraped_apartments(price);
CREATE INDEX IF NOT EXISTS idx_location ON scraped_apartments(location);