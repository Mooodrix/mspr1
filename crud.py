import streamlit as st
import requests
import pandas as pd

# 🌍 API Endpoint de ton backend Flask
API_URL = "http://127.0.0.1:5000/api/monkeypox_data"

# 📌 Fonction pour récupérer les données depuis l'API Flask
def fetch_data():
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        else:
            st.error(f"❌ Erreur API: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Impossible de récupérer les données: {e}")
        return pd.DataFrame()

# 📌 Fonction pour envoyer des données au backend Flask
def send_data(data, action):
    try:
        url = f"http://127.0.0.1:5000/api/{action}"
        response = requests.post(url, json=data)
        return response.json()
    except Exception as e:
        st.error(f"❌ Erreur lors de l'envoi des données: {e}")
        return None

# 🏠 Interface CRUD
def crud_page():
    st.title("📊 Gestion des Données Monkeypox (CRUD)")

    # 📌 Charger les données
    df = fetch_data()
    if df.empty:
        st.warning("⚠️ Aucune donnée disponible.")
    else:
        st.dataframe(df)

    # 📌 Ajouter une nouvelle entrée
    st.subheader("➕ Ajouter une Nouvelle Entrée")
    with st.form("add_entry"):
        location = st.text_input("🌍 Pays:")
        date = st.date_input("📅 Date:")
        total_cases = st.number_input("🦠 Total Cases:", min_value=0, step=1)
        new_cases = st.number_input("📈 Nouveaux Cas:", min_value=0, step=1)
        total_deaths = st.number_input("☠️ Total Deaths:", min_value=0, step=1)

        submitted = st.form_submit_button("Ajouter")
        if submitted:
            new_data = {
                "location": location,
                "date": str(date),
                "total_cases": total_cases,
                "new_cases": new_cases,
                "total_deaths": total_deaths
            }
            response = send_data(new_data, "add")
            if response and response.get("success"):
                st.success("✅ Entrée ajoutée avec succès !")
                st.experimental_rerun()

    # 📌 Supprimer une entrée
    st.subheader("🗑️ Supprimer une Entrée")
    if not df.empty:
        selected_row = st.selectbox("📌 Sélectionner un pays à supprimer:", df["location"].unique())
        if st.button("Supprimer"):
            delete_data = {"location": selected_row}
            response = send_data(delete_data, "delete")
            if response and response.get("success"):
                st.success(f"✅ {selected_row} supprimé avec succès !")
                st.experimental_rerun()

    # 📌 Importer les données depuis un fichier CSV
    st.subheader("📂 Importer un fichier CSV")
    uploaded_file = st.file_uploader("📥 Déposer un fichier CSV", type=["csv"])
    if uploaded_file:
        data_csv = pd.read_csv(uploaded_file)
        if st.button("📤 Importer dans la base de données"):
            for _, row in data_csv.iterrows():
                csv_data = {
                    "location": row["location"],
                    "date": row["date"],
                    "total_cases": int(row["total_cases"]),
                    "new_cases": int(row["new_cases"]),
                    "total_deaths": int(row["total_deaths"])
                }
                send_data(csv_data, "add")
            st.success("✅ Données importées avec succès !")
            st.experimental_rerun()

# Exécuter la page CRUD
if __name__ == "__main__":
    crud_page()
