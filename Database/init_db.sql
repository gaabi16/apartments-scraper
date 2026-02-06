CREATE TABLE IF NOT EXISTS scraped_apartments (
    id SERIAL PRIMARY KEY,
    source_website VARCHAR(50),
    title TEXT,
    price INTEGER,
    location TEXT,
    surface FLOAT,
    rooms INTEGER,
    description TEXT,
    link TEXT,
    floor VARCHAR(50),
    contact_name VARCHAR(100),
    phone_number VARCHAR(50),
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_ad UNIQUE (title, price, location, surface)
);