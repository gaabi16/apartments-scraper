-- Migration v2: user_filters, run_log, index on scraped_at

-- Index pe scraped_at pentru query-uri rapide per zi
CREATE INDEX IF NOT EXISTS idx_scraped_at ON scraped_apartments (scraped_at);

-- Filtrele salvate de utilizator (folosite de scheduler la rularea automată)
CREATE TABLE IF NOT EXISTS user_filters (
    id SERIAL PRIMARY KEY,
    rooms INTEGER,
    sector INTEGER,
    price_min INTEGER,
    price_max INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Log per rulare zilnică
CREATE TABLE IF NOT EXISTS run_log (
    id SERIAL PRIMARY KEY,
    run_date DATE NOT NULL DEFAULT CURRENT_DATE,
    site VARCHAR(50) NOT NULL,
    apartments_found INTEGER DEFAULT 0,
    new_count INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);

-- Inserează filtre default dacă tabelul e gol
INSERT INTO user_filters (rooms, sector, price_min, price_max)
SELECT 2, 0, 10000, 150000
WHERE NOT EXISTS (SELECT 1 FROM user_filters LIMIT 1);
