import streamlit as st
import joblib
import numpy as np
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from dotenv import load_dotenv
import os

# --- Load Environment Variables ---
load_dotenv("links.env")  # Specify the path to your .env file
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- Verify Environment Variables ---
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("🚫 Missing Supabase credentials in links.env file")
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Configuration ---
st.set_page_config(
    page_title="Water Quality Anomaly Detector",
    page_icon="💧",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Styling for Custom Backgrounds ---
st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(180deg, #a8dadc, #457b9d);
            color: #1d3557;
        }
        .graph-container {
            background-color: #f0f8ff; /* Light Blue for Graphs */
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .chart-container {
            background-color: #f5f5dc; /* Beige for Charts */
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .table-container {
            background-color: #fffacd; /* Lemon Chiffon for Tables */
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# --- Initialization ---
model = joblib.load("water_quality_model.pkl")

# --- Data Fetching Functions ---
def get_latest_record():
    data = supabase.table("lakefishcage").select("*").order("timestamp", desc=True).limit(1).execute().data[0]
    return data["temperature"], data["turbidity"], data["ph"]

def get_historical_data(limit=50, include_pred=False):
    data = supabase.table("lakefishcage").select("*").order("timestamp", desc=True).limit(limit).execute().data
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    if include_pred:
        preds = model.predict(df[["temperature", "turbidity", "ph"]].values)
        label_map = {0: "🌟 Excellent", 1: "👍 Good", 2: "⚠️ Poor"}
        df["predicted_quality"] = [label_map[p] for p in preds]
    return df

# --- Tabbed Layout ---
tabs = st.tabs(["Home", "About"])

# --- Home Tab ---
with tabs[0]:
    st.title("💧 Smart Fish Cage:Water Quality Detector")
    if st.button("Fetch Latest & Predict"):
        with st.spinner("Fetching latest data..."):
            time.sleep(1)
            try:
                temp, turb, ph = get_latest_record()
                pred = model.predict(np.array([[temp, turb, ph]]))[0]
                label_map = {0: "🌟 Excellent", 1: "👍 Good", 2: "⚠️ Poor"}

                st.markdown('<div class="chart-container"><h4>📱 Latest Sensor Readings</h4></div>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                col1.metric("🌡 Temperature (°C)", f"{temp:.2f}")
                col2.metric("💧 Turbidity", f"{turb:.2f} cm")
                col3.metric("🧪 pH", f"{ph:.2f}")

                st.markdown('<div class="chart-container"><h4>🧠 Predicted Water Quality</h4></div>', unsafe_allow_html=True)
                st.success(f"{label_map[pred]}")
            except Exception as e:
                st.error(f"🚫 Error fetching data: {e}")

    # --- Historical Trends ---
    with st.expander("📈 Show Historical Trends"):
        num_records = st.selectbox("Select number of past records to view", [10, 25, 50, 100], index=2)
        try:
            df = get_historical_data(limit=num_records)
            for feature, title, unit in zip(["temperature", "turbidity", "ph"],
                                            ["Temperature", "Turbidity", "pH"],
                                            ["°C", "Turbidity (cm)", "pH"]):
                st.markdown(f'<div class="graph-container"><h4>{title} Over Time</h4></div>', unsafe_allow_html=True)
                st.plotly_chart(
                    px.line(df, x="timestamp", y=feature, title=title, labels={feature: unit}, markers=True),
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"🚫 Error fetching historical data: {e}")

    # --- Predictions Table ---
    with st.expander("📋 Last 50 Predictions Table"):
        try:
            st.markdown('<div class="table-container"><h4>Last 50 Predictions</h4></div>', unsafe_allow_html=True)
            df_pred = get_historical_data(limit=50, include_pred=True)
            st.dataframe(df_pred[["timestamp", "temperature", "turbidity", "ph", "predicted_quality"]]
                         .rename(columns={
                             "timestamp": "Time",
                             "temperature": "Temperature (°C)",
                             "turbidity": "Turbidity (cm)",
                             "ph": "pH",
                             "predicted_quality": "Predicted Quality"
                         }))
        except Exception as e:
            st.error(f"🚫 Error showing predictions table: {e}")

# --- About Tab ---
with tabs[1]:
    st.title("ℹ️ About This App")
    st.markdown("""
        **Welcome to the Smart Fish Cage Water Quality Predictor!**  
        This application is designed to:
        - Fetch real-time data from sensors monitoring water quality in fish cages.
        - Predict water quality using a trained machine learning model.
        - Display historical trends and predictions in an interactive, user-friendly interface.
        
        **How It Works:**
        1. Sensor data (temperature, turbidity, pH) is stored in a database.
        2. This app retrieves the data and uses a trained model to predict water quality.
        3. The results are displayed as metrics, trends, and tables for easy interpretation.
        
        **Features:**
        - Real-time predictions for water quality.
        - Historical data visualization (temperature, turbidity, pH).
        - User-friendly interface with interactive charts.
        
        Created by: Phillip Mboya  EEE JKUAT @2025.  
        For inquiries, contact: [itsmboya18@gmail.com](mailto:itsmboya18@gmail.com)
    """)