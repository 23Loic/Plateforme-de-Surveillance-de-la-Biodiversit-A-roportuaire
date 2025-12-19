import os
import json
import glob

# Dossier où sont stockés tes fichiers JSON bruts
TARGET_DIR = "data/bronze/inaturalist/pages"

def clean_corrupted_data():
    print(f"🧹 Démarrage du nettoyage dans : {TARGET_DIR}")
    
    files = glob.glob(os.path.join(TARGET_DIR, "*.json"))
    deleted_count = 0
    total_count = len(files)
    
    print(f"Analyse de {total_count} fichiers...")

    for i, filepath in enumerate(files):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            html_content = data.get('raw_html_content', '')
            
            # Les marqueurs d'erreur 429 dans le HTML partiel
            if "Too Many Requests" in html_content or "429 Too Many Requests" in html_content:
                print(f"❌ Fichier corrompu détecté (429) : {os.path.basename(filepath)}")
                
                # On ferme et on supprime
                f.close() 
                os.remove(filepath)
                deleted_count += 1
                
        except Exception as e:
            print(f"⚠️ Erreur lecture {filepath}: {e}")

    print("-" * 30)
    print(f"BILAN : {deleted_count} fichiers supprimés sur {total_count}.")
    print("Vous pouvez relancer le scraper, il traitera à nouveau ces fichiers manquants.")

if __name__ == "__main__":
    clean_corrupted_data()