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

class INaturalistDeepTraverser(BaseScraper):
    def __init__(self):
        super().__init__(base_url="https://www.inaturalist.org", output_subfolder="0_planning")
        self.start_url = "https://www.inaturalist.org/taxa/3-Aves"

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("--headless") # Decommenter pour cacher le navigateur
        self.driver = webdriver.Chrome(options=chrome_options)

    def ensure_taxonomy_tab(self):
        """
        Active l'onglet Taxinomie sur la page actuelle.
        C'est indispensable pour voir l'arbre ou les listes enfants.
        """
        try:
            wait = WebDriverWait(self.driver, 5)
            # On cherche le lien qui active l'onglet #taxonomy-tab
            tab_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#taxonomy-tab']")))
            self.driver.execute_script("arguments[0].click();", tab_link)
            
            # Attente courte pour que le contenu charge
            time.sleep(2)
            return True
        except:
            return False

    def get_links_by_rank(self, rank_name):
        """
        Recupere les liens des enfants d'un rang donne (ex: 'order', 'family').
        Utilise sur les pages parents.
        """
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        links = []
        
        # Le conteneur de l'arbre
        container = soup.find("div", id="taxonomy-tab")
        if not container: return []

        # On cherche les spans: taxon order, taxon family...
        target_class = f"taxon {rank_name}"
        nodes = container.find_all("span", class_=lambda x: x and target_class in x)

        for node in nodes:
            try:
                link_tag = node.find("a", class_="sciname") or node.find("a", href=True)
                if not link_tag: continue
                
                href = link_tag['href']
                # Extraction ID
                match = re.search(r'/taxa/(\d+)', href)
                if not match: continue
                
                # Nom (nettoyage basique)
                raw_name = link_tag.get_text(strip=True)
                name = raw_name.replace("Ordre", "").replace("Order", "") \
                               .replace("Famille", "").replace("Family", "").strip()

                links.append({
                    "name": name,
                    "url": f"{self.base_url}{href}"
                })
            except: continue
            
        # Dedoublonnage
        unique = {v['url']: v for v in links}.values()
        return list(unique)

    def extract_species_from_current_page(self):
        """
        Recupere les especes et sous-especes sur la page actuelle (niveau Famille).
        Utilise ton selecteur precis 'SplitTaxon'.
        """
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        species_data = []

        container = soup.find("div", id="taxonomy-tab")
        if not container: return []

        # TON SELECTEUR : class="SplitTaxon taxon species..." ou "...subspecies..."
        # On cherche toutes les balises qui correspondent
        target_nodes = container.find_all("span", class_=lambda x: x and "SplitTaxon" in x and ("species" in x or "subspecies" in x))

        for node in target_nodes:
            try:
                # 1. Recuperation du lien (code + url)
                link = node.find("a", href=True)
                if not link: continue
                
                href = link['href']
                match = re.search(r'/taxa/(\d+)', href)
                if not match: continue
                
                code = match.group(1)
                
                # On ignore l'ID 1 ou 3 (Animalia/Aves) si par erreur ils sont pris
                if code in ["1", "3"]: continue

                # 2. Recuperation du Nom
                # Priorite : Nom commun (comname) > Nom scientifique (sciname)
                name_tag = node.find("a", class_="comname")
                if not name_tag:
                    name_tag = node.find("a", class_="sciname")
                
                if name_tag:
                    # On nettoie le texte (au cas ou il y a des balises <span class="rank"> dedans)
                    # On decompose les spans internes pour ne garder que le texte pur
                    temp_soup = BeautifulSoup(str(name_tag), 'html.parser')
                    for rank in temp_soup.find_all("span", class_="rank"):
                        rank.decompose()
                    final_name = temp_soup.get_text(strip=True)
                else:
                    final_name = "Inconnu"

                species_data.append({
                    "code": code,
                    "nom": final_name,
                    "url": f"{self.base_url}{href}"
                })

            except: continue

        return species_data

    def run(self):
        logger.info("Demarrage du Parcours Complet (Ordre > Famille > Especes)...")
        self._init_driver()
        master_list = []
        
        try:
            # ETAPE 1 : Recuperer les Ordres depuis la page Aves
            self.driver.get(self.start_url)
            self.ensure_taxonomy_tab()
            
            orders = self.get_links_by_rank("order")
            logger.info(f"{len(orders)} Ordres trouves a la racine.")
            
            # ETAPE 2 : Parcourir chaque Ordre
            count_ord = 1
            for order in orders:
                logger.info(f"[{count_ord}/{len(orders)}] Exploration Ordre : {order['name']}")
                
                # Navigation vers la page de l'Ordre
                self.driver.get(order['url'])
                self.ensure_taxonomy_tab()
                
                # Recuperer les Familles
                families = self.get_links_by_rank("family")
                logger.info(f"   -> {len(families)} familles trouvees.")
                
                # ETAPE 3 : Parcourir chaque Famille
                for fam in families:
                    # Navigation vers la page de la Famille
                    self.driver.get(fam['url'])
                    self.ensure_taxonomy_tab()
                    
                    # C'est ici qu'on recupere les especes/sous-especes
                    # Puisqu'on est au niveau Famille, l'arbre affiche generalement tout
                    # On scrolle un peu pour charger le lazy-loading si besoin
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    
                    species = self.extract_species_from_current_page()
                    
                    # Ajout a la liste globale
                    for sp in species:
                        sp['ordre'] = order['name']
                        sp['famille'] = fam['name']
                        master_list.append(sp)
                        
                    sys.stdout.write(f"\r      + {fam['name']} : {len(species)} codes recuperes.\n")
                
                count_ord += 1

            # SAUVEGARDE
            os.makedirs("data/0_planning", exist_ok=True)
            path = "data/0_planning/MASTER_AVES_CODES.json"
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(master_list, f, indent=4, ensure_ascii=False)
                
            logger.info("-" * 30)
            logger.info(f"Termine. {len(master_list)} especes/sous-especes sauvegardees.")
            logger.info(f"Fichier : {path}")

        except Exception as e:
            logger.error(f"Erreur critique : {e}")
        finally:
            if self.driver: self.driver.quit()

if __name__ == "__main__":
    bot = INaturalistDeepTraverser()
    bot.run()