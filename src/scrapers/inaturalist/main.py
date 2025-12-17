import requests
import json
import time
import os
import sys

# --- CONFIGURATION ---
BASE_URL = "https://api.inaturalist.org/v1/taxa"
OUTPUT_DIR = "data/0_planning"

# ID Taxonomique (3 = Aves/Oiseaux)
TAXON_ID = 3
TIMEOUT_SEC = 30
REQ_PER_SEC = 1.0  # Temporisation pour la stabilite

def fetch_bird_species():
    """
    Recupere la liste complete des especes via l'API.
    Utilise la pagination 'id_above' pour garantir l'exhaustivite (10k+ especes).
    Ne garde que les donnees utiles pour le futur scraping.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    all_species = []
    last_id = 0
    batch_size = 200 # Max par page
    
    print(f"Demarrage de l'indexation API (Taxon ID: {TAXON_ID})...")
    
    while True:
        params = {
            'taxon_id': TAXON_ID,
            'rank': 'species',         # On filtre deja ici, donc le champ 'rank' devient inutile
            'per_page': batch_size,
            'locale': 'fr',            # Noms communs francais
            'preferred_place_id': 1,
            'is_active': 'true',
            'order': 'asc',
            'order_by': 'id',
            'id_above': last_id        # Pagination glissante
        }

        try:
            response = requests.get(BASE_URL, params=params, timeout=TIMEOUT_SEC)
            
            if response.status_code != 200:
                print(f"Erreur API {response.status_code}")
                break

            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            for taxon in results:
                # On recupere uniquement ce qui sert a identifier la page a scraper
                entry = {
                    'id': str(taxon['id']),
                    'scientific_name': taxon['name'],
                    'common_name': taxon.get('preferred_common_name', ''),
                    # URL cible pour le scraper
                    'url': f"https://www.inaturalist.org/taxa/{taxon['id']}",
                    # Image API (utile comme backup si le scraping echoue)
                    'api_image_url': taxon.get('default_photo', {}).get('medium_url') if taxon.get('default_photo') else None
                }
                all_species.append(entry)

            last_id = results[-1]['id']
            
            # Feedback minimaliste
            sys.stdout.write(f"\rIndexe : {len(all_species)} especes (Curseur ID: {last_id})")
            sys.stdout.flush()

            time.sleep(REQ_PER_SEC)

        except Exception as e:
            print(f"\nErreur : {e}")
            break

    # --- GENERATION DES FICHIERS ---
    print("\n" + "-" * 50)
    
    # Fichier Plan de Scraping (JSON leger)
    filename = f"SCRAPING_PLAN_{TAXON_ID}.json"
    output_path = os.path.join(OUTPUT_DIR, filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_species, f, ensure_ascii=False, indent=4)

    print(f"Termine. {len(all_species)} especes indexees.")
    print(f"Fichier genere : {output_path}")

if __name__ == "__main__":
    fetch_bird_species()