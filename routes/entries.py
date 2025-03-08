from flask import Blueprint, render_template, request, redirect, url_for
from db import get_db_connection

entries_bp = Blueprint('entries', __name__)

@entries_bp.route('/ajout', methods=['GET', 'POST'])
def ajout():
    if request.method == 'POST':
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
        return redirect(url_for('main.tableau'))
    return render_template('Ajout.html')

@entries_bp.route('/delete/<int:id>')
def delete_entry(id):
    connection = get_db_connection()
    if connection is None:
        return "⚠️ Erreur de connexion à la base de données", 500

    cursor = connection.cursor()
    cursor.execute("DELETE FROM monkeypox_data WHERE id = %s", (id,))
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('main.index'))

@entries_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_entry(id):
    connection = get_db_connection()
    if connection is None:
        return "⚠️ Erreur de connexion à la base de données", 500
    cursor = connection.cursor(dictionary=True)

    if request.method == 'GET':
        cursor.execute("SELECT * FROM monkeypox_data WHERE id = %s", (id,))
        row = cursor.fetchone()
        if row is None:
            return "⚠️ Entrée non trouvée", 404

        sort_by = request.args.get('sort_by', 'location')
        order = request.args.get('order', 'asc')
        page = int(request.args.get('page', 1))
        results_per_page = 10
        offset = (page - 1) * results_per_page

        cursor.execute(f"""
            SELECT * FROM monkeypox_data
            ORDER BY {sort_by} {order}
            LIMIT %s OFFSET %s
        """, (results_per_page, offset))
        _ = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) as count FROM monkeypox_data")
        total_rows = cursor.fetchone()['count']
        total_pages = (total_rows + results_per_page - 1) // results_per_page

        cursor.close()
        connection.close()
        return render_template('edit_entry.html', row=row, page=page, sort_by=sort_by, order=order, total_pages=total_pages)

    if request.method == 'POST':
        location = request.form['location']
        iso_code = request.form['iso_code']
        date = request.form['date']
        total_cases = request.form['total_cases']
        cursor.execute("""
            UPDATE monkeypox_data 
            SET location = %s, iso_code = %s, date = %s, total_cases = %s 
            WHERE id = %s
        """, (location, iso_code, date, total_cases, id))
        connection.commit()
        cursor.close()
        connection.close()
        return redirect(url_for('main.tableau', 
                                page=request.args.get('page', 1),
                                sort_by=request.args.get('sort_by', 'location'),
                                order=request.args.get('order', 'asc')))
