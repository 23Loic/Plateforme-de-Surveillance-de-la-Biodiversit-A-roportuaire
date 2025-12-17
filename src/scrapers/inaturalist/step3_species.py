import time
import re
import json
import os
import sys
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Import absolu depuis ton package
from src.scrapers.base_scraper import BaseScraper, logger

class Step3SpeciesScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            base_url="https://www.inaturalist.org", 
            output_subfolder="0_planning"
        )
        self.driver = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("--headless") # Decommenter si besoin
        self.driver = webdriver.Chrome(options=chrome_options)

    def load_families(self):
        path = "data/0_planning/2_families.json"
        if not os.path.exists(path):
            logger.error(f"Fichier {path} introuvable. Lancez l'Etape 2 d'abord.")
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def clean_name(self, tag):
        if not tag: return None
        soup_fragment = BeautifulSoup(str(tag), 'html.parser')
        for rank in soup_fragment.find_all("span", class_="rank"):
            rank.decompose()
        return soup_fragment.get_text(strip=True)

    def scroll_to_bottom(self):
        """
        Scroll basé sur ta méthode : Hauteur + Compteur de blocage + Limite de sécurité.
        """
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        
        # Compteur pour détecter si on est bloqué
        stuck_counter = 0 
        MAX_STUCK_RETRIES = 3  # On essaie 3 fois avant d'abandonner
        MAX_SCROLLS_SAFETY = 300 # Sécurité pour ne pas boucler à l'infini

        while scroll_count < MAX_SCROLLS_SAFETY:
            # Scroll vers le bas
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # On attend 3.5s comme dans ton exemple
            time.sleep(3.5) 
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                # La page n'a pas bougé
                stuck_counter += 1
                if stuck_counter >= MAX_STUCK_RETRIES:
                    # On considère que le chargement est fini
                    break
            else:
                # Ça a bougé, on reset le compteur de blocage et on continue
                stuck_counter = 0
                last_height = new_height
                scroll_count += 1

    def fetch_species_from_grid(self, family_id):
        url = f"{self.base_url}/observations?view=species&taxon_id={family_id}&place_id=any&verifiable=any"
        self.driver.get(url)

        # Utilisation de TA méthode de scroll
        self.scroll_to_bottom()
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        species_list = []
        
        cells = soup.find_all("div", class_="taxon-grid-cell")
        
        for cell in cells:
            try:
                caption = cell.find("div", class_="caption")
                if not caption: continue

                disp_tag = caption.find("a", class_="display-name")
                sec_tag = caption.find("a", class_="secondary-name")
                
                main_tag = disp_tag if disp_tag else sec_tag
                if not main_tag: continue

                href = main_tag['href']
                match = re.search(r'/taxa/(\d+)', href)
                if not match: continue
                sp_id = match.group(1)

                if sp_id in ["1", "3"]: continue 

                full_url = f"{self.base_url}{href}"

                nom_commun = self.clean_name(disp_tag)
                nom_scientifique = self.clean_name(sec_tag)
                
                final_name = nom_commun if nom_commun else nom_scientifique

                species_list.append({
                    "id": sp_id,
                    "nom": final_name,
                    "nom_scientifique": nom_scientifique,
                    "url": full_url
                })
            except: continue
            
        return species_list

    def run(self):
        logger.info("Demarrage Etape 3 : Moissonnage (Structure v3 + Scroll 'Height Check')")
        self._init_driver()
        full_inventory = []
        
        try:
            families = self.load_families()
            if not families: return

            count = 1
            total = len(families)

            for fam in families:
                sys.stdout.write(f"\r[{count}/{total}] Scan Famille : {fam['name']}...")
                sys.stdout.flush()
                
                species = self.fetch_species_from_grid(fam['id'])
                
                for sp in species:
                    sp['famille'] = fam['name']
                    sp['ordre'] = fam['order']
                    full_inventory.append(sp)
                
                sys.stdout.write(f" -> {len(species)} esp.\n")
                count += 1

            os.makedirs("data/0_planning", exist_ok=True)
            path = "data/0_planning/MASTER_AVES_DATA.json"
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(full_inventory, f, indent=4, ensure_ascii=False)
            
            logger.info("-" * 30)
            logger.info(f"TERMINE.")
            logger.info(f"Total especes : {len(full_inventory)}")
            logger.info(f"Fichier : {path}")
            logger.info("-" * 30)

        except Exception as e:
            logger.error(f"Erreur : {e}")
        finally:
            if self.driver: self.driver.quit()

if __name__ == "__main__":
    bot = Step3SpeciesScraper()
    bot.run()