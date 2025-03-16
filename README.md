# MSPR1 README

## Sommaire
1. [Introduction](#introduction)
2. [Prérequis](#prérequis)
3. [Installation des packages](#installation-des-packages)
4. [Configuration](#configuration)
5. [Utilisation](#utilisation)
6. [Structure du projet](#structure-du-projet)
7. [API](#api)
8. [Documentation](#documentation)
9. [Dépannage](#dépannage)
10. [Contributeurs](#contributeurs)

## Introduction
MSPR1 est une application web développée avec Flask pour la gestion et la visualisation des données liées au virus Monkeypox (variole du singe). L'application permet de consulter, ajouter, modifier et supprimer des données épidémiologiques, ainsi que de visualiser ces données sous forme de graphiques. Elle propose également des fonctionnalités d'importation de données via des fichiers CSV.

## Prérequis
- Python 3.7 ou supérieur
- MySQL Server (ou un service cloud MySQL comme Aiven)
- Navigateur web moderne
- Connexion Internet (pour les bibliothèques CDN)

## Installation des packages

Ce projet nécessite les packages Python suivants :
- mysql-connector-python
- pandas
- flask
- flask_paginate

Pour installer ces packages, exécutez la commande suivante :

```bash
pip install mysql-connector-python pandas flask flask-paginate
```

Ou : 

```bash
pip install -r requirements.txt
```

## Configuration

### Base de données
Le projet utilise une base de données MySQL. Les paramètres de connexion sont configurés dans le fichier `app.py` :

```python
config = {
    'host': 'votre-host-mysql',
    'port': votre-port,
    'user': 'votre-utilisateur',
    'password': 'votre-mot-de-passe',
    'database': 'monkeypox_db',
    'ssl_ca': 'chemin-vers-certificat-ssl',
    'connect_timeout': 10
}
```

Remplacez les valeurs par vos propres paramètres de connexion MySQL.

### Structure de la base de données
Assurez-vous que votre base de données contient une table nommée `monkeypox_data` avec les colonnes suivantes :
- id (INT, auto-increment, primary key)
- location (VARCHAR)
- iso_code (VARCHAR)
- date (DATE)
- total_cases (INT)
- total_deaths (INT) (optionnel selon les données disponibles)

## Utilisation

1. Démarrez l'application en exécutant :
   ```bash
   python app.py
   ```

2. Accédez à l'application dans votre navigateur à l'adresse : `http://localhost:5000`

3. Fonctionnalités disponibles :
   - **Page d'accueil** : Affiche un tableau des données avec options de tri et pagination
   - **Graphique** : Visualise les données sous forme de graphique linéaire
   - **Ajouter** : Permet d'ajouter manuellement une nouvelle entrée
   - **Importer CSV** : Permet d'importer des données en masse via un fichier CSV

## Structure du projet

```
mspr1/
├── app.py                 # Application principale Flask
├── templates/             # Dossiers des templates HTML
│   ├── Ajout.html         # Formulaire d'ajout de données
│   ├── graphique.html     # Page de visualisation graphique
│   ├── importCSV.html     # Page d'importation CSV
│   └── index.html         # Page d'accueil avec le tableau de données
├── uploads/               # Dossier pour les fichiers CSV importés
├── aiven-ca-cert.pem      # Certificat SSL pour la connexion MySQL
└── requirements.txt       # Liste des dépendances Python
```

## API

L'application expose les routes suivantes :

- `GET /` : Affiche la page d'accueil avec le tableau de données
  - Paramètres optionnels :
    - `sort_by` : Colonne pour le tri (par défaut : date)
    - `order` : Ordre du tri (asc ou desc)
    - `page` : Numéro de page pour la pagination

- `GET /ajout` : Affiche le formulaire d'ajout de données
- `GET /delete/<id>` : Supprime l'entrée avec l'ID spécifié
- `POST /edit/<id>` : Met à jour l'entrée avec l'ID spécifié
- `GET /importCSV` : Affiche la page d'importation CSV
- `GET /graphique` : Affiche la page de visualisation graphique

## Documentation

La documentation complète du projet est disponible sur GitBook à l'adresse suivante : [mspr1.gitbook.io/monkeypox](https://mspr1.gitbook.io/monkeypox)

### Contenu de la documentation

#### 1. Guide d'installation
- Instructions détaillées pour l'installation du projet
- Configuration de l'environnement de développement
- Mise en place de la base de données

#### 2. Guide d'utilisation
- Navigation dans l'interface
- Gestion des données Monkeypox
  - Consultation des données
  - Ajout de nouvelles entrées
  - Modification des entrées existantes
  - Suppression d'entrées
- Visualisation des données via graphiques

#### 3. Référence technique
- Architecture de l'application
- Modèle de données
- Description détaillée des API
- Guide de personnalisation

#### 4. Développement et contribution
- Comment contribuer au projet
- Standards de codage
- Processus de soumission de modifications

### Mise à jour de la documentation
La documentation est régulièrement mise à jour. Pour contribuer à la documentation :
1. Contactez les administrateurs du projet
2. Proposez vos modifications via le système de contribution GitBook

## Dépannage

### Problèmes de connexion à la base de données
- Vérifiez que vos identifiants MySQL sont corrects
- Vérifiez que le service MySQL est en cours d'exécution
- Vérifiez que le certificat SSL est bien présent et valide

### Problèmes d'affichage graphique
- Assurez-vous que Chart.js est correctement chargé
- Vérifiez la console du navigateur pour d'éventuelles erreurs JavaScript

## Contributeurs
*À compléter*
