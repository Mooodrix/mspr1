from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import pandas as pd
import os
import random
from flask_paginate import Pagination, get_page_parameter
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

# Configuration MySQL
config = {
    'host': 'mysql-10befa8c-keskoum120-db6d.b.aivencloud.com',
    'port': 27381,
    'user': 'avnadmin',
    'password': 'AVNS_AEfYMTwHdCFIzRZjyoS',
    'database': 'monkeypox_db',
    'ssl_ca': 'aiven-ca-cert.pem',
    'connect_timeout': 10
}

# Colonnes attendues dans le CSV
EXPECTED_COLUMNS = {
    "location", "iso_code", "date", "total_cases", "total_deaths",
    "new_cases", "new_deaths", "new_cases_smoothed", "new_deaths_smoothed",
    "new_cases_per_million", "total_cases_per_million", "new_cases_smoothed_per_million",
    "new_deaths_per_million", "total_deaths_per_million", "new_deaths_smoothed_per_million"
}

# Fonction pour se connecter à la BDD
def get_db_connection():
    try:
        return mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        print(f"⚠️ Erreur de connexion MySQL: {err}")
        return None

# filepath: /c:/Users/julie/Documents/mspr1/app.py
# Route principale : Afficher les données
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/tableau')
def tableau():
    sort_by = request.args.get('sort_by', 'date')  # Trier par défaut par date
    order = request.args.get('order', 'desc')  # Trier par défaut en décroissant
    page = int(request.args.get('page', 1))  # Page actuelle (par défaut 1)
    per_page = 20  # Nombre d'éléments par page
    offset = (page - 1) * per_page

    valid_columns = {"location", "iso_code", "date", "total_cases", "total_deaths"}
    if sort_by not in valid_columns:
        sort_by = "date"  # Sécurité : si mauvais paramètre, on remet date

    order_sql = "DESC" if order == "desc" else "ASC"

    connection = get_db_connection()
    if connection is None:
        return "Erreur de connexion à la base de données", 500

    cursor = connection.cursor(dictionary=True)
    
    # Récupérer le nombre total d'entrées
    cursor.execute("SELECT COUNT(*) AS total FROM monkeypox_data;")
    total_entries = cursor.fetchone()["total"]
    total_pages = (total_entries // per_page) + (1 if total_entries % per_page > 0 else 0)
    
    # Récupérer les données paginées et triées
    query = f"SELECT * FROM monkeypox_data ORDER BY {sort_by} {order_sql} LIMIT {per_page} OFFSET {offset};"
    cursor.execute(query)
    data = cursor.fetchall()
    
    cursor.close()
    connection.close()

    return render_template('Tableau.html', data=data, page=page, total_pages=total_pages, sort_by=sort_by, order=order)

# Route pour ajouter une nouvelle entrée
@app.route('/ajout')
def ajout():
    return render_template('Ajout.html')

# Route pour supprimer une entrée
@app.route('/delete/<int:id>')
def delete_entry(id):
    connection = get_db_connection()
    if connection is None:
        return "⚠️ Erreur de connexion à la base de données", 500

    cursor = connection.cursor()
    cursor.execute("DELETE FROM monkeypox_data WHERE id = %s", (id,))
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('index'))

# Route pour modifier une entrée
@app.route('/edit/<int:id>', methods=['POST'])
def edit_entry(id):
    location = request.form['location']
    iso_code = request.form['iso_code']
    date = request.form['date']
    total_cases = request.form['total_cases']

    connection = get_db_connection()
    if connection is None:
        return "⚠️ Erreur de connexion à la base de données", 500

    cursor = connection.cursor()
    cursor.execute("""
        UPDATE monkeypox_data 
        SET location = %s, iso_code = %s, date = %s, total_cases = %s
        WHERE id = %s
    """, (location, iso_code, date, total_cases, id))
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('index'))

@app.route('/importCSV')
def import_csv():
    return render_template('importCSV.html')
    
# Exemple de données statiques pour le graphique (tu peux les récupérer de ta base de données)
@app.route('/graphique')
def graphique():
    # Exemple de labels et de données
    labels = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai']
    cases = [random.randint(1, 50) for _ in labels]  # Générer des nombres aléatoires pour les cas

    # Rendre la page avec les données
    return render_template('graphique.html', labels=labels, cases=cases)

@app.route('/world-map')
def world_map():
    # Obtenir les paramètres de filtre depuis l'URL
    country = request.args.get('country', 'all')
    date_range = request.args.get('date_range', 'all')
    data_type = request.args.get('data_type', 'total_cases')
    
    # Établir une connexion à la base de données
    connection = get_db_connection()
    if connection is None:
        return "⚠️ Erreur de connexion à la base de données", 500

    cursor = connection.cursor(dictionary=True)
    
    # Récupérer la liste des pays uniques
    cursor.execute("SELECT DISTINCT location FROM monkeypox_data ORDER BY location;")
    countries = [row['location'] for row in cursor.fetchall()]
    
    # Construire les conditions de filtrage
    conditions = []
    params = []
    
    if country != 'all':
        conditions.append("location = %s")
        params.append(country)
    
    # Gérer les filtres de date
    if date_range != 'all':
        today = datetime.now()
        if date_range == 'last-week':
            start_date = today - timedelta(days=7)
        elif date_range == 'last-month':
            start_date = today - timedelta(days=30)
        elif date_range == 'last-year':
            start_date = today - timedelta(days=365)
        
        conditions.append("date >= %s")
        params.append(start_date.strftime('%Y-%m-%d'))
    
    # Construire la requête SQL
    query = "SELECT * FROM monkeypox_data"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    cursor.execute(query, params)
    all_data = cursor.fetchall()
    
    # Regrouper les données par pays et obtenir l'entrée la plus récente pour chaque pays
    countries_latest_data = {}
    for row in all_data:
        country_name = row['location']
        date = row['date']
        
        # Si ce pays n'est pas dans notre dictionnaire ou si cette entrée est plus récente, mettre à jour
        if country_name not in countries_latest_data or date > countries_latest_data[country_name]['date']:
            countries_latest_data[country_name] = row
    
    # Maintenant, convertir au format nécessaire pour la carte
    # Utiliser le nom du pays comme clé au lieu du code ISO
    countries_data = {}
    
    for country_name, row in countries_latest_data.items():
        iso = row['iso_code']
        # Créer une entrée avec le nom du pays
        countries_data[iso if iso else f"country_{len(countries_data)}"] = {
            'total_cases': row['total_cases'] or 0,
            'total_deaths': row['total_deaths'] or 0,
            'new_cases': row['new_cases'] or 0,
            'new_deaths': row['new_deaths'] or 0,
            'date': row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], datetime) else str(row['date']),
            'country_name': country_name
        }
    
    # Calculer les statistiques basées sur les données filtrées
    total_cases = sum(row['total_cases'] or 0 for row in countries_latest_data.values())
    total_deaths = sum(row['total_deaths'] or 0 for row in countries_latest_data.values())
    
    # Trouver la date de mise à jour la plus récente
    dates = [row['date'] for row in countries_latest_data.values() if row['date']]
    last_update = max(dates) if dates else datetime.now()
    
    # Formater la date
    last_update_formatted = last_update.strftime('%d/%m/%Y') if isinstance(last_update, datetime) else str(last_update)
    
    # Préparer les statistiques
    stats = {
        'total_cases': "{:,}".format(int(total_cases)).replace(',', ' '),
        'total_deaths': "{:,}".format(int(total_deaths)).replace(',', ' '),
        'countries_count': len(countries_data),
        'last_update': last_update_formatted
    }
    
    cursor.close()
    connection.close()
    
    return render_template('world-map.html', 
                         countries=countries,
                         countries_data=json.dumps(countries_data),
                         stats=stats)

if __name__ == '__main__':
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.run(debug=True)
