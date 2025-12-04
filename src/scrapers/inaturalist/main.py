import time
from bs4 import BeautifulSoup
from src.scrapers.base_scraper import BaseScraper, logger

class INaturalistScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            base_url="https://www.inaturalist.org", 
            output_subfolder="inaturalist_birds"
        )

    def extract_birds_from_html(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        birds_found = []
        cells = soup.find_all("div", class_="taxon-grid-cell")
        
        logger.info(f"Analyse HTML : {len(cells)} éléments trouvés.")

        for cell in cells:
            try:
                link_tag = cell.find("a", class_="photo")
                if not link_tag or not link_tag.has_attr('href'):
                    continue
                
                href = link_tag['href']
                full_url = f"{self.base_url}{href}"

                name_tag = cell.find("a", class_="display-name")
                name = name_tag.get_text(strip=True) if name_tag else href.split("/")[-1]

                birds_found.append({"name": name, "url": full_url})
            except Exception as e:
                logger.error(f"Erreur parsing carte : {e}")

        return birds_found

    def run(self):
        target_url = f"{self.base_url}/observations?view=species&iconic_taxa=Aves"
        logger.info(f"Démarrage Scraping iNaturalist : {target_url}")

        response = self._get_response(target_url)
        
        if response:
            birds = self.extract_birds_from_html(response.text)
            logger.info(f"Succès : {len(birds)} espèces identifiées.")
            for bird in birds:
                logger.info(f" - Trouvé : {bird['name']}")

if __name__ == "__main__":
    scraper = INaturalistScraper()
    scraper.run()