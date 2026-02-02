-- SCRIPT MIGRARE: Schimbare PK din ID in LINK
-- Ruleaza acest script o singura data pentru a actualiza structura existenta.

BEGIN;

-- 1. Stergem constrangerea veche de Primary Key (asociata cu id)
ALTER TABLE scraped_apartments DROP CONSTRAINT IF EXISTS scraped_apartments_pkey;

-- 2. Stergem coloana 'id' deoarece link-ul va fi identificatorul unic
ALTER TABLE scraped_apartments DROP COLUMN IF EXISTS id;

-- 3. Setam coloana 'link' ca noua Primary Key
-- (Aceasta operatiune va esua daca exista duplicate in link, dar scraperul nostru a prevenit asta)
ALTER TABLE scraped_apartments ADD PRIMARY KEY (link);

COMMIT;