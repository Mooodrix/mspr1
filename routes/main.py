from flask import Blueprint, render_template, request
from db import get_db_connection

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/tableau', methods=['GET'])
def tableau():
    connection = get_db_connection()
    if connection is None:
        return "⚠️ Erreur de connexion à la base de données", 500

    cursor = connection.cursor(dictionary=True)
    sort_by = request.args.get('sort_by', 'location')
    order = request.args.get('order', 'asc')
    page = int(request.args.get('page', 1))
    results_per_page = 10
    offset = (page - 1) * results_per_page

    # Si besoin de conditions supplémentaires, elles seront ajoutées ici
    conditions = []

    query = f"""
        SELECT * FROM monkeypox_data
        WHERE location != 'World'
        {"AND " + " AND ".join(conditions) if conditions else ""}
        ORDER BY {sort_by} {order}
        LIMIT %s OFFSET %s
    """
    params = [results_per_page, offset]

    cursor.execute(query, params)
    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) as count FROM monkeypox_data")
    total_records = cursor.fetchone()['count']
    total_pages = (total_records + results_per_page - 1) // results_per_page

    connection.close()
    return render_template("tableau.html", data=data, sort_by=sort_by, order=order, page=page, total_pages=total_pages)
