-- Creeaza baza de date (optional, poti folosi una existenta)
-- CREATE DATABASE apartments_db;

-- Dupa ce te conectezi la baza de date dorita, ruleaza:

CREATE TABLE IF NOT EXISTS scraped_apartments (
    id SERIAL PRIMARY KEY,
    source_website VARCHAR(50) NOT NULL, -- ex: 'Imobiliare', 'Publi24'
    title TEXT,
    price NUMERIC(10, 2), -- Stocam pretul numeric pentru filtre
    currency VARCHAR(10) DEFAULT 'EUR',
    location TEXT,
    surface NUMERIC(10, 2), -- Suprafata in mp
    rooms INTEGER,
    description TEXT,
    link TEXT UNIQUE, -- Evitam duplicatele pe baza link-ului
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraint pentru a nu insera duplicate (ignora sau updateaza)
    CONSTRAINT unique_link_constraint UNIQUE (link)
);

-- Index pentru cautari rapide dupa pret si zona
CREATE INDEX idx_price ON scraped_apartments(price);
CREATE INDEX idx_location ON scraped_apartments(location);