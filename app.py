from flask import Flask, render_template, request, redirect, url_for, jsonify
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
    
# Fonction auxiliaire pour mapper les pays à leurs continents
def get_continent(country):
    # Dictionnaire simplifié des pays et de leurs continents
    continents = {
        'Europe': ['Royaume-Uni', 'Espagne', 'France', 'Allemagne', 'Italie', 'Portugal', 'Pays-Bas', 'Belgique', 'Suisse', 'Suède', 'Norvège', 'Finlande', 'Danemark', 'Autriche', 'Pologne', 'République tchèque', 'Hongrie', 'Grèce', 'Irlande', 'Roumanie'],
        'Amérique du Nord': ['États-Unis', 'Canada', 'Mexique', 'Panama', 'Costa Rica', 'Guatemala', 'Honduras', 'Nicaragua', 'El Salvador', 'Belize'],
        'Amérique du Sud': ['Brésil', 'Argentine', 'Chili', 'Colombie', 'Pérou', 'Équateur', 'Venezuela', 'Bolivie', 'Paraguay', 'Uruguay'],
        'Asie': ['Chine', 'Japon', 'Inde', 'Corée du Sud', 'Thaïlande', 'Vietnam', 'Indonésie', 'Philippines', 'Malaisie', 'Singapour'],
        'Afrique': ['Afrique du Sud', 'Nigeria', 'Égypte', 'Maroc', 'Algérie', 'Kenya', 'Ghana', 'Éthiopie', 'Tanzanie', 'Ouganda'],
        'Océanie': ['Australie', 'Nouvelle-Zélande', 'Papouasie-Nouvelle-Guinée', 'Fidji', 'Samoa', 'Tonga', 'Vanuatu', 'Îles Salomon', 'Kiribati', 'Tuvalu']
    }
    
    for continent, countries in continents.items():
        if country in countries:
            return continent
    
    # Par défaut, si le pays n'est pas trouvé
    return "Autre"

# Route pour remplacer votre route "/graphique" existante
@app.route('/graphique')
def graphique():
    return render_template('graphiques.html')

# Route pour récupérer la liste des pays
@app.route('/api/countries')
def get_countries():
    connection = get_db_connection()
    if connection is None:
        return jsonify([]), 500
    
    cursor = connection.cursor()
    cursor.execute("SELECT DISTINCT location FROM monkeypox_data ORDER BY location")
    countries = [row[0] for row in cursor.fetchall()]
    
    # Éliminer les doublons potentiels
    unique_countries = list(set(countries))
    unique_countries.sort()
    
    cursor.close()
    connection.close()
    
    return jsonify(unique_countries)

# Route pour les données du graphique camembert
@app.route('/api/pie-data')
def get_pie_data():
    metric = request.args.get('metric', 'total_cases')
    view_type = request.args.get('view_type', 'continent')
    
    # S'assurer que la métrique est valide pour éviter les injections SQL
    valid_metrics = ['total_cases', 'total_deaths', 'cases_per_million']
    if metric not in valid_metrics:
        metric = 'total_cases'  # Métrique par défaut
    
    # Utiliser la métrique dans la colonne appropriée
    metric_column = metric
    if metric == 'cases_per_million':
        metric_column = 'total_cases_per_million'
    
    connection = get_db_connection()
    if connection is None:
        return jsonify({"labels": [], "values": []}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    if view_type == 'continent':
        # Récupérer les données les plus récentes pour chaque pays
        query = f"""
        SELECT t1.location, t1.{metric_column}
        FROM monkeypox_data t1
        INNER JOIN (
            SELECT location, MAX(date) as latest_date
            FROM monkeypox_data
            GROUP BY location
        ) t2 ON t1.location = t2.location AND t1.date = t2.latest_date
        WHERE t1.{metric_column} IS NOT NULL
        """
        
        cursor.execute(query)
        data = cursor.fetchall()
        
        # Dictionnaire pour stocker la correspondance pays -> continent
        country_to_continent = {}
        
        # Regrouper par continent avec nettoyage des noms
        continent_data = {}
        for row in data:
            country = row['location'].strip()  # Supprimer les espaces superflus
            value = float(row[metric_column] or 0)
            
            # Ignorer les entrées comme "World" ou "North America" qui ne sont pas des pays
            if country.lower() in ['world', 'global', 'international']:
                continue
                
            # Filtrer les entrées qui sont déjà des continents
            if country.lower() in ['north america', 'south america', 'europe', 'asia', 'africa', 'oceania']:
                continue
            
            # Déterminer le continent
            continent = get_continent(country)
            
            # Stocker la correspondance pays -> continent
            country_to_continent[country] = continent
            
            if continent in continent_data:
                continent_data[continent] += value
            else:
                continent_data[continent] = value
        
        # Convertir en listes pour le graphique
        labels = list(continent_data.keys())
        values = list(continent_data.values())
        
    else:  # top-countries
        # Récupérer tous les pays (pas les continents ou régions comme "World")
        query = f"""
        SELECT t1.location, t1.{metric_column}
        FROM monkeypox_data t1
        INNER JOIN (
            SELECT location, MAX(date) as latest_date
            FROM monkeypox_data
            GROUP BY location
        ) t2 ON t1.location = t2.location AND t1.date = t2.latest_date
        WHERE t1.{metric_column} IS NOT NULL
        """
        
        cursor.execute(query)
        all_data = cursor.fetchall()
        
        # Nettoyer et dédupliquer les données
        country_data = {}
        
        for row in all_data:
            # Nettoyer le nom du pays
            country = row['location'].strip()
            value = float(row[metric_column] or 0)
            
            # Ignorer les entrées comme "World" ou "North America" qui ne sont pas des pays
            if country.lower() in ['world', 'global', 'international', 
                               'north america', 'south america', 'europe', 
                               'asia', 'africa', 'oceania']:
                continue
            
            # Normaliser certains noms de pays qui pourraient avoir des variations
            lower_country = country.lower()
            if 'united states' in lower_country or 'usa' in lower_country or 'u.s.a' in lower_country:
                country = 'United States'
            elif 'united kingdom' in lower_country or 'uk' in lower_country or 'u.k' in lower_country:
                country = 'United Kingdom'
            elif 'france' in lower_country:
                country = 'France'
            
            # Agréger les valeurs par pays normalisé
            if country in country_data:
                country_data[country] += value
            else:
                country_data[country] = value
        
        # Trier par valeur et prendre les 5 premiers
        sorted_countries = sorted(country_data.items(), key=lambda x: x[1], reverse=True)[:5]
        
        labels = [country for country, _ in sorted_countries]
        values = [value for _, value in sorted_countries]
    
    cursor.close()
    connection.close()
    
    return jsonify({"labels": labels, "values": values})

# Route pour les données du graphique linéaire
@app.route('/api/line-data')
def get_line_data():
    data_type = request.args.get('data_type', 'total_cases')
    time_range = request.args.get('time_range', '1y')
    location = request.args.get('location', 'all')
    
    connection = get_db_connection()
    if connection is None:
        return jsonify({"dates": [], "datasets": []}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    # Déterminer la date de début en fonction de la plage de temps
    start_date = None
    now = datetime.now()
    
    if time_range == '3m':
        start_date = now - timedelta(days=90)
    elif time_range == '6m':
        start_date = now - timedelta(days=180)
    elif time_range == '1y':
        start_date = now - timedelta(days=365)
    elif time_range == '2022':
        start_date = datetime(2022, 1, 1)
    # Sinon, toutes les données disponibles
    
    # Construire la condition de date
    date_condition = ""
    if start_date:
        date_condition = f"WHERE date >= '{start_date.strftime('%Y-%m-%d')}'"
    
    # Préparer les données
    if location == 'all':
        # Données mondiales
        query = f"""
        SELECT date, SUM({data_type}) as value
        FROM monkeypox_data
        {date_condition}
        GROUP BY date
        ORDER BY date
        """
        
        cursor.execute(query)
        data = cursor.fetchall()
        
        dates = [row['date'].strftime('%Y-%m-%d') for row in data]
        values = [float(row['value'] or 0) for row in data]
        
        datasets = [{
            'label': 'Monde',
            'data': values
        }]
        
    elif location == 'top5':
        # Top 5 des pays les plus touchés
        # D'abord, identifier les 5 pays avec le plus de cas
        top_query = f"""
        SELECT location, MAX({data_type}) as max_value
        FROM monkeypox_data
        GROUP BY location
        ORDER BY max_value DESC
        LIMIT 5
        """
        
        cursor.execute(top_query)
        top_countries = [row['location'] for row in cursor.fetchall()]
        
        # Ensuite, récupérer les données temporelles pour chaque pays
        datasets = []
        
        for country in top_countries:
            query = f"""
            SELECT date, {data_type} as value
            FROM monkeypox_data
            WHERE location = %s {' AND ' + date_condition.replace('WHERE', '') if date_condition else ''}
            ORDER BY date
            """
            
            cursor.execute(query, (country,))
            country_data = cursor.fetchall()
            
            if country_data:
                dates = [row['date'].strftime('%Y-%m-%d') for row in country_data]
                values = [float(row['value'] or 0) for row in country_data]
                
                datasets.append({
                    'label': country,
                    'data': values
                })
        
    else:  # 'continent'
        # Données par continent
        # Récupérer tous les pays et leurs données
        query = f"""
        SELECT location, date, {data_type} as value
        FROM monkeypox_data
        {date_condition}
        ORDER BY date, location
        """
        
        cursor.execute(query)
        all_data = cursor.fetchall()
        
        # Regrouper par continent et par date
        continent_data = {}
        dates_set = set()
        
        for row in all_data:
            country = row['location']
            date = row['date'].strftime('%Y-%m-%d')
            value = float(row['value'] or 0)
            
            # Déterminer le continent
            continent = get_continent(country)
            
            dates_set.add(date)
            
            if continent not in continent_data:
                continent_data[continent] = {}
                
            if date in continent_data[continent]:
                continent_data[continent][date] += value
            else:
                continent_data[continent][date] = value
        
        # Convertir en format pour Chart.js
        dates = sorted(list(dates_set))
        datasets = []
        
        for continent, data in continent_data.items():
            values = [data.get(date, 0) for date in dates]
            
            datasets.append({
                'label': continent,
                'data': values
            })
    
    cursor.close()
    connection.close()
    
    return jsonify({"dates": dates, "datasets": datasets})

# Route pour les données du graphique à barres
@app.route('/api/bar-data')
def get_bar_data():
    comparison = request.args.get('comparison', 'cases_deaths')
    region = request.args.get('region', 'all')
    count = int(request.args.get('count', 5))
    
    connection = get_db_connection()
    if connection is None:
        return jsonify({"labels": [], "datasets": []}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    # Filtrer par région si nécessaire
    region_condition = ""
    if region != 'all':
        # Récupérer les pays de la région
        region_countries = []
        if region == 'europe':
            region_countries = ['Royaume-Uni', 'Espagne', 'France', 'Allemagne', 'Italie', 'Portugal', 'Pays-Bas', 'Belgique', 'Suisse', 'Suède', 'Norvège']
        elif region == 'north_america':
            region_countries = ['États-Unis', 'Canada', 'Mexique']
        elif region == 'south_america':
            region_countries = ['Brésil', 'Argentine', 'Chili', 'Colombie', 'Pérou']
        elif region == 'asia':
            region_countries = ['Chine', 'Japon', 'Inde', 'Corée du Sud', 'Thaïlande']
        elif region == 'africa':
            region_countries = ['Afrique du Sud', 'Nigeria', 'Égypte', 'Maroc', 'Algérie']
        elif region == 'oceania':
            region_countries = ['Australie', 'Nouvelle-Zélande']
        
        # Construire la condition SQL
        if region_countries:
            region_condition = f"WHERE location IN ({', '.join(['%s'] * len(region_countries))})"
    
    # Récupérer les données en fonction de la comparaison
    if comparison == 'cases_deaths':
        # Cas et décès
        query = f"""
        SELECT location, MAX(total_cases) as cases, MAX(total_deaths) as deaths
        FROM monkeypox_data
        {region_condition}
        GROUP BY location
        ORDER BY cases DESC
        LIMIT %s
        """
        
        params = []
        if region_countries:
            params.extend(region_countries)
        params.append(count)
        
        cursor.execute(query, tuple(params))
        data = cursor.fetchall()
        
        countries = [row['location'] for row in data]
        cases = [float(row['cases'] or 0) for row in data]
        deaths = [float(row['deaths'] or 0) for row in data]
        
        datasets = [
            {
                'label': 'Total des cas',
                'data': cases
            },
            {
                'label': 'Total des décès',
                'data': deaths
            }
        ]
        
    elif comparison == 'per_million':
        # Cas par million d'habitants
        query = f"""
        SELECT location, MAX(total_cases_per_million) as cases_per_million
        FROM monkeypox_data
        {region_condition}
        GROUP BY location
        ORDER BY cases_per_million DESC
        LIMIT %s
        """
        
        params = []
        if region_countries:
            params.extend(region_countries)
        params.append(count)
        
        cursor.execute(query, tuple(params))
        data = cursor.fetchall()
        
        countries = [row['location'] for row in data]
        values = [float(row['cases_per_million'] or 0) for row in data]
        
        datasets = [
            {
                'label': 'Cas par million d\'habitants',
                'data': values
            }
        ]
        
    else:  # growth_rate
        # Taux de croissance
        # Calculer le taux de croissance comme la différence entre le dernier jour et 7 jours avant
        query = f"""
        SELECT t1.location, 
               (t1.total_cases - t2.total_cases) / t2.total_cases * 100 as growth_rate
        FROM 
            (SELECT location, MAX(date) as latest_date, total_cases
             FROM monkeypox_data
             GROUP BY location) t1
        JOIN 
            (SELECT location, MAX(date) as week_before_date, total_cases
             FROM monkeypox_data
             WHERE date <= DATE_SUB((SELECT MAX(date) FROM monkeypox_data), INTERVAL 7 DAY)
             GROUP BY location) t2
        ON t1.location = t2.location
        {region_condition.replace('WHERE', 'AND') if region_condition else ''}
        WHERE t2.total_cases > 0
        ORDER BY growth_rate DESC
        LIMIT %s
        """
        
        params = []
        if region_countries:
            params.extend(region_countries)
        params.append(count)
        
        cursor.execute(query, tuple(params))
        data = cursor.fetchall()
        
        countries = [row['location'] for row in data]
        values = [float(row['growth_rate'] or 0) for row in data]
        
        datasets = [
            {
                'label': 'Taux de croissance hebdomadaire (%)',
                'data': values
            }
        ]
    
    cursor.close()
    connection.close()
    
    return jsonify({"labels": countries, "datasets": datasets})

if __name__ == '__main__':
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.run(debug=True)
