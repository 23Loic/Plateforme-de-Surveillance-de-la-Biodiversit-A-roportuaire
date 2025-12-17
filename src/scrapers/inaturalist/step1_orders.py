import time
import re
import json
import os
import sys
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.scrapers.base_scraper import BaseScraper, logger

class Step1OrderScraper(BaseScraper):
    def __init__(self):
        super().__init__(base_url="https://www.inaturalist.org", output_subfolder="0_planning")
        self.start_url = "https://www.inaturalist.org/taxa/3-Aves"

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        self.driver = webdriver.Chrome(options=chrome_options)

    def open_taxonomy_tab(self):
        """ Ouvre l'onglet Taxinomie pour charger l'arbre. """
        try:
            logger.info("Ouverture de l'onglet Taxinomie...")
            wait = WebDriverWait(self.driver, 15)
            tab_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#taxonomy-tab']")))
            self.driver.execute_script("arguments[0].click();", tab_link)
            wait.until(EC.presence_of_element_located((By.ID, "taxonomy-tab")))
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Erreur onglet : {e}")
            return False

    def extract_orders(self):
        """ Extrait les Ordres en ignorant ceux qui sont 'hidable' (éteints). """
        logger.info("Extraction des Ordres...")
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        orders = []

        container = soup.find("div", id="taxonomy-tab")
        if not container: return []

        # Recherche des balises 'taxon order'
        nodes = container.find_all("span", class_=lambda x: x and "taxon order" in x)

        for node in nodes:
            try:
                # --- FILTRE ANTI-EXTINCTION ---
                # On remonte au parent <li> pour vérifier s'il est 'hidable'
                parent_li = node.find_parent("li")
                if parent_li and parent_li.get("class"):
                    if "hidable" in parent_li.get("class"):
                        # C'est un ordre éteint, on passe au suivant
                        continue
                # ------------------------------

                link = node.find("a", class_="sciname") or node.find("a", href=True)
                if not link: continue

                href = link['href']
                match = re.search(r'/taxa/(\d+)', href)
                if not match: continue
                
                raw_name = link.get_text(strip=True)
                name = raw_name.replace("Ordre", "").replace("Order", "").strip()

                orders.append({
                    "id": match.group(1),
                    "name": name,
                    "url": f"{self.base_url}{href}"
                })
            except: continue
        
        unique_orders = {v['id']: v for v in orders}.values()
        return sorted(list(unique_orders), key=lambda x: x['name'])

    def run(self):
        logger.info("Demarrage Etape 1 : Ordres (Filtre Actif)")
        self._init_driver()
        
        try:
            self.driver.get(self.start_url)
            
            if self.open_taxonomy_tab():
                orders = self.extract_orders()
                
                logger.info(f"{len(orders)} Ordres valides (non-éteints) récupérés.")
                
                os.makedirs("data/0_planning", exist_ok=True)
                path = "data/0_planning/1_orders.json"
                
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(orders, f, indent=4, ensure_ascii=False)
                
                logger.info(f"Fichier sauvegardé : {path}")
            
        except Exception as e:
            logger.error(f"Erreur : {e}")
        finally:
            if self.driver: self.driver.quit()

if __name__ == "__main__":
    bot = Step1OrderScraper()
    bot.run()