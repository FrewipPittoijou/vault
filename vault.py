from flask import Flask, jsonify, request
import pyodbc
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Charger la configuration depuis le fichier .env
load_dotenv()

db_url = os.getenv("DATABASE_URL")

# Extraire les informations de connexion depuis l'URL de la base de données
import urllib.parse as up
up.uses_netloc.append("postgres")
url = up.urlparse(db_url)

def get_db_connection():
    conn = pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={url.hostname};'
        f'PORT={url.port};'
        f'DATABASE={url.path[1:]};'
        f'UID={url.username};'
        f'PWD={url.password}'
    )
    return conn

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
