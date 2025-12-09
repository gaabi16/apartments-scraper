# Rezumat: Scraper + Frontend

## Obiectiv
- Rulez scrapingul local, pe PC-ul meu.  
- Salvez rezultatele intr-o baza de date PostgreSQL/Supabase.  
- Creez un frontend static (HTML/CSS/JS) pe GitHub Pages care afiseaza datele.  
- Ceilalti utilizatori pot vedea doar rezultatele, fara sa poata rula scrapingul.

## Structura
1. **Scraper Python**  
   - Ruleaza local.  
   - Pot completa manual captcha daca apare.  
   - Trimite rezultatele in baza de date.

2. **Baza de date PostgreSQL**  
   - Stochez anunturile.  
   - Frontend-ul are acces doar read-only.  

3. **Frontend HTML/CSS/JS**  
   - Citeste datele din API-ul bazei de date.  
   - Este static si gazduit pe GitHub Pages.  

## Flux
1. Rulez scraperul local.  
2. Datele se trimit in baza de date.  
3. Frontend-ul afiseaza datele.  
4. Utilizatorii nu pot porni scrapingul.

## Avantaje
- Pot folosi GitHub Pages pentru frontend static.  
- Scrapingul ramane local si securizat.  
- Datele sunt centralizate si accesibile doar celor autorizati.
