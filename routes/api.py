from flask import Blueprint, request, jsonify
from db import get_db_connection

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/monkeypox_data', methods=['GET'])
def get_monkeypox_data():
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Erreur de connexion à la base de données"}), 500
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM monkeypox_data")
    data = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(data)

@api_bp.route('/add', methods=['POST'])
def add_data():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Aucune donnée fournie"}), 400

    location = data.get("location")
    date = data.get("date")
    total_cases = data.get("total_cases")
    new_cases = data.get("new_cases")
    total_deaths = data.get("total_deaths")
    
    connection = get_db_connection()
    if connection is None:
        return jsonify({"success": False, "error": "Erreur de connexion à la base de données"}), 500
    
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO monkeypox_data (location, date, total_cases, new_cases, total_deaths)
            VALUES (%s, %s, %s, %s, %s)
        """, (location, date, total_cases, new_cases, total_deaths))
        connection.commit()
    except Exception as e:
        connection.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()
    return jsonify({"success": True})

@api_bp.route('/delete', methods=['POST'])
def delete_data():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Aucune donnée fournie"}), 400

    location = data.get("location")
    connection = get_db_connection()
    if connection is None:
        return jsonify({"success": False, "error": "Erreur de connexion à la base de données"}), 500

    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM monkeypox_data WHERE location = %s", (location,))
        connection.commit()
    except Exception as e:
        connection.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()
    return jsonify({"success": True})
