import json
import re
import os
from bs4 import BeautifulSoup

# Configuration
INPUT_FILE = "data/bronze/inaturalist/test_bronze_duck.json"
OUTPUT_DIR = "data/silver/inaturalist"

def extract_bg_image(style_str):
    """ Extrait l'URL propre depuis 'background-image: url(...)' """
    if not style_str: return None
    match = re.search(r'url\((?:&quot;|")?(.*?)(?:&quot;|")?\)', style_str)
    return match.group(1) if match else None

def clean_text(text):
    """ Nettoie le texte (espaces multiples, sauts de ligne) """
    if not text: return None
    return re.sub(r'\s+', ' ', text).strip()

def process_deep_extraction():
    print(f"🕵️  Démarrage de l'extraction APPROFONDIE sur : {INPUT_FILE}")
    
    if not os.path.exists(INPUT_FILE):
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    soup = BeautifulSoup(raw_data.get('raw_html_content', ''), 'html.parser')
    
    # --- 1. TAXONOMIE (Déjà validé) ---
    # (Je garde la version simple ici pour la cohérence)
    taxonomy = {}
    crumbs = soup.find('ul', class_='TaxonCrumbs')
    if crumbs:
        for li in crumbs.find_all('li'):
            rank_span = li.find('span', class_='rank')
            name_tag = li.find('a', class_='sciname') or li.find('span', class_='sciname')
            if rank_span and name_tag:
                rank = rank_span.get_text(strip=True).lower()
                name = name_tag.get_text(strip=True).replace(rank_span.get_text(strip=True), "").strip()
                taxonomy[rank] = name

    # --- 2. DESCRIPTION (Le texte "À propos") ---
    # iNaturalist met le contenu Wikipedia dans une div class "wikipedia_description"
    description_text = ""
    desc_div = soup.find('div', class_='wikipedia_description')
    if desc_div:
        # On prend tous les paragraphes <p> pour avoir un texte structuré
        paragraphs = [p.get_text(strip=True) for p in desc_div.find_all('p') if p.get_text(strip=True)]
        description_text = "\n\n".join(paragraphs)

    # --- 3. STATUTS DE CONSERVATION & GÉOGRAPHIE ---
    # Ces infos sont dans l'onglet #status-tab
    conservation_status = []
    status_tab = soup.find('div', id='status-tab')
    if status_tab:
        rows = status_tab.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                # La 1ère colonne contient le lieu (souvent dans un lien ou texte direct)
                place = clean_text(cols[0].get_text())
                # La 2ème colonne contient le statut (ex: LC, Secure...)
                status = clean_text(cols[1].get_text())
                if place and status:
                    conservation_status.append({"lieu": place, "statut": status})

    # --- 4. STATUTS D'IMPLANTATION (Natif / Introduit) ---
    # Souvent dans une section class "establishment-means"
    establishment = []
    est_section = soup.find('div', class_='establishment-means')
    if est_section:
        rows = est_section.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                place = clean_text(cols[0].get_text())
                means = clean_text(cols[1].get_text()) # "Introduit", "Natif"...
                if place and means:
                    establishment.append({"lieu": place, "type": means})

    # --- 5. GALERIE PHOTOS (Toutes les images) ---
    photos = []
    # Photo principale (Cover)
    cover_div = soup.find('div', class_='CoverImage')
    if cover_div:
        img_url = extract_bg_image(cover_div.get('style'))
        if img_url: photos.append({"type": "cover", "url": img_url})
    
    # Autres photos (vignettes)
    other_photos_ul = soup.find('ul', class_='others')
    if other_photos_ul:
        for a_tag in other_photos_ul.find_all('a', class_='photoItem'):
            # L'image est souvent en background du div interne
            div_img = a_tag.find('div', class_='CoverImage')
            if div_img:
                img_url = extract_bg_image(div_img.get('style'))
                if img_url: 
                    # On nettoie l'URL pour avoir la version large si possible (souvent 'square' -> 'medium' ou 'large')
                    large_url = img_url.replace('square', 'large').replace('small', 'large')
                    photos.append({"type": "gallery", "url": large_url})

    # --- 6. AUDIOS / SONS ---
    sounds = []
    audio_tags = soup.find_all('audio')
    for audio in audio_tags:
        src = audio.get('src') or (audio.find('source')['src'] if audio.find('source') else None)
        if src:
            sounds.append(src)

    # --- ASSEMBLAGE FINAL ---
    silver_data = {
        "id_source": raw_data['url'].split('/')[-1].split('-')[0],
        "nom_commun": clean_text(soup.find('div', id='TaxonHeader').find('h1').find('span', class_='comname').get_text()) if soup.find('div', id='TaxonHeader') else "Inconnu",
        "nom_scientifique": clean_text(soup.find('div', id='TaxonHeader').find('h1').find('span', class_='sciname').get_text()) if soup.find('div', id='TaxonHeader') else "Inconnu",
        "taxonomie": taxonomy,
        "description_courte": description_text[:300] + "..." if description_text else None, # Aperçu
        "description_complete": description_text, # Tout le texte
        "media": {
            "photos": photos,
            "sons": sounds
        },
        "biogeographie": {
            "conservation": conservation_status,
            "implantation": establishment
        },
        "source_url": raw_data['url']
    }

    # --- SAUVEGARDE ET APERÇU ---
    print("\n--- APERÇU DES DONNÉES EXTRAITES ---")
    print(f"Taxonomie : {silver_data['taxonomie']}")
    print(f"Photos récupérées : {len(photos)}")
    print(f"Sons récupérés : {len(sounds)}")
    print(f"Lignes de conservation : {len(conservation_status)}")
    print(f"Lignes d'implantation : {len(establishment)}")
    print(f"Début description : {silver_data['description_courte']}")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "silver_duck_enriched.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(silver_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ Fichier enrichi sauvegardé : {output_path}")

if __name__ == "__main__":
    process_deep_extraction()