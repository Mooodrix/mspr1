from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import pandas as pd
import os

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

# Route principale : Afficher les données
@app.route('/')
def index():
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

    return render_template('index.html', data=data, page=page, total_pages=total_pages, sort_by=sort_by, order=order)



# Route pour ajouter une nouvelle entrée
@app.route('/add', methods=['POST'])
def add_entry():
    location = request.form['location']
    iso_code = request.form['iso_code']
    date = request.form['date']
    total_cases = request.form['total_cases']

    connection = get_db_connection()
    if connection is None:
        return "⚠️ Erreur de connexion à la base de données", 500

    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO monkeypox_data (location, iso_code, date, total_cases) 
        VALUES (%s, %s, %s, %s)
    """, (location, iso_code, date, total_cases))
    
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('index'))

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

# Route pour uploader un fichier CSV en batch
@app.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return "⚠️ Aucun fichier sélectionné", 400

    file = request.files['file']
    if file.filename == '':
        return "⚠️ Nom de fichier invalide", 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    try:
        print("📥 Lecture du fichier CSV...")
        batch_size = 500  # Taille des lots
        total_rows = 0    # Compteur total
        connection = get_db_connection()
        if connection is None:
            return "⚠️ Erreur de connexion à la base de données", 500

        cursor = connection.cursor()

        for chunk in pd.read_csv(filepath, chunksize=batch_size):
            print(f"➡️ Traitement de {len(chunk)} lignes...")
            
            # Compter les lignes traitées
            total_rows += len(chunk)
            print(f"📊 Total traité jusqu'ici: {total_rows} lignes")

            # Vérification des colonnes valides
            valid_columns = [col for col in chunk.columns if col in EXPECTED_COLUMNS]
            chunk = chunk[valid_columns]

            if not valid_columns:
                os.remove(filepath)
                return "⚠️ Aucune colonne valide trouvée dans le fichier CSV.", 400

            # Remplacer NaN par None pour éviter erreurs MySQL
            chunk = chunk.where(pd.notna(chunk), None)

            # Construction de la requête SQL
            placeholders = ", ".join(["%s"] * len(valid_columns))
            columns = ", ".join(valid_columns)
            sql = f"INSERT INTO monkeypox_data ({columns}) VALUES ({placeholders})"

            # Insertion des données par batch
            data_tuples = [tuple(row) for row in chunk.to_numpy()]
            cursor.executemany(sql, data_tuples)
            connection.commit()

        print(f"✅ Import terminé ! {total_rows} lignes insérées.")
        cursor.close()
        connection.close()

    except Exception as e:
        print(f"⚠️ Erreur lors de l'import CSV: {e}")
        return f"⚠️ Erreur: {e}", 500
    finally:
        os.remove(filepath)

    return redirect(url_for('index'))


if __name__ == '__main__':
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.run(debug=True)
