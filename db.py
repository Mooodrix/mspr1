import mysql.connector
from mysql.connector import Error
from config import Config

def get_db_connection():
    try:
        connection = mysql.connector.connect(**Config.MYSQL_CONFIG)
        return connection
    except Error as err:
        print(f"⚠️ Erreur de connexion MySQL: {err}")
        return None
