const BACKEND_URL = 'https://nonpractically-unlamed-kesha.ngrok-free.dev';

// Headers pentru ngrok
const fetchOptions = {
    headers: {
        'ngrok-skip-browser-warning': 'true',
        'User-Agent': 'MyApp'
    }
};

function startScraping(site) {
    console.log(`Starting scraping for ${site}...`);
    
    const statusText = document.getElementById(`status_${site}`);
    const statusBadge = document.getElementById(`badge_${site}`);
    const statusIcon = document.getElementById(`icon_${site}`);
    const progressBar = document.getElementById(`progress_${site}`);
    const scrapeBtn = document.getElementById(`btn_scrape_${site}`);
    const downloadBtn = document.getElementById(`btn_download_${site}`);
    
    statusText.innerText = "Se conectează la site...";
    statusBadge.innerText = "În lucru";
    statusBadge.classList.add("running");
    statusBadge.classList.remove("finished");
    statusIcon.classList.add("spinning");
    statusIcon.classList.remove("success");
    progressBar.classList.add("active");
    
    scrapeBtn.disabled = true;
    downloadBtn.disabled = true;
    
    fetch(`${BACKEND_URL}/scrape/${site}`, fetchOptions)
        .then(response => {
            console.log('Response:', response);
            return response.json();
        })
        .then(data => {
            console.log('Data:', data);
            if (data.started) {
                statusText.innerText = "Scraping în desfășurare...";
                checkStatus(site);
            } else {
                statusText.innerText = "Scraping-ul este deja activ";
                setTimeout(() => checkStatus(site), 1000);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            statusText.innerText = "Eroare la conectarea cu backend-ul";
            resetUI(site);
        });
}

function checkStatus(site) {
    const statusText = document.getElementById(`status_${site}`);
    const statusBadge = document.getElementById(`badge_${site}`);
    const statusIcon = document.getElementById(`icon_${site}`);
    const progressBar = document.getElementById(`progress_${site}`);
    const scrapeBtn = document.getElementById(`btn_scrape_${site}`);
    const downloadBtn = document.getElementById(`btn_download_${site}`);
    
    fetch(`${BACKEND_URL}/status/${site}`, fetchOptions)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                statusText.innerText = "Eroare: " + data.error;
                resetUI(site);
                return;
            }
            
            if (data.finished) {
                statusText.innerText = "✓ Scraping terminat cu succes!";
                statusBadge.innerText = "Terminat";
                statusBadge.classList.remove("running");
                statusBadge.classList.add("finished");
                statusIcon.classList.remove("spinning");
                statusIcon.classList.add("success");
                progressBar.classList.remove("active");
                
                scrapeBtn.disabled = false;
                downloadBtn.disabled = false;
                
                const card = statusIcon.closest('.scraper-card');
                card.style.animation = 'none';
                setTimeout(() => {
                    card.style.animation = 'fadeInUp 0.6s ease-out';
                }, 10);
                
            } else if (data.running) {
                statusText.innerText = "Se extrag datele... Vă rugăm așteptați";
                setTimeout(() => checkStatus(site), 2000);
            } else {
                resetUI(site);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            statusText.innerText = "Eroare la verificarea statusului";
            resetUI(site);
        });
}

function downloadFile(site) {
    const statusText = document.getElementById(`status_${site}`);
    statusText.innerText = "Se pregătește descărcarea...";
    
    window.location.href = `${BACKEND_URL}/download/${site}`;
    
    setTimeout(() => {
        statusText.innerText = "Fișier descărcat!";
        setTimeout(() => {
            statusText.innerText = "Apasă butonul pentru a începe";
        }, 3000);
    }, 1000);
}

function resetUI(site) {
    const statusText = document.getElementById(`status_${site}`);
    const statusBadge = document.getElementById(`badge_${site}`);
    const statusIcon = document.getElementById(`icon_${site}`);
    const progressBar = document.getElementById(`progress_${site}`);
    const scrapeBtn = document.getElementById(`btn_scrape_${site}`);
    
    statusText.innerText = "Apasă butonul pentru a începe";
    statusBadge.innerText = "Gata";
    statusBadge.classList.remove("running", "finished");
    statusIcon.classList.remove("spinning", "success");
    progressBar.classList.remove("active");
    scrapeBtn.disabled = false;
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Page loaded, Backend URL:', BACKEND_URL);
    
    ['imobiliare', 'publi24', 'romimo'].forEach(site => {
        fetch(`${BACKEND_URL}/status/${site}`, fetchOptions)
            .then(response => response.json())
            .then(data => {
                console.log(`Status for ${site}:`, data);
                
                if (data.running) {
                    const statusText = document.getElementById(`status_${site}`);
                    const statusBadge = document.getElementById(`badge_${site}`);
                    const statusIcon = document.getElementById(`icon_${site}`);
                    const progressBar = document.getElementById(`progress_${site}`);
                    
                    statusText.innerText = "Scraping în desfășurare...";
                    statusBadge.innerText = "În lucru";
                    statusBadge.classList.add("running");
                    statusIcon.classList.add("spinning");
                    progressBar.classList.add("active");
                    
                    checkStatus(site);
                } else if (data.finished && data.file) {
                    const statusText = document.getElementById(`status_${site}`);
                    const statusBadge = document.getElementById(`badge_${site}`);
                    const statusIcon = document.getElementById(`icon_${site}`);
                    const downloadBtn = document.getElementById(`btn_download_${site}`);
                    
                    statusText.innerText = "✓ Scraping terminat cu succes!";
                    statusBadge.innerText = "Terminat";
                    statusBadge.classList.add("finished");
                    statusIcon.classList.add("success");
                    downloadBtn.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error checking initial status:', error);
            });
    });
});