import os
import time
import logging
import requests
from abc import ABC, abstractmethod

# Configuration globale des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Scraper")

class BaseScraper(ABC):
    """
    Classe Mère abstraite. 
    Elle fournit les outils communs (télécharger, sauvegarder) 
    mais ne sait pas 'quoi' scrapper (ça c'est le job des filles).
    """

    def __init__(self, base_url, output_subfolder):
        self.base_url = base_url
        # Architecture Bronze : on sauvegarde dans data/1_bronze/{sous_dossier}
        self.output_dir = os.path.join("data", "1_bronze", output_subfolder)
        
        # Création automatique du dossier
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        logger.info(f"Scraper initialisé. Dossier cible : {self.output_dir}")

    def _get_soup(self, url):
        """Méthode interne pour récupérer le HTML (utilisée par les filles)"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response # On renvoie l'objet response complet (pour .text ou .content)
        except Exception as e:
            logger.error(f"Erreur connexion sur {url} : {e}")
            return None

    def save_file(self, filename, content, extension="html"):
        """Sauvegarde le contenu sur le disque"""
        # Nettoyage du nom de fichier (enlève les caractères interdits)
        safe_name = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
        full_path = os.path.join(self.output_dir, f"{safe_name}.{extension}")

        if os.path.exists(full_path):
            logger.info(f"Ignoré (Existe déjà) : {safe_name}")
            return False

        try:
            mode = "wb" if isinstance(content, bytes) else "w"
            encoding = None if isinstance(content, bytes) else "utf-8"
            
            with open(full_path, mode, encoding=encoding) as f:
                f.write(content)
            
            logger.info(f"Sauvegardé : {safe_name}.{extension}")
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde {filename} : {e}")
            return False

    @abstractmethod
    def run(self):
        """Force les classes filles à avoir une méthode run"""
        pass