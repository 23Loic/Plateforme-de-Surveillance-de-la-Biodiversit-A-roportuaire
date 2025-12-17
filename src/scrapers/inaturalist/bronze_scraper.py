import json
import time
import os
import concurrent.futures
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
INPUT_PLAN = "data/0_planning/SCRAPING_PLAN_3.json"  # Le fichier généré par l'API
OUTPUT_DIR = "data/bronze/inaturalist/pages"         # Où on stocke les HTML
MAX_WORKERS = 4                                      # Nombre de navigateurs en parallèle (4-6 recommandés)
TIMEOUT = 15                                         # Temps max pour charger une page

def get_optimized_driver():
    """ Crée un driver Chrome ultra-léger pour le scraping de masse """
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # OPTIMISATION MAJEURE : Bloquer le chargement des images et du CSS
    # On ne veut que le HTML, on se fiche que la page soit "belle".
    prefs = {
        "profile.managed_default_content_settings.images": 2,       # Pas d'images
        "profile.managed_default_content_settings.stylesheets": 2,  # Pas de CSS
        "profile.managed_default_content_settings.cookies": 2,      # Pas de cookies
        "profile.managed_default_content_settings.javascript": 1    # JS activé (obligatoire pour React)
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Stratégie de chargement "eager" : On n'attend pas que tout soit chargé à 100%
    # Dès que le DOM est interactif, on prend la main.
    chrome_options.page_load_strategy = 'eager'
    
    return webdriver.Chrome(options=chrome_options)

def scrape_worker(species_subset, worker_id):
    """
    Fonction exécutée par chaque 'Worker' (Thread).
    Il ouvre son propre navigateur et traite sa liste d'espèces.
    """
    print(f"[Worker {worker_id}] Démarrage... ({len(species_subset)} espèces à traiter)")
    
    driver = None
    try:
        driver = get_optimized_driver()
    except Exception as e:
        print(f"[Worker {worker_id}] Erreur initialisation driver: {e}")
        return

    count = 0
    for sp in species_subset:
        sp_id = sp['id']
        filename = os.path.join(OUTPUT_DIR, f"{sp_id}.json")

        # 1. Skip si déjà fait (Reprise sur erreur)
        if os.path.exists(filename):
            continue

        try:
            # 2. Navigation
            driver.get(sp['url'])

            # 3. Attente ciblée (TaxonDetail)
            # On attend juste que la boite principale apparaisse
            try:
                element = WebDriverWait(driver, TIMEOUT).until(
                    EC.presence_of_element_located((By.ID, "TaxonDetail"))
                )
                
                # Petite pause aléatoire pour ne pas ressembler à un robot (0.5 à 1.5s)
                # Même en mode bourrin, un peu d'aléatoire évite le ban IP
                time.sleep(random.uniform(0.5, 1.5))
                
                # 4. Extraction
                raw_html = element.get_attribute('outerHTML')
                
                # 5. Sauvegarde
                data = {
                    "id": sp_id,
                    "url": sp['url'],
                    "scraped_at": time.time(),
                    "raw_html_content": raw_html
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False)
                
                count += 1
                if count % 10 == 0:
                    print(f"[Worker {worker_id}] {count}/{len(species_subset)} traités.")

            except Exception as e:
                print(f"[Worker {worker_id}] Timeout/Erreur sur {sp_id} : {e}")
                # On écrit un fichier vide ou d'erreur pour ne pas rebloquer dessus ?
                # Non, on laisse pour retenter plus tard.

        except Exception as e:
            print(f"[Worker {worker_id}] Crash critique sur {sp_id}: {e}")
            # Si le driver est mort, on tente de le relancer
            try:
                driver.quit()
                driver = get_optimized_driver()
            except: pass

    if driver:
        driver.quit()
    print(f"[Worker {worker_id}] Terminé.")

def run_orchestrator():
    # 1. Préparation
    if not os.path.exists(INPUT_PLAN):
        print("Erreur : Lance d'abord l'API Harvester pour générer le plan !")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_PLAN, 'r', encoding='utf-8') as f:
        full_list = json.load(f)
    
    # Filtrer ceux déjà faits pour gagner du temps au redémarrage
    existing_files = set(os.listdir(OUTPUT_DIR))
    todo_list = [sp for sp in full_list if f"{sp['id']}.json" not in existing_files]
    
    total = len(full_list)
    remaining = len(todo_list)
    
    print(f"PLAN DE CHARGE : {total} espèces au total.")
    print(f"DÉJÀ FAIT      : {total - remaining}")
    print(f"À FAIRE        : {remaining}")
    print("-" * 50)

    if remaining == 0:
        print("Tout est fini ! Bravo.")
        return

    # 2. Découpage pour les Workers
    # On divise la liste en N parts égales
    chunk_size = len(todo_list) // MAX_WORKERS + 1
    chunks = [todo_list[i:i + chunk_size] for i in range(0, len(todo_list), chunk_size)]

    print(f"Lancement de {len(chunks)} workers en parallèle...")

    # 3. Exécution Parallèle
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for i, chunk in enumerate(chunks):
            futures.append(executor.submit(scrape_worker, chunk, i+1))
        
        # Attente de la fin
        concurrent.futures.wait(futures)

    print("-" * 50)
    print("SCRAPING TERMINÉ.")

if __name__ == "__main__":
    run_orchestrator()