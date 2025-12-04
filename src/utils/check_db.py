import psycopg2
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
import time

print("--- DIAGNOSTIC DES BASES DE DONNÉES ---")

# 1. TEST POSTGRESQL (PostGIS)
try:
    print("Tentative de connexion à PostGIS...", end=" ")
    conn = psycopg2.connect(
        dbname="aerowise_db",
        user="admin",
        password="admin_password",
        host="localhost",
        port="5433"
    )
    # On vérifie si l'extension spatiale est bien là
    cur = conn.cursor()
    cur.execute("SELECT PostGIS_Version();")
    version = cur.fetchone()[0]
    print(f"SUCCÈS ! (Version: {version})")
    conn.close()
except Exception as e:
    print(f"\nÉCHEC PostGIS : {e}")

# 2. TEST QDRANT (Vecteurs)
try:
    print("⏳ Tentative de connexion à Qdrant...", end=" ")
    client = QdrantClient(host="localhost", port=6333)
    collections = client.get_collections()
    print(f"SUCCÈS ! (Qdrant répond, {len(collections.collections)} collections)")
except Exception as e:
    print(f"\nÉCHEC Qdrant : {e}")

# 3. TEST NEO4J (Graphe)
try:
    print("Tentative de connexion à Neo4j...", end=" ")
    # On attend un peu car Neo4j est lent à démarrer
    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri, auth=("neo4j", "password_graph"))
    driver.verify_connectivity()
    print("SUCCÈS ! (Connecté au Graphe)")
    driver.close()
except Exception as e:
    print(f"\nÉCHEC Neo4j : {e}")
    print(" Conseil : Neo4j met parfois 30sec à démarrer. Réessaie dans un instant.")

print("---------------------------------------")