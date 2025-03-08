import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')

    # Configuration MySQL
    MYSQL_CONFIG = {
        'host': 'mysql-10befa8c-keskoum120-db6d.b.aivencloud.com',
        'port': 27381,
        'user': 'avnadmin',
        'password': 'AVNS_AEfYMTwHdCFIzRZjyoS',
        'database': 'monkeypox_db',
        'ssl_ca': 'aiven-ca-cert.pem',
        'connect_timeout': 10
    }

    # Colonnes attendues pour l'import CSV
    EXPECTED_COLUMNS = {
        "location", "iso_code", "date", "total_cases", "total_deaths",
        "new_cases", "new_deaths", "new_cases_smoothed", "new_deaths_smoothed",
        "new_cases_per_million", "total_cases_per_million", "new_cases_smoothed_per_million",
        "new_deaths_per_million", "total_deaths_per_million", "new_deaths_smoothed_per_million"
    }
