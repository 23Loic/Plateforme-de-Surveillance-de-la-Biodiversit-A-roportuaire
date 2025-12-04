# AeroWise - Système de Gestion Aéroportuaire Intelligent

AeroWise est une plateforme Big Data dédiée à la gestion des risques aéroportuaires, avec un focus particulier sur la biodiversité (Péril Animalier) et la sécurité des pistes.

L'architecture repose sur une collecte de données multi-sources (Scraping), une analyse par IA (Agents, OCR, NLP) et un stockage multi-modèle (Géospatial, Graphe, Vectoriel).

---

## 1. Pré-requis techniques

Avant de commencer, assurez-vous d'avoir installé :

- **Git** : Pour cloner le dépôt
- **Docker Desktop** : Indispensable pour l'infrastructure (PostGIS, Neo4j, Qdrant)
- **Python 3.10+** : Langage principal du backend
- **Node.js & npm** : Pour la partie Frontend (React)
- **VS Code** (Recommandé)

---

## 2. Installation (Backend)

### Étape A : Cloner le projet

```bash
git clone <VOTRE_URL_REPO>
cd airport-ai-project
```

### Étape B : Créer l'environnement virtuel

Ne travaillez jamais sur le Python global.

**Windows (PowerShell) :**

```powershell
# Création (Si 'python' ne marche pas, essayez 'py')
python -m venv venv

# Activation
.\venv\Scripts\activate
```

**Mac / Linux :**

```bash
python3 -m venv venv
source venv/bin/activate
```

### Étape C : Installation en mode "Editable" (Vital)

Pour éviter les erreurs d'import (`ModuleNotFoundError: src`), nous installons le projet comme un package local. Cela permet d'importer les fichiers entre les dossiers scrapers, agents et api.

```bash
pip install -e .
```

### Étape D : Installer les dépendances des modules

Installez les librairies requises selon la partie sur laquelle vous travaillez :

```bash
# Pour le Scraping et la Data
pip install -r src/scrapers/requirements.txt

# Pour les utilitaires de diagnostic BDD
pip install -r src/utils/requirements.txt
```

### Étape E : Configuration des secrets (.env)

1. Créez un fichier `.env` à la racine du projet
2. Copiez-y le contenu ci-dessous (mots de passe configurés pour Docker local) :

```ini
# --- CONFIGURATION AEROWISE ---
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin_password
POSTGRES_DB=aerowise_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5433

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password_graph

QDRANT_HOST=localhost
QDRANT_PORT=6333

# Ajoutez vos clés API ici
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
```

---

## 3. Lancement de l'Infrastructure

Toutes les bases de données tournent sous Docker.

```bash
docker-compose up -d
```

⚠️ Le premier lancement peut être long (téléchargement des images).

**Vérification :** Pour s'assurer que les bases répondent bien, lancez le script de diagnostic :

```bash
python src/utils/check_db.py
```

✅ Vous devez obtenir 3 succès.

---

## 4. Structure du Projet

L'architecture suit une logique modulaire :

```
data/                       # Stockage local (Ignoré par Git)
├── 1_bronze/              # Données brutes (HTML, PDF)
├── 2_silver/              # Données nettoyées (Markdown, JSON)
└── 3_gold/                # Données enrichies (Vecteurs)

docker/                     # Fichiers de configuration Infra

src/                        # Code source Python
├── scrapers/              # Modules de collecte (1 dossier par site)
├── processors/            # Modules de transformation (OCR, Chunking)
├── agents/                # Logique IA et Chatbot
├── api/                   # Serveur Backend (FastAPI)
└── utils/                 # Scripts transverses

frontend/                   # Applications Web et Mobile
```

---

## 5. Utilisation : Lancer un Scraper

Grâce à l'installation en mode package, vous pouvez lancer les scripts depuis la racine.

**Exemple : Lancer le scraper iNaturalist**

```bash
python src/scrapers/inaturalist/main.py
```

---

## 6. Dépannage (FAQ)

### Erreur : "L'exécution de scripts est désactivée sur ce système" (PowerShell)

**Solution :** Windows bloque l'activation du venv par sécurité. Lancez cette commande (une seule fois) :

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Erreur : "ModuleNotFoundError: No module named 'src'"

**Solution :** Vous avez oublié l'étape C. Lancez `pip install -e .` à la racine.

### Erreur : Neo4j "ClientError: ... already running" ou pid:7

**Solution :** Neo4j n'a pas été arrêté proprement.

```bash
docker-compose down -v  # Attention, supprime les données de la base
docker-compose up -d
```

**Note :** L'option `init: true` a été ajoutée au docker-compose pour éviter cela.

### Erreur : Connexion BDD refusée (byte 0xe9)

**Solution :** Vérifiez que vous n'avez pas un autre Postgres local qui tourne sur le port 5432. AeroWise utilise le port 5433 pour éviter les conflits.