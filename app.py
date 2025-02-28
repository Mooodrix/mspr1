from flask import Flask, render_template, request, redirect, url_for, jsonify
import mysql.connector
import pandas as pd
import os
import random

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

# MySQL Configuration
config = {
    'host': 'mysql-10befa8c-keskoum120-db6d.b.aivencloud.com',
    'port': 27381,
    'user': 'avnadmin',
    'password': 'AVNS_AEfYMTwHdCFIzRZjyoS',
    'database': 'monkeypox_db',
    'ssl_ca': 'aiven-ca-cert.pem',
    'connect_timeout': 10
}

# Connect to MySQL
def get_db_connection():
    try:
        return mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        print(f"⚠️ MySQL Connection Error: {err}")
        return None

# 📌 API: Fetch Monkeypox Data for Visualization
@app.route('/api/monkeypox_data', methods=['GET'])
def get_monkeypox_data():
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT location, date, total_cases, total_deaths, new_cases FROM monkeypox_data;")
    data = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return jsonify(data)

# Start Flask App
if __name__ == '__main__':
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.run(debug=True, port=5000)  # Running on port 5000
