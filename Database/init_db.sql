DROP TABLE IF EXISTS scraped_apartments;

CREATE TABLE scraped_apartments (
    id SERIAL PRIMARY KEY,
    source_website VARCHAR(50) NOT NULL,
    title TEXT,
    price NUMERIC(10, 2),
    currency VARCHAR(10) DEFAULT 'EUR',
    location TEXT,
    surface NUMERIC(10, 2),
    rooms INTEGER,
    description TEXT,
    link TEXT, -- Link-ul nu mai este PK si nu mai trebuie sa fie unic strict (pastram prima varianta gasita)
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- AICI ESTE CHEIA SUCCESULUI:
    -- Unicitatea este data de combinatia Titlu + Pret + Locatie + Suprafata
    CONSTRAINT unique_ad UNIQUE (title, price, location, surface)
);

CREATE INDEX IF NOT EXISTS idx_price ON scraped_apartments(price);
CREATE INDEX IF NOT EXISTS idx_location ON scraped_apartments(location);