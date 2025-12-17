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

class Step2FamilyScraper(BaseScraper):
    def __init__(self):
        super().__init__(base_url="https://www.inaturalist.org", output_subfolder="0_planning")

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        self.driver = webdriver.Chrome(options=chrome_options)

    def load_orders(self):
        """ Charge la liste des Ordres depuis l'etape 1 """
        path = "data/0_planning/1_orders.json"
        if not os.path.exists(path):
            logger.error(f"Fichier {path} introuvable. Lancez l'Etape 1 d'abord.")
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def open_taxonomy_tab(self):
        """ Ouvre l'onglet Taxinomie """
        try:
            wait = WebDriverWait(self.driver, 10)
            tab_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#taxonomy-tab']")))
            self.driver.execute_script("arguments[0].click();", tab_link)
            wait.until(EC.presence_of_element_located((By.ID, "taxonomy-tab")))
            time.sleep(2)
            return True
        except:
            return False

    def extract_families(self, order_name):
        """ 
        Extrait les Familles valides de la page courante.
        Applique le filtre 'hidable' (especes eteintes).
        """
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        families = []

        container = soup.find("div", id="taxonomy-tab")
        if not container: return []

        nodes = container.find_all("span", class_=lambda x: x and "taxon family" in x)

        for node in nodes:
            try:
                # --- FILTRE ANTI-EXTINCTION ---
                parent_li = node.find_parent("li")
                if parent_li and parent_li.get("class"):
                    if "hidable" in parent_li.get("class"):
                        continue 
                # ------------------------------

                link = node.find("a", class_="sciname") or node.find("a", href=True)
                if not link: continue

                href = link['href']
                match = re.search(r'/taxa/(\d+)', href)
                if not match: continue
                
                raw_name = link.get_text(strip=True)
                name = raw_name.replace("Famille", "").replace("Family", "").strip()

                families.append({
                    "id": match.group(1),
                    "name": name,
                    "order": order_name, # On garde la reference de l'Ordre parent
                    "url": f"{self.base_url}{href}"
                })
            except: continue
        
        unique = {v['id']: v for v in families}.values()
        return list(unique)

    def run(self):
        logger.info("Demarrage Etape 2 : Recuperation des Familles")
        self._init_driver()
        all_families = []
        
        try:
            orders = self.load_orders()
            if not orders: return

            count = 1
            total = len(orders)

            for order in orders:
                logger.info(f"[{count}/{total}] Traitement de l'Ordre : {order['name']}")
                
                self.driver.get(order['url'])
                
                if self.open_taxonomy_tab():
                    fams = self.extract_families(order['name'])
                    all_families.extend(fams)
                    logger.info(f"   -> {len(fams)} familles trouvees.")
                else:
                    logger.warning(f"   -> Pas d'onglet Taxinomie ou vide pour {order['name']}.")

                count += 1

            # Sauvegarde
            os.makedirs("data/0_planning", exist_ok=True)
            path = "data/0_planning/2_families.json"
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(all_families, f, indent=4, ensure_ascii=False)
            
            logger.info(f"TERMINE. {len(all_families)} familles valides sauvegardees dans {path}")

        except Exception as e:
            logger.error(f"Erreur critique : {e}")
        finally:
            if self.driver: self.driver.quit()

if __name__ == "__main__":
    bot = Step2FamilyScraper()
    bot.run()