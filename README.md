Projet Airport AI - Biodiversité & Sécurité

Ce projet a pour objectif de créer une base de données intelligente pour la gestion des risques aéroportuaires liés à la biodiversité (Bird Strikes, incursions). Il s'appuie sur une architecture multi-agents et des bases de données spécialisées (Géospatiale, Graphe, Vectorielle).

---

1. Pré-requis

Avant de récupérer le projet, assurez-vous d'avoir installé sur votre machine :
- Git : Pour le versioning.
- Docker Desktop : Indispensable pour faire tourner les bases de données.
- Python 3.10 (ou supérieur).
- VS Code (Recommandé) avec l'extension Python.

---

2. Installation (Pas à pas)

Étape A : Cloner le dépôt
Ouvrez votre terminal et lancez :

git clone <URL_DU_REPO_GITHUB>
cd airport-ai-project

Étape B : Configurer l'environnement Python
Ne travaillez jamais sur le Python global. Créez un environnement virtuel isolé.

Sur Windows (PowerShell) :

python -m venv venv
.\venv\Scripts\activate

Sur Mac / Linux :

python3 -m venv venv
source venv/bin/activate

Étape C : Installer les dépendances

pip install -r requirements.txt

Étape D : Configuration des secrets (.env)

Dupliquez le fichier .env.example situé à la racine.
Renommez la copie en .env.
Ce fichier contient les mots de passe des bases de données (pré-configurés pour Docker) et les clés API (OpenAI, DeepSeek) à ajouter soi-même.
Le fichier .env est ignoré par Git pour des raisons de sécurité.

---

3. Lancement de l'Infrastructure

Ce projet utilise Docker pour orchestrer les bases de données (PostGIS, Neo4j, Qdrant). Il n'est pas nécessaire de les installer localement.

Assurez-vous que Docker Desktop est lancé.
Dans le terminal, lancez :

docker-compose up -d

Le premier lancement peut prendre plusieurs minutes.

---

4. Vérification de l'installation

Un script de diagnostic permet de valider la connectivité aux bases de données.
Assurez-vous d'être dans l'environnement virtuel et lancez :

python check_db.py

Si le script retourne trois messages de succès, tout fonctionne.

---

5. Organisation du Projet

Le projet suit une architecture Medallion (Bronze → Silver → Gold).

data/ : ignoré par Git, contient les données locales
- 1_bronze/ : Données brutes (HTML, PDF)
- 2_silver/ : Données nettoyées (Markdown)
- 3_gold/ : Données enrichies (vecteurs, graphes)

src/ : Code source
- scrapers/ : scripts de collecte
- processors/ : OCR, nettoyage
- database/ : connexion aux BDD

---

6. Dépannage (FAQ)

Problème : Module not found ou pip n'est pas reconnu
→ L’environnement virtuel n'est pas activé.

Windows : .\venv\Scripts\activate
Mac/Linux : source venv/bin/activate

Problème : Erreur de connexion BDD (byte 0xe9, Connection Refused)
→ Conflit de port probable.

1. Ouvrir docker-compose.yml
2. Modifier le port, ex : "5433:5432"
3. Mettre à jour check_db.py
4. Relancer Docker :

docker-compose down
docker-compose up -d

Problème : Docker ne démarre pas
→ Vérifier que la virtualisation est activée dans le BIOS.

