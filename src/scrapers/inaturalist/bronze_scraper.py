import json
import time
import os
import requests
import random
import concurrent.futures
import threading
from datetime import datetime

# --- CONFIGURATION STABILISÉE ---
INPUT_PLAN = "data/0_planning/SCRAPING_PLAN_3.json"
OUTPUT_DIR = "data/bronze/inaturalist/pages"

# On réduit la charge pour éviter le "Soft Ban"
MAX_WORKERS = 4 
MIN_SLEEP = 1.5
MAX_SLEEP = 3.5

# LISTE DE CAMOUFLAGE (User-Agents Rotatifs)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/119.0.0.0 Safari/537.36"
]

thread_local = threading.local()

def get_session():
    """ Crée une session avec un User-Agent aléatoire fixe pour ce thread """
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
        # On choisit une identité au hasard pour ce worker
        ua = random.choice(USER_AGENTS)
        thread_local.session.headers.update({
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
        })
    return thread_local.session

def get_full_wikipedia_content(session, scientific_name, common_name):
    attempts = [
        {"lang": "fr", "query": scientific_name},
        {"lang": "en", "query": scientific_name},
        {"lang": "fr", "query": common_name}
    ]
    
    for attempt in attempts:
        if not attempt["query"]: continue
        try:
            url = f"https://{attempt['lang']}.wikipedia.org/w/api.php"
            params = {
                "action": "query", "format": "json", "titles": attempt["query"],
                "prop": "extracts", "explaintext": True, "redirects": 1
            }
            # Timeout court pour Wiki, ce n'est pas le goulot d'étranglement
            resp = session.get(url, params=params, timeout=3)
            if resp.status_code == 200:
                pages = resp.json().get("query", {}).get("pages", {})
                pid = next(iter(pages))
                if pid != "-1" and len(pages[pid].get("extract", "")) > 100:
                    return {
                        "source": f"wikipedia_{attempt['lang']}",
                        "title": pages[pid].get("title"),
                        "full_text": pages[pid]["extract"]
                    }
        except: continue
    return None

def process_species(sp):
    sp_id = sp['id']
    url = sp['url']
    filename = os.path.join(OUTPUT_DIR, f"{sp_id}.json")
    
    if os.path.exists(filename): return "EXISTS"

    session = get_session()
    
    # STRATÉGIE DE BACKOFF EXPONENTIEL (Tentatives intelligentes)
    # Tentative 1 : immédiate
    # Tentative 2 : attendre 5s
    # Tentative 3 : attendre 15s (si le serveur est fâché)
    delays = [0, 5, 15] 

    for delay in delays:
        if delay > 0:
            time.sleep(delay)

        try:
            # Timeout augmenté pour absorber les lenteurs du serveur
            response = session.get(url, timeout=20)
            
            # Si on se fait bloquer (429) ou erreur serveur (5xx), on retry
            if response.status_code == 429 or response.status_code >= 500:
                continue 
            
            if response.status_code == 200:
                html_content = response.text
                wiki_data = get_full_wikipedia_content(session, sp.get('scientific_name'), sp.get('nom'))
                
                final_data = {
                    "id": sp_id, "url": url,
                    "scraped_at": datetime.now().isoformat(),
                    "scientific_name": sp.get('scientific_name'),
                    "common_name": sp.get('nom'),
                    "raw_html_content": html_content,
                    "external_description": wiki_data
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(final_data, f, ensure_ascii=False)

                # Pause aléatoire pour casser le rythme robotique
                time.sleep(random.uniform(MIN_SLEEP, MAX_SLEEP))
                return "OK"
            
            elif response.status_code == 404:
                return "ERROR_404" # Inutile de réessayer une 404

        except requests.exceptions.RequestException:
            continue # Erreur réseau pure -> on retry

    return "ERROR_FINAL"

def run_stable_scraper():
    if not os.path.exists(INPUT_PLAN): return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(INPUT_PLAN, 'r', encoding='utf-8') as f:
        full_list = json.load(f)
    
    # Mélange aléatoire pour ne pas taper toujours les mêmes familles
    random.shuffle(full_list)

    existing = set(os.listdir(OUTPUT_DIR))
    todo = [sp for sp in full_list if f"{sp['id']}.json" not in existing]
    
    print(f"🛡️ Démarrage MODE STABLE ({MAX_WORKERS} workers)")
    print(f"📋 Reste : {len(todo)} espèces.")
    
    stats = {"OK": 0, "ERR": 0, "SKIP": 0}
    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_species, sp): sp for sp in todo}
        
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            res = future.result()
            if res == "OK": stats["OK"] += 1
            elif res == "EXISTS": stats["SKIP"] += 1
            else: stats["ERR"] += 1
            
            if (i + 1) % 20 == 0:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed
                # Calcul précis du % d'erreur
                err_rate = (stats["ERR"] / (stats["OK"] + stats["ERR"] + 0.1)) * 100
                rem_min = (len(todo) - (i + 1)) / (rate + 0.01) / 60
                
                print(f"[{i+1}/{len(todo)}] Vit: {rate:.1f} sp/s | Erreurs: {stats['ERR']} ({err_rate:.1f}%) | Fin: ~{rem_min:.0f} min")

    print(f"Terminé. OK: {stats['OK']}, Erreurs: {stats['ERR']}")

if __name__ == "__main__":
    run_stable_scraper()