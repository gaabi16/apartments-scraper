-- TABEL: scraped_apartments
-- Ruleaza acest script conectat la baza de date 'apartments_vatty'

CREATE TABLE IF NOT EXISTS scraped_apartments (
    id SERIAL PRIMARY KEY,
    source_website VARCHAR(50) NOT NULL, -- ex: 'Imobiliare', 'Publi24'
    title TEXT,
    price NUMERIC(10, 2), -- Pret numeric pentru calcule
    currency VARCHAR(10) DEFAULT 'EUR',
    location TEXT,
    surface NUMERIC(10, 2), -- Suprafata in mp
    rooms INTEGER,
    description TEXT,
    link TEXT UNIQUE, -- Link unic pentru a preveni duplicatele
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexuri pentru performanta la filtrare
CREATE INDEX IF NOT EXISTS idx_price ON scraped_apartments(price);
CREATE INDEX IF NOT EXISTS idx_location ON scraped_apartments(location);