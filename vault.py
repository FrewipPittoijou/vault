from flask import Flask, jsonify, request
import os
from dotenv import load_dotenv
import urllib.parse as up
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient
import pyodbc

app = Flask(__name__)
load_dotenv()

# --- Variables pour SQL (si besoin) ---
db_url = os.getenv("DATABASE_URL")
parsed_url = up.urlparse(db_url)

def get_db_connection():
    # Exemple de connexion SQL standard (à adapter si nécessaire)
    conn = pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={parsed_url.hostname};'
        f'PORT={parsed_url.port or 1433};'
        f'DATABASE={parsed_url.path.lstrip("/")};'
    )
    return conn

# --- Variables pour Azure Blob ---
AZURE_STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")
AZURE_SAS_TOKEN = os.getenv("AZURE_SAS_TOKEN")
# Construction de l'URL du Storage Account
account_url = f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net"

# Nom du container utilisé pour stocker les secrets
VAULT_CONTAINER = "vault"

def get_blob_service_client():
    return BlobServiceClient(account_url=account_url, credential=AZURE_SAS_TOKEN)

def get_vault_container_client():
    blob_service_client = get_blob_service_client()
    container_client = blob_service_client.get_container_client(VAULT_CONTAINER)
    # Crée le container s'il n'existe pas encore
    try:
        container_client.create_container()
    except Exception:
        # Le container existe probablement déjà
        pass
    return container_client

# --- Endpoints pour la gestion des secrets (type Vault) ---

# Lister tous les secrets (les blobs présents dans le container)
@app.route('/secrets', methods=['GET'])
def list_secrets():
    container_client = get_vault_container_client()
    blobs = container_client.list_blobs()
    secret_names = [blob.name for blob in blobs]
    return jsonify({"secrets": secret_names})

# Récupérer le contenu d'un secret
@app.route('/secrets/<string:secret_name>', methods=['GET'])
def get_secret(secret_name):
    container_client = get_vault_container_client()
    blob_client = container_client.get_blob_client(secret_name)
    try:
        secret_data = blob_client.download_blob().readall().decode("utf-8")
    except Exception as e:
        return jsonify({"error": f"Secret '{secret_name}' introuvable ou inaccessible.", "details": str(e)}), 404
    return jsonify({"secret_name": secret_name, "value": secret_data})

# Stocker ou mettre à jour un secret
@app.route('/secrets', methods=['POST'])
def store_secret():
    data = request.json
    secret_name = data.get("name")
    secret_value = data.get("value")

    if not secret_name or not secret_value:
        return jsonify({"error": "Les champs 'name' et 'value' sont requis."}), 400

    container_client = get_vault_container_client()
    blob_client = container_client.get_blob_client(secret_name)
    blob_client.upload_blob(secret_value, overwrite=True)
    return jsonify({"message": f"Secret '{secret_name}' stocké avec succès."}), 201

# Supprimer un secret
@app.route('/secrets/<string:secret_name>', methods=['DELETE'])
def delete_secret(secret_name):
    container_client = get_vault_container_client()
    blob_client = container_client.get_blob_client(secret_name)
    try:
        blob_client.delete_blob()
    except Exception as e:
        return jsonify({"error": f"Impossible de supprimer le secret '{secret_name}'.", "details": str(e)}), 404
    return jsonify({"message": f"Secret '{secret_name}' supprimé avec succès."})

# --- Endpoints SQL existants (pour illustration) ---
@app.route('/passwords', methods=['POST'])
def store_password():
    data = request.json
    password = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO passwords (encrypted_password) VALUES (?)", (password,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Password stored successfully!"}), 201

@app.route('/passwords/<int:id>', methods=['PUT'])
def modify_password(id):
    data = request.json
    new_password = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE passwords SET encrypted_password = ? WHERE id = ?", (new_password, id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Password updated successfully!"})

@app.route('/passwords', methods=['GET'])
def get_passwords():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, encrypted_password FROM passwords")
    passwords = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify([{"id": row[0], "password": row[1]} for row in passwords])

if __name__ == '__main__':
    app.run(port=5000, debug=os.getenv("DEBUG") == "True")