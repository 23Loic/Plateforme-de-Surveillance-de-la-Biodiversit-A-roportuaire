import time
import re
import sys
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Import absolu depuis le package AeroWise
from src.scrapers.base_scraper import BaseScraper, logger

class INaturalistScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            base_url="https://www.inaturalist.org", 
            output_subfolder="inaturalist_birds"
        )
        self.driver = None

    def _init_driver(self):
        chrome_options = Options()
        
        # --- 1. OPTIMISATIONS POUR EVITER LES CRASH ---
        # Masque les logs techniques de Chrome (DEPRECATED_ENDPOINT, etc.)
        chrome_options.add_argument("--log-level=3") 
        chrome_options.add_argument("--silent")
        
        # Desactive les extensions et fonctionnalités lourdes
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu") 
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        
        # Tu peux décommenter pour voir le navigateur (utile pour debug)
        # chrome_options.add_argument("--headless") 

        self.driver = webdriver.Chrome(options=chrome_options)

    def scroll_to_bottom(self):
        """
        Scroll infini SÉCURISÉ.
        S'arrête si la page ne grandit plus après 3 essais successifs.
        """
        logger.info("Debut du chargement...")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        
        # Compteur pour détecter si on est bloqué
        stuck_counter = 0 
        MAX_STUCK_RETRIES = 3  # On essaie 3 fois avant d'abandonner
        
        # Sécurité : On s'arrête forcément après 500 scrolls (environ 15 000 oiseaux...)
        # pour éviter de faire exploser la RAM du PC.
        MAX_SCROLLS_SAFETY = 500 

        while scroll_count < MAX_SCROLLS_SAFETY:
            # Scroll vers le bas
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # On attend un peu plus longtemps pour laisser le temps au réseau (3.5s)
            time.sleep(3.5) 
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                # La page n'a pas bougé... Est-ce la fin ou un lag ?
                stuck_counter += 1
                sys.stdout.write(f"\r    Pas de nouveau contenu ({stuck_counter}/{MAX_STUCK_RETRIES})...")
                sys.stdout.flush()
                
                if stuck_counter >= MAX_STUCK_RETRIES:
                    print("\n Fin de la page ou blocage détecté. Arrêt du scroll.")
                    break
            else:
                # Ça a bougé, on reset le compteur de blocage
                stuck_counter = 0
                last_height = new_height
                scroll_count += 1
                sys.stdout.write(f"\r   Chargement page/scroll #{scroll_count}...")
                sys.stdout.flush()
        
        logger.info("Chargement termine.")

    def extract_data(self, html_content):
        # ... (Cette partie ne change pas, garde ton code précédent) ...
        soup = BeautifulSoup(html_content, 'html.parser')
        extracted_items = []
        cells = soup.find_all("div", class_="taxon-grid-cell")

        for cell in cells:
            try:
                link_tag = cell.find("a", class_="photo")
                if not link_tag: continue
                href = link_tag.get('href')
                full_url = f"{self.base_url}{href}"

                image_url = None
                style = link_tag.get('style', '')
                match = re.search(r'url\([\"\']?(.*?)[\"\']?\)', style)
                if match:
                    image_url = match.group(1)

                common_name = "Inconnu"
                caption = cell.find("div", class_="caption")
                if caption:
                    name_tag = caption.find("a", class_="display-name")
                    if name_tag:
                        rank_tag = name_tag.find("span", class_="rank")
                        if rank_tag: rank_tag.decompose()
                        common_name = name_tag.get_text(strip=True)

                    scientific_name = "Inconnu"
                    sciname_tag = caption.find("a", class_="secondary-name")
                    if sciname_tag:
                        rank_sci = sciname_tag.find("span", class_="rank")
                        if rank_sci: rank_sci.decompose()
                        scientific_name = sciname_tag.get_text(strip=True)

                extracted_items.append({
                    "common_name": common_name,
                    "scientific_name": scientific_name,
                    "url_fiche": full_url,
                    "image_url": image_url
                })
            except Exception:
                continue
        return extracted_items

    def run(self):
        target_url = f"{self.base_url}/observations?view=species&iconic_taxa=Aves"
        logger.info(f"Demarrage AeroWise Scraper : {target_url}")

        try:
            self._init_driver()
            self.driver.get(target_url)
            time.sleep(5) # Attente initiale plus longue
            
            # 1. Scroll sécurisé
            self.scroll_to_bottom()
            
            full_html = self.driver.page_source
            
            # 2. Extraction
            items = self.extract_data(full_html)
            
            if not items:
                logger.error(" Aucune espèce trouvée ! Vérifier le chargement de la page.")
                return

            # 3. Sauvegarde JSON
            self.save_json("toutes_especes", items)
            
            # 4. Telechargement Images
            logger.info(f"Debut du telechargement des images pour {len(items)} especes...")
            
            download_count = 0
            for item in items:
                if item["image_url"]:
                    success = self.save_image(item["image_url"], item['common_name'])
                    if success:
                        download_count += 1
            
            logger.info("-" * 30)
            logger.info(f" TERMINÉ.")
            logger.info(f" Espèces collectées : {len(items)}")
            logger.info(f" Images sauvegardées : {download_count}")
            logger.info("-" * 30)

        except Exception as e:
            logger.error(f"Erreur : {e}")
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    scraper = INaturalistScraper()
    scraper.run()