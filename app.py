import os
from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Créer le dossier uploads s'il n'existe pas
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Enregistrer les blueprints
    from routes.main import main_bp
    from routes.entries import entries_bp
    from routes.visualization import vis_bp
    from routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(entries_bp)
    app.register_blueprint(vis_bp)
    app.register_blueprint(api_bp)  # API endpoints pour le CRUD via Streamlit

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
