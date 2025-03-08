import random
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request
from db import get_db_connection

vis_bp = Blueprint('vis', __name__)

@vis_bp.route('/importCSV')
def import_csv():
    return render_template('importCSV.html')

@vis_bp.route('/graphique')
def graphique():
    labels = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai']
    cases = [random.randint(1, 50) for _ in labels]
    return render_template('graphique.html', labels=labels, cases=cases)

@vis_bp.route('/world-map')
def world_map():
    country = request.args.get('country', 'all')
    date_range = request.args.get('date_range', 'all')
    data_type = request.args.get('data_type', 'total_cases')
    
    connection = get_db_connection()
    if connection is None:
        return "⚠️ Erreur de connexion à la base de données", 500
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute("SELECT DISTINCT location FROM monkeypox_data ORDER BY location;")
    countries = [row['location'] for row in cursor.fetchall()]
    
    conditions = []
    params = []
    
    if country != 'all':
        conditions.append("location = %s")
        params.append(country)
    
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
    
    query = "SELECT * FROM monkeypox_data"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    cursor.execute(query, params)
    all_data = cursor.fetchall()
    
    # Récupérer la donnée la plus récente pour chaque pays
    countries_latest_data = {}
    for row in all_data:
        country_name = row['location']
        row_date = row['date']
        if country_name not in countries_latest_data or row_date > countries_latest_data[country_name]['date']:
            countries_latest_data[country_name] = row

    countries_data = {}
    for country_name, row in countries_latest_data.items():
        iso = row['iso_code']
        countries_data[iso if iso else f"country_{len(countries_data)}"] = {
            'total_cases': row.get('total_cases') or 0,
            'total_deaths': row.get('total_deaths') or 0,
            'new_cases': row.get('new_cases') or 0,
            'new_deaths': row.get('new_deaths') or 0,
            'date': row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], datetime) else str(row['date']),
            'country_name': country_name
        }
    
    total_cases = sum(row.get('total_cases') or 0 for row in countries_latest_data.values())
    total_deaths = sum(row.get('total_deaths') or 0 for row in countries_latest_data.values())
    
    dates = [row['date'] for row in countries_latest_data.values() if row['date']]
    last_update = max(dates) if dates else datetime.now()
    last_update_formatted = last_update.strftime('%d/%m/%Y') if isinstance(last_update, datetime) else str(last_update)
    
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
