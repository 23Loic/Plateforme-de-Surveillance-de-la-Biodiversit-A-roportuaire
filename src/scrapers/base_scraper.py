import os
import json
import shutil
import logging
import requests
from abc import ABC, abstractmethod

# Configuration des logs sans emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("AeroWise_Scraper")

class BaseScraper(ABC):
    """
    Classe Mere : Gere le telechargement et le stockage (Bronze Layer).
    Supporte : HTML, JSON (Metadonnees/Textes), Images.
    """

    def __init__(self, base_url, output_subfolder):
        """
        Initialise le scraper, definit l'URL de base et cree la structure de dossiers
        pour le stockage des donnees (html, images, metadata).
        """
        self.base_url = base_url
        self.output_dir = os.path.join("data", "1_bronze", output_subfolder)
        
        self.dirs = {
            "html": os.path.join(self.output_dir, "html"),
            "images": os.path.join(self.output_dir, "images"),
            "metadata": os.path.join(self.output_dir, "metadata")
        }
        
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        logger.info(f"Scraper initialise. Dossier de sortie : {self.output_dir}")

    def save_html(self, filename, content):
        """
        Sauvegarde le contenu textuel (code source HTML) dans le dossier html.
        Ajoute automatiquement l'extension .html si absente.
        """
        safe_name = self._sanitize_filename(filename) + ".html"
        path = os.path.join(self.dirs["html"], safe_name)
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde HTML {filename} : {e}")
            return False

    def save_json(self, filename, data):
        """
        Sauvegarde des donnees structurees (dictionnaire ou liste) au format JSON
        dans le dossier metadata. Utile pour les liens et descriptions.
        """
        safe_name = self._sanitize_filename(filename) + ".json"
        path = os.path.join(self.dirs["metadata"], safe_name)
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde JSON {filename} : {e}")
            return False

    def save_image(self, url, filename):
        """
        Telecharge une image depuis une URL et la sauvegarde dans le dossier images.
        Gere le streaming pour eviter de charger de gros fichiers en memoire.
        """
        safe_name = self._sanitize_filename(filename)
        if not safe_name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            safe_name += ".jpg" 
            
        path = os.path.join(self.dirs["images"], safe_name)

        if os.path.exists(path):
            return False 

        try:
            response = requests.get(url, headers=self.headers, stream=True, timeout=15)
            response.raise_for_status()
            with open(path, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
            return True
        except Exception as e:
            logger.error(f"Erreur telechargement Image {url} : {e}")
            return False

    def _sanitize_filename(self, filename):
        """
        Nettoie une chaine de caracteres pour la rendre compatible avec le systeme de fichiers
        (supprime les caracteres speciaux et remplace les espaces par des underscores).
        """
        return "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip().replace(' ', '_')

    @abstractmethod
    def run(self):
        """
        Methode abstraite qui devra etre implementee par chaque scraper specifique
        pour definir sa logique d'execution.
        """
        pass