import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import numpy as np

# Flask API Endpoint
API_URL = "http://127.0.0.1:5000/api/monkeypox_data"  # Ensure Flask is running

# Fetch Data from Flask API
st.set_page_config(page_title="Monkeypox Dashboard", layout="wide")
st.title("🦠 Monkeypox Data Visualization Dashboard")

# Navigation
page = st.sidebar.radio("Navigation", ["🏠 Accueil", "📊 Bar Chart", "📈 Scatter Plot", "🌍 World Map"])

if page == "🏠 Accueil":
    st.subheader("Bienvenue sur le Dashboard Monkeypox")
    st.write("Utilisez le menu sur la gauche pour naviguer entre les graphiques.")
else:
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
        else:
            st.error("Failed to fetch data from Flask API")
            st.stop()

        # Convert date to datetime format
        df["date"] = pd.to_datetime(df["date"])

        # 🏳️ Select a Country
        locations = df["location"].unique()
        locations = np.append(locations, "All")
        selected_country = st.selectbox("🏳️ Select a Country:", locations)


        # 📅 **Date Range Selector**
        min_date, max_date = df["date"].min(), df["date"].max()
        date_range = st.date_input("📆 Select Date Range:", [min_date, max_date], min_value=min_date, max_value=max_date)

        # 📊 Filter Data
        if selected_country == "All":
            filtered_df = df[(df["date"] >= pd.to_datetime(date_range[0])) & 
                            (df["date"] <= pd.to_datetime(date_range[1]))]
        else:
            filtered_df = df[(df["location"] == selected_country) & 
                            (df["date"] >= pd.to_datetime(date_range[0])) & 
                            (df["date"] <= pd.to_datetime(date_range[1]))]

        # ✅ Fix NaN values in numeric columns
        numeric_columns = ["total_cases", "total_deaths", "new_cases"]
        df[numeric_columns] = df[numeric_columns].fillna(0)
        filtered_df[numeric_columns] = filtered_df[numeric_columns].fillna(0)

        if filtered_df.empty:
            st.warning(f"No data available for {selected_country}. Adjust filters.")
        else:
            # 📌 Show Key Metrics
            total_cases = filtered_df["total_cases"].sum()
            total_deaths = filtered_df["total_deaths"].sum()
            new_cases = filtered_df["new_cases"].sum()

            st.metric("Total Cases in Selected Period", f"{total_cases:,}")
            st.metric("Total Deaths in Selected Period", f"{total_deaths:,}")
            st.metric("New Cases in Selected Period", f"{new_cases:,}")

            if page == "📊 Bar Chart":
                st.subheader("📊 Cases and Deaths Breakdown")
                fig_bar = px.bar(
                    x=["New Cases", "Total Cases", "Total Deaths"],
                    y=[new_cases, total_cases, total_deaths],
                    labels={"x": "Category", "y": "Count"},
                    color=["New Cases", "Total Cases", "Total Deaths"],
                    title=f"Monkeypox Cases Breakdown in {selected_country}",
                    template="plotly_dark",
                )
                st.plotly_chart(fig_bar)

            elif page == "📈 Scatter Plot":
                st.subheader("📍 New Cases vs. Total Cases")
                fig_scatter = px.scatter(
                    filtered_df,
                    x="total_cases",
                    y="new_cases",
                    size=filtered_df["new_cases"],
                    color="new_cases",
                    hover_name="date",
                    title="New Cases vs. Total Cases",
                    template="plotly_dark",
                )
                st.plotly_chart(fig_scatter)

            elif page == "🌍 World Map":
                st.subheader("🗺️ Monkeypox Cases Around the World")
                
                # Add a slider to select sample size
                sample_size = st.sidebar.slider("Select Sample Size for Map", min_value=100, max_value=1000, value=500, step=100)
                
                # Sample data to avoid overloading the map
                if len(df) > sample_size:
                    df_sampled = df.sample(n=sample_size)
                else:
                    df_sampled = df
            
                fig_map = px.scatter_geo(
                    df_sampled,
                    locations="location",
                    locationmode="country names",
                    size=df_sampled["total_cases"],
                    color="new_cases",
                    hover_name="location",
                    title="Global Monkeypox Cases",
                    template="plotly_dark",
                    projection="natural earth",
                )
                st.plotly_chart(fig_map)

    except Exception as e:
        st.error(f"Error: {e}")