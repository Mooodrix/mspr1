from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
import mysql.connector
import pandas as pd
import os
import random
from flask_paginate import Pagination, get_page_parameter
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import logging

app = Flask(__name__)
CORS(app)
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
    "location", "date", "total_cases", "total_deaths",
    "new_cases", "new_deaths", "new_cases_smoothed", "new_deaths_smoothed",
    "new_cases_per_million", "total_cases_per_million", "new_cases_smoothed_per_million",
    "new_deaths_per_million", "total_deaths_per_million", "new_deaths_smoothed_per_million",
    "CaseGrowthRate"
}


def setup_swagger(app):
    # URL pour accéder à la documentation Swagger
    SWAGGER_URL = '/api/docs'
    
    # URL pour accéder au fichier de spécification OpenAPI
    API_URL = '/swagger/swagger.yaml'
    
    # Créer un blueprint pour Swagger UI avec une meilleure configuration
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "Monkeypox Data API",
            'dom_id': '#swagger-ui',
            'layout': 'BaseLayout',
            'deepLinking': True,
            'showExtensions': True,
            'showCommonExtensions': True,
            'supportedSubmitMethods': ['get', 'post', 'put', 'delete', 'patch'],
            'validatorUrl': None  # Désactiver la validation externe
        }
    )
    
    # Enregistrer le blueprint dans l'application Flask
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
    
    # Mettre à jour le serveur dans la spécification Swagger
    @app.route('/swagger/swagger.yaml')
    def serve_swagger_spec():
        from flask import Response
        
        # Charger le YAML comme objet Python pour le modifier
        swagger_content = """openapi: 3.0.0
info:
  title: Monkeypox Data API
  description: API pour la gestion et l'analyse des données Monkeypox
  version: 1.3.0
servers:
  - url: /
    description: Serveur actuel
tags:
  - name: Visualisation
    description: Points d'entrée pour la visualisation des données
  - name: Informations
    description: Points d'entrée pour les informations générales
  - name: CRUD
    description: Opérations de création, lecture, mise à jour et suppression des données

paths:
  /api/pie-data:
    get:
      tags:
        - Visualisation
      summary: Récupère les données pour un graphique en camembert
      description: Fournit les données formatées pour un graphique en camembert montrant la répartition des cas/décès par continent ou pays
      parameters:
        - name: metric
          in: query
          description: Type de données à visualiser
          required: false
          schema:
            type: string
            enum: [total_cases, total_deaths, cases_per_million]
            default: total_cases
        - name: view_type
          in: query
          description: Type de visualisation
          required: false
          schema:
            type: string
            enum: [continent, top-countries]
            default: continent
      responses:
        '200':
          description: Données du graphique en camembert récupérées avec succès
          content:
            application/json:
              schema:
                type: object
                properties:
                  labels:
                    type: array
                    description: Noms des continents ou pays
                    items:
                      type: string
                    example: ["Europe", "North America", "South America", "Asia", "Africa", "Oceania"]
                  values:
                    type: array
                    description: Valeurs correspondantes pour chaque label
                    items:
                      type: number
                    example: [45, 25, 15, 8, 5, 2]
        '500':
          description: Erreur serveur lors de la récupération des données
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                    description: Message d'erreur
                    example: "Database connection failed"

  /api/line-data:
    get:
      tags:
        - Visualisation
      summary: Récupère les données pour un graphique linéaire
      description: Fournit les données formatées pour un graphique linéaire montrant l'évolution temporelle des cas ou décès
      parameters:
        - name: data_type
          in: query
          description: Type de données à visualiser
          required: false
          schema:
            type: string
            enum: [total_cases, new_cases, new_cases_smoothed]
            default: total_cases
        - name: time_range
          in: query
          description: Période de temps à analyser
          required: false
          schema:
            type: string
            enum: [3m, 6m, 1y, 2022, all]
            default: 3m
        - name: location
          in: query
          description: Zone géographique à analyser
          required: false
          schema:
            type: string
            enum: [all, top5, continent]
            default: all
      responses:
        '200':
          description: Données du graphique linéaire récupérées avec succès
          content:
            application/json:
              schema:
                type: object
                properties:
                  labels:
                    type: array
                    description: Dates pour l'axe X
                    items:
                      type: string
                    example: ["Jan 2022", "Feb 2022", "Mar 2022", "Apr 2022"]
                  datasets:
                    type: array
                    description: Jeux de données pour chaque série
                    items:
                      type: object
                      properties:
                        label:
                          type: string
                          description: Nom de la série
                          example: "World"
                        data:
                          type: array
                          description: Valeurs de la série
                          items:
                            type: number
                          example: [100, 150, 200, 180]
                        borderColor:
                          type: string
                          description: Couleur de la bordure de la ligne
                          example: "rgba(54, 162, 235, 1)"
                        backgroundColor:
                          type: string
                          description: Couleur de fond
                          example: "rgba(54, 162, 235, 0.7)"
        '500':
          description: Erreur serveur lors de la récupération des données
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                    description: Message d'erreur
                    example: "Database connection failed"

  /api/bar-data:
    get:
      tags:
        - Visualisation
      summary: Récupère les données pour un graphique à barres
      description: Fournit les données formatées pour un graphique à barres comparant différents pays
      parameters:
        - name: comparison
          in: query
          description: Type de comparaison
          required: false
          schema:
            type: string
            enum: [cases_deaths, per_million, growth_rate]
            default: cases_deaths
        - name: region
          in: query
          description: Région à filtrer
          required: false
          schema:
            type: string
            enum: [all, europe, north_america, south_america, asia, africa, oceania]
            default: all
        - name: count
          in: query
          description: Nombre de pays à afficher
          required: false
          schema:
            type: integer
            enum: [5, 10, 15, 20]
            default: 5
      responses:
        '200':
          description: Données du graphique à barres récupérées avec succès
          content:
            application/json:
              schema:
                type: object
                properties:
                  labels:
                    type: array
                    description: Noms des pays
                    items:
                      type: string
                    example: ["United States", "Brazil", "United Kingdom", "Spain", "France"]
                  datasets:
                    type: array
                    description: Jeux de données pour chaque série
                    items:
                      type: object
                      properties:
                        label:
                          type: string
                          description: Nom de la série
                          example: "Total Cases"
                        data:
                          type: array
                          description: Valeurs de la série
                          items:
                            type: number
                          example: [1000, 800, 600, 500, 400]
                        backgroundColor:
                          type: string
                          description: Couleur de fond des barres
                          example: "rgba(54, 162, 235, 0.7)"
                        borderColor:
                          type: string
                          description: Couleur de la bordure des barres
                          example: "rgba(54, 162, 235, 1)"
                        borderWidth:
                          type: integer
                          description: Largeur de la bordure
                          example: 1
        '500':
          description: Erreur serveur lors de la récupération des données
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                    description: Message d'erreur
                    example: "Database connection failed"

  /api/general-info:
    get:
      tags:
        - Informations
      summary: Récupère les informations générales sur les données Monkeypox
      description: Fournit un résumé des cas totaux, décès et date de dernière mise à jour
      responses:
        '200':
          description: Informations générales récupérées avec succès
          content:
            application/json:
              schema:
                type: object
                properties:
                  total_cases:
                    type: number
                    description: Nombre total de cas
                    example: 12500
                  total_deaths:
                    type: number
                    description: Nombre total de décès
                    example: 450
                  last_update:
                    type: string
                    description: Date de la dernière mise à jour
                    format: date
                    example: "2023-06-30"
        '500':
          description: Erreur serveur lors de la récupération des données
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                    description: Message d'erreur
                    example: "Database connection failed"

  # Documentation des opérations CRUD
  /tableau:
    get:
      tags:
        - CRUD
      summary: Affiche les données Monkeypox sous forme de tableau
      description: Récupère les données Monkeypox avec pagination et options de tri
      parameters:
        - name: sort_by
          in: query
          description: Champ pour le tri des données
          required: false
          schema:
            type: string
            enum: [location, date, total_cases, total_deaths]
            default: location
        - name: order
          in: query
          description: Ordre de tri (ascendant ou descendant)
          required: false
          schema:
            type: string
            enum: [asc, desc]
            default: asc
        - name: page
          in: query
          description: Numéro de la page à afficher
          required: false
          schema:
            type: integer
            default: 1
      responses:
        '200':
          description: Données récupérées avec succès et affichées dans un tableau
        '500':
          description: Erreur serveur lors de la récupération des données
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /ajout:
    get:
      tags:
        - CRUD
      summary: Affiche le formulaire d'ajout de données
      description: Renvoie la page HTML avec le formulaire pour ajouter une nouvelle entrée
      responses:
        '200':
          description: Formulaire d'ajout affiché avec succès
    post:
      tags:
        - CRUD
      summary: Ajoute une nouvelle entrée de données
      description: Crée une nouvelle entrée dans la base de données Monkeypox à partir des données du formulaire
      requestBody:
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                location:
                  type: string
                  description: Nom du pays ou de la région
                  example: "France"
                date:
                  type: string
                  format: date
                  description: Date de l'enregistrement (YYYY-MM-DD)
                  example: "2023-01-15"
                total_cases:
                  type: number
                  description: Nombre total de cas
                  example: 1250
              required:
                - location
                - date
                - total_cases
      responses:
        '302':
          description: Redirection vers la page du tableau après ajout réussi
        '500':
          description: Erreur serveur lors de l'ajout des données
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /delete/{id}:
    get:
      tags:
        - CRUD
      summary: Supprime une entrée de données
      description: Supprime une entrée spécifique de la base de données en fonction de son ID
      parameters:
        - name: id
          in: path
          description: ID de l'entrée à supprimer
          required: true
          schema:
            type: integer
          example: 123
      responses:
        '302':
          description: Redirection vers la page du tableau après suppression réussie
        '500':
          description: Erreur serveur lors de la suppression
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /edit/{id}:
    get:
      tags:
        - CRUD
      summary: Affiche le formulaire de modification pour une entrée spécifique
      description: Récupère les données d'une entrée spécifique et affiche un formulaire pré-rempli pour la modification
      parameters:
        - name: id
          in: path
          description: ID de l'entrée à modifier
          required: true
          schema:
            type: integer
          example: 123
        - name: sort_by
          in: query
          description: Champ pour le tri des données
          required: false
          schema:
            type: string
            default: location
        - name: order
          in: query
          description: Ordre de tri (ascendant ou descendant)
          required: false
          schema:
            type: string
            enum: [asc, desc]
            default: asc
        - name: page
          in: query
          description: Numéro de la page
          required: false
          schema:
            type: integer
            default: 1
      responses:
        '200':
          description: Formulaire de modification affiché avec succès
        '404':
          description: Entrée non trouvée
        '500':
          description: Erreur serveur lors de la récupération des données
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
    post:
      tags:
        - CRUD
      summary: Met à jour une entrée existante
      description: Modifie les données d'une entrée spécifique dans la base de données
      parameters:
        - name: id
          in: path
          description: ID de l'entrée à modifier
          required: true
          schema:
            type: integer
          example: 123
        - name: sort_by
          in: query
          description: Champ pour le tri des données après redirection
          required: false
          schema:
            type: string
            default: location
        - name: order
          in: query
          description: Ordre de tri après redirection
          required: false
          schema:
            type: string
            enum: [asc, desc]
            default: asc
        - name: page
          in: query
          description: Numéro de la page après redirection
          required: false
          schema:
            type: integer
            default: 1
      requestBody:
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                location:
                  type: string
                  description: Nom du pays ou de la région
                  example: "France"
                date:
                  type: string
                  format: date
                  description: Date de l'enregistrement (YYYY-MM-DD)
                  example: "2023-01-15"
                total_cases:
                  type: number
                  description: Nombre total de cas
                  example: 1250
              required:
                - location
                - date
                - total_cases
      responses:
        '302':
          description: Redirection vers la page du tableau après modification réussie
        '404':
          description: Entrée non trouvée
        '500':
          description: Erreur serveur lors de la mise à jour des données
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

components:
  schemas:
    Error:
      type: object
      properties:
        error:
          type: string
          description: Message d'erreur
      required:
        - error
    
    MonkeypoxData:
      type: object
      properties:
        id:
          type: integer
          description: Identifiant unique de l'entrée
          example: 123
        location:
          type: string
          description: Pays ou région
          example: "France"
        date:
          type: string
          format: date
          description: Date de l'enregistrement
          example: "2023-01-15"
        total_cases:
          type: number
          description: Nombre total de cas
          example: 1250
        total_deaths:
          type: number
          description: Nombre total de décès
          example: 45
        new_cases:
          type: number
          description: Nouveaux cas
          example: 25
        new_deaths:
          type: number
          description: Nouveaux décès
          example: 2
      required:
        - id
        - location
        - date
        - total_cases"""
        
        return Response(swagger_content, mimetype='text/yaml')

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

@app.route('/tableau', methods=['GET'])
def tableau():
    connection = get_db_connection()
    if connection is None:
        return "⚠️ Erreur de connexion à la base de données", 500

    cursor = connection.cursor(dictionary=True)

    # Récupération des paramètres de tri et de pagination
    sort_by = request.args.get('sort_by', 'location')  # Default sorting by location
    order = request.args.get('order', 'asc')  # Default order ascending
    page = int(request.args.get('page', 1))  # Default page 1

    # Limite des résultats par page
    results_per_page = 10
    offset = (page - 1) * results_per_page

    conditions = []  # Assurez-vous que conditions est toujours défini

    # Construction de la requête SQL
    query = f"""
        SELECT * FROM monkeypox_data
        WHERE location != 'World'
        {"AND " + " AND ".join(conditions) if conditions else ""}
        ORDER BY {sort_by} {order}
        LIMIT %s OFFSET %s
    """


    params = [results_per_page, offset]

    # Exécution de la requête avec tri et pagination
    cursor.execute(query, params)
    data = cursor.fetchall()

    # Récupération du nombre total de pages
    cursor.execute("SELECT COUNT(*) as count FROM monkeypox_data")
    total_records = cursor.fetchone()['count']
    total_pages = (total_records + results_per_page - 1) // results_per_page  # Calcul du nombre total de pages

    connection.close()

    return render_template("tableau.html", data=data, sort_by=sort_by, order=order, page=page, total_pages=total_pages)

# Route pour ajouter une nouvelle entrée
@app.route('/ajout', methods=['GET', 'POST'])
def ajout():
    if request.method == 'POST':
        # Récupérer les données du formulaire
        location = request.form['location']
        date = request.form['date']
        total_cases = request.form['total_cases']

        # Se connecter à la base de données
        connection = get_db_connection()
        cursor = connection.cursor()

        # Insérer les données dans la base
        cursor.execute("""
            INSERT INTO monkeypox_data (location, date, total_cases)
            VALUES (%s, %s, %s)
        """, (location, date, total_cases))
        connection.commit()

        # Fermer la connexion
        cursor.close()
        connection.close()

        # Rediriger vers une autre page après l'ajout (par exemple, vers le tableau)
        return redirect(url_for('tableau'))  # Redirige vers la page du tableau

    # Si c'est une requête GET, afficher simplement le formulaire d'ajout
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
    return redirect(url_for('tableau'))

# Route pour modifier une entrée
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_entry(id):
    # Connexion à la base de données
    connection = get_db_connection()
    if connection is None:
        return "⚠️ Erreur de connexion à la base de données", 500

    cursor = connection.cursor(dictionary=True)

    # Si la méthode est GET, récupérer les données actuelles pour pré-remplir le formulaire
    if request.method == 'GET':
        cursor.execute("SELECT * FROM monkeypox_data WHERE id = %s", (id,))
        row = cursor.fetchone()

        if row is None:
            return "⚠️ Entrée non trouvée", 404

        # Récupérer les paramètres de tri et de pagination
        sort_by = request.args.get('sort_by', 'location')  # Default sorting by location
        order = request.args.get('order', 'asc')  # Default order ascending
        page = int(request.args.get('page', 1))  # Default page 1

        # Limite des résultats par page
        results_per_page = 10
        offset = (page - 1) * results_per_page

        # Exécution de la requête avec tri et pagination
        cursor.execute(f"""
            SELECT * FROM monkeypox_data
            ORDER BY {sort_by} {order}
            LIMIT %s OFFSET %s
        """, (results_per_page, offset))

        rows = cursor.fetchall()

        # Récupérer le nombre total d'entrées pour calculer le nombre total de pages
        cursor.execute("SELECT COUNT(*) FROM monkeypox_data")
        total_rows = cursor.fetchone()['COUNT(*)']
        total_pages = (total_rows // results_per_page) + (1 if total_rows % results_per_page > 0 else 0)

        # Fermer la connexion et afficher le formulaire
        cursor.close()
        connection.close()

        # Passer les paramètres au template
        return render_template('edit_entry.html', row=row, page=page, sort_by=sort_by, order=order, total_pages=total_pages)

    # Si la méthode est POST, récupérer les nouvelles données et mettre à jour l'entrée
    if request.method == 'POST':
        location = request.form['location']
        date = request.form['date']
        total_cases = request.form['total_cases']

        cursor.execute(""" 
            UPDATE monkeypox_data 
            SET location = %s, date = %s, total_cases = %s 
            WHERE id = %s
        """, (location, date, total_cases, id))
        connection.commit()

        # Récupération des paramètres de tri et de pagination
        sort_by = request.args.get('sort_by', 'location')  # Default sorting by location
        order = request.args.get('order', 'asc')  # Default order ascending
        page = int(request.args.get('page', 1))  # Default page 1

        # Limite des résultats par page
        results_per_page = 10
        offset = (page - 1) * results_per_page

        # Exécution de la requête avec tri et pagination
        cursor.execute(f"""
            SELECT * FROM monkeypox_data
            ORDER BY {sort_by} {order}
            LIMIT %s OFFSET %s
        """, (results_per_page, offset))

        rows = cursor.fetchall()

        # Récupérer le nombre total d'entrées pour calculer le nombre total de pages
        cursor.execute("SELECT COUNT(*) FROM monkeypox_data")
        total_rows = cursor.fetchone()['COUNT(*)']
        total_pages = (total_rows // results_per_page) + (1 if total_rows % results_per_page > 0 else 0)

        cursor.close()
        connection.close()

        # Message de confirmation
        success_message = "Les données ont été mises à jour avec succès !"

        # Rediriger vers la page du tableau avec les mêmes paramètres de tri et de pagination
        return redirect(url_for('tableau', page=page, sort_by=sort_by, order=order))



@app.route('/graphique')
def graphique():
    # Exemple de labels et de données
    labels = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai']
    cases = [random.randint(1, 50) for _ in labels]  # Générer des nombres aléatoires pour les cas

    # Rendre la page avec les données
    return render_template('graphique.html', labels=labels, cases=cases)

@app.route('/api/pie-data', methods=['GET'])
def get_pie_data():
    metric = request.args.get('metric', 'total_cases')
    view_type = request.args.get('view_type', 'continent')
    
    # Connect to database
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    # Prepare response data
    result = {
        "labels": [],
        "values": []
    }
    
    try:
        if view_type == 'continent':
            # Utilisation d'une approche simplifiée basée sur le préfixe du nom du pays
            continents = {
                'Europe': ['France', 'Germany', 'United Kingdom', 'Italy', 'Spain', 'Poland', 'Netherlands', 'Belgium'],
                'North America': ['United States', 'Canada', 'Mexico'],
                'South America': ['Brazil', 'Argentina', 'Colombia', 'Chile', 'Peru'],
                'Asia': ['China', 'Japan', 'India', 'South Korea', 'Indonesia'],
                'Africa': ['South Africa', 'Nigeria', 'Egypt', 'Morocco', 'Algeria'],
                'Oceania': ['Australia', 'New Zealand']
            }
            
            # Pour chaque continent, on récupère les données agrégées des pays correspondants
            for continent, countries in continents.items():
                if countries:
                    placeholders = ', '.join(['%s'] * len(countries))
                    query = f"""
                        SELECT SUM({metric}) as total 
                        FROM monkeypox_data 
                        WHERE location IN ({placeholders})
                        AND {metric} IS NOT NULL
                    """
                    cursor.execute(query, countries)
                    data = cursor.fetchone()
                    if data and data['total'] is not None:
                        result["labels"].append(continent)
                        result["values"].append(float(data['total']))
        
        elif view_type == 'top-countries':
            # Extraire la liste des entités à exclure directement de la base de données
            # D'abord, obtenir une liste de toutes les entités qui sont clairement des continents/régions
            known_continents = ['World', 'Europe', 'North America', 'South America', 
                               'Asia', 'Africa', 'Oceania', 'European Union', 
                               'International', 'Low income', 'Lower middle income', 
                               'Upper middle income', 'High income']
            
            placeholders = ', '.join(['%s'] * len(known_continents))
            
            # Requête pour obtenir les pays (avec la plus haute valeur par pays)
            query = f"""
                SELECT location, MAX({metric}) as value 
                FROM monkeypox_data 
                WHERE location NOT IN ({placeholders})
                AND {metric} IS NOT NULL
                GROUP BY location
                ORDER BY value DESC
                LIMIT 5
            """
            cursor.execute(query, known_continents)
            data = cursor.fetchall()
            
            for row in data:
                result["labels"].append(row['location'])
                result["values"].append(float(row['value']))
            
            # Si nous n'avons pas assez de résultats, afficher un message
            if len(result["labels"]) == 0:
                print("Attention: Aucun pays trouvé dans la base de données")
                # Voici les noms de toutes les entités pour déboguer
                cursor.execute("SELECT DISTINCT location FROM monkeypox_data ORDER BY location")
                all_locations = [row['location'] for row in cursor.fetchall()]
                print("Locations disponibles:", all_locations)
    
        # Si aucune donnée n'a été trouvée, ajouter des données factices pour éviter une erreur
        if not result["labels"]:
            # Ajouter des données de démonstration
            result["labels"] = ["Pas de données disponibles"]
            result["values"] = [100]
    
    except Exception as e:
        print(f"Error in /api/pie-data: {e}")
        # Renvoyer des données de démonstration en cas d'erreur
        if view_type == 'continent':
            result["labels"] = ["Europe", "North America", "South America", "Asia", "Africa", "Oceania"]
            result["values"] = [45, 25, 15, 8, 5, 2]
        else:
            result["labels"] = ["États-Unis", "Brésil", "Royaume-Uni", "Espagne", "France"]
            result["values"] = [25, 15, 12, 10, 8]
    
    finally:
        cursor.close()
        connection.close()
    
    return jsonify(result)

# Add routes for the other chart types
@app.route('/api/line-data', methods=['GET'])
def get_line_data():
    data_type = request.args.get('data_type', 'total_cases')
    time_range = request.args.get('time_range', '3m')
    location = request.args.get('location', 'all')
    
    # Connect to database
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    # Define date range
    date_limit = None
    if time_range == '3m':
        date_limit = "DATE_SUB(CURDATE(), INTERVAL 3 MONTH)"
    elif time_range == '6m':
        date_limit = "DATE_SUB(CURDATE(), INTERVAL 6 MONTH)"
    elif time_range == '1y':
        date_limit = "DATE_SUB(CURDATE(), INTERVAL 1 YEAR)"
    elif time_range == '2022':
        date_limit = "'2022-01-01'"
    
    datasets = []
    labels = []
    
    try:
        if location == 'all':
            # Get data for the entire world
            query = f"""
                SELECT date, {data_type}
                FROM monkeypox_data
                WHERE location = 'World' 
                {f"AND date >= {date_limit}" if date_limit else ""}
                ORDER BY date
            """
            cursor.execute(query)
            data = cursor.fetchall()
            
            # Extract dates for labels
            labels = [row['date'].strftime('%b %Y') for row in data]
            
            # Create dataset
            datasets.append({
                "label": "World",
                "data": [float(row[data_type]) if row[data_type] is not None else 0 for row in data],
                "borderColor": "rgba(54, 162, 235, 1)",
                "backgroundColor": "rgba(54, 162, 235, 0.7)"
            })
            
        elif location == 'top5':
            # First, find the top 5 countries
            query = f"""
                SELECT location, MAX({data_type}) as max_value
                FROM monkeypox_data
                WHERE location != 'World'
                GROUP BY location
                ORDER BY max_value DESC
                LIMIT 5
            """
            cursor.execute(query)
            top_countries = [row['location'] for row in cursor.fetchall()]
            
            # Now get timeline data for each country
            colors = [
                ["rgba(255, 99, 132, 0.7)", "rgba(255, 99, 132, 1)"],
                ["rgba(54, 162, 235, 0.7)", "rgba(54, 162, 235, 1)"],
                ["rgba(255, 206, 86, 0.7)", "rgba(255, 206, 86, 1)"],
                ["rgba(75, 192, 192, 0.7)", "rgba(75, 192, 192, 1)"],
                ["rgba(153, 102, 255, 0.7)", "rgba(153, 102, 255, 1)"]
            ]
            
            # Get all dates first to ensure alignment
            date_query = f"""
                SELECT DISTINCT date
                FROM monkeypox_data
                {f"WHERE date >= {date_limit}" if date_limit else ""}
                ORDER BY date
            """
            cursor.execute(date_query)
            dates = [row['date'] for row in cursor.fetchall()]
            labels = [date.strftime('%b %Y') for date in dates]
            
            for i, country in enumerate(top_countries):
                query = f"""
                    SELECT date, {data_type}
                    FROM monkeypox_data
                    WHERE location = %s
                    {f"AND date >= {date_limit}" if date_limit else ""}
                    ORDER BY date
                """
                cursor.execute(query, (country,))
                country_data = cursor.fetchall()
                
                # Create a dictionary for quick lookup
                country_values = {row['date']: row[data_type] for row in country_data}
                
                # Create dataset with aligned dates
                data_points = []
                for date in dates:
                    if date in country_values and country_values[date] is not None:
                        data_points.append(float(country_values[date]))
                    else:
                        data_points.append(None)  # Handle missing data points
                
                datasets.append({
                    "label": country,
                    "data": data_points,
                    "borderColor": colors[i % len(colors)][1],
                    "backgroundColor": colors[i % len(colors)][0]
                })
        
        elif location == 'continent':
            # Similar implementation to top5, but for continents
            # This would require mapping countries to continents in your data
            pass  # Placeholder - implement based on your data structure
    
    except Exception as e:
        print(f"Error in /api/line-data: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        cursor.close()
        connection.close()
    
    return jsonify({
        "labels": labels,
        "datasets": datasets
    })

@app.route('/api/bar-data', methods=['GET'])
def get_bar_data():
    comparison = request.args.get('comparison', 'cases_deaths')
    region = request.args.get('region', 'all')
    count = int(request.args.get('count', 5))
    
    # Connect to database
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    labels = []
    datasets = []
    
    try:
        # Region filtering logic would go here
        region_condition = ""
        region_params = []
        
        if region != 'all':
            # This is a simplified example - you would need to map countries to regions in your data
            pass
        
        if comparison == 'cases_deaths':
            # Get countries with highest case counts
            query = f"""
                SELECT location, 
                MAX(total_cases) as cases, 
                MAX(total_deaths) as deaths
                FROM monkeypox_data
                WHERE location != 'World' {region_condition}
                GROUP BY location
                HAVING cases IS NOT NULL
                ORDER BY cases DESC
                LIMIT %s
            """
            cursor.execute(query, region_params + [count])
            data = cursor.fetchall()
            
            labels = [row['location'] for row in data]
            
            datasets = [
                {
                    "label": "Total Cases",
                    "data": [float(row['cases']) if row['cases'] is not None else 0 for row in data],
                    "backgroundColor": "rgba(54, 162, 235, 0.7)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 1
                },
                {
                    "label": "Total Deaths",
                    "data": [float(row['deaths']) if row['deaths'] is not None else 0 for row in data],
                    "backgroundColor": "rgba(255, 99, 132, 0.7)",
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "borderWidth": 1
                }
            ]
            
        elif comparison == 'per_million':
            # Get countries with highest cases per million
            query = f"""
                SELECT location, 
                MAX(total_cases_per_million) as cases_per_million
                FROM monkeypox_data
                WHERE location != 'World' {region_condition}
                GROUP BY location
                HAVING cases_per_million IS NOT NULL
                ORDER BY cases_per_million DESC
                LIMIT %s
            """
            cursor.execute(query, region_params + [count])
            data = cursor.fetchall()
            
            labels = [row['location'] for row in data]
            
            datasets = [
                {
                    "label": "Cases per Million",
                    "data": [float(row['cases_per_million']) if row['cases_per_million'] is not None else 0 for row in data],
                    "backgroundColor": "rgba(75, 192, 192, 0.7)",
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "borderWidth": 1
                }
            ]
            
        elif comparison == 'growth_rate':
            # This would require calculating growth rates from your data
            # For now, using a placeholder implementation
            pass  # Implement based on your data structure
    
    except Exception as e:
        print(f"Error in /api/bar-data: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        cursor.close()
        connection.close()
    
    return jsonify({
        "labels": labels,
        "datasets": datasets
    })

@app.route('/api/general-info', methods=['GET'])
def get_general_info():
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)
    
    query = """
        SELECT 
            SUM(total_cases) as total_cases,
            SUM(total_deaths) as total_deaths,
            DATE(MAX(date)) as last_update
        FROM monkeypox_data
    """
    cursor.execute(query)
    data = cursor.fetchone()
    
    cursor.close()
    connection.close()
    
    return jsonify(data)

if __name__ == '__main__':
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    
    # Créer le répertoire swagger si il n'existe pas
    if not os.path.exists("swagger"):
        os.makedirs("swagger")
        
    # Initialiser Swagger
    setup_swagger(app)
    
    app.run(debug=True)