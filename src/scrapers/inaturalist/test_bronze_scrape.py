import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# URL de test : Le Canard colvert (Anas platyrhynchos)
TEST_URL = "https://www.inaturalist.org/taxa/6930-Anas-platyrhynchos"
OUTPUT_DIR = "data/bronze/inaturalist"

def get_driver():
    """ Configuration du driver """
    chrome_options = Options()
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=chrome_options)

def test_scrape_one_page():
    print(f"Demarrage du test de scraping BRONZE sur : {TEST_URL}")
    
    driver = get_driver()
    raw_data = {}

    try:
        driver.get(TEST_URL)

        # On attend que la div #TaxonDetail soit presente dans le DOM
        wait = WebDriverWait(driver, 15)
        main_element = wait.until(EC.presence_of_element_located((By.ID, "TaxonDetail")))
        
        # Pause pour laisser les scripts JS charger les images/cartes
        time.sleep(2)

        # Extraction brute : on recupere tout le HTML interne de la balise
        raw_html = main_element.get_attribute('outerHTML')
        
        # Texte brut pour verification rapide
        text_content = main_element.text

        # Structure de la donnee Bronze
        raw_data = {
            "url": TEST_URL,
            "scraped_at": time.time(),
            "raw_html_content": raw_html, 
            "debug_text_preview": text_content[:500] 
        }

        print("Extraction reussie.")
        print(f"Taille du HTML recupere : {len(raw_html)} caracteres")

    except Exception as e:
        print(f"Erreur lors du scraping : {e}")
    
    finally:
        driver.quit()

    # Sauvegarde
    if raw_data:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = os.path.join(OUTPUT_DIR, "test_bronze_duck.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=4)
            
        print(f"Donnees brutes sauvegardees dans : {filename}")

if __name__ == "__main__":
    test_scrape_one_page()