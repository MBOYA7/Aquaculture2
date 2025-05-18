import streamlit as st
import joblib
import numpy as np
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
from dotenv import load_dotenv
import os

# ======================
# ENVIRONMENT SETUP
# ======================
load_dotenv("links.env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("🚫 Missing Supabase credentials in links.env file")
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================
# PAGE CONFIGURATION
# ======================
st.set_page_config(
    page_title="Smart Fish Cage Dashboard",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed"  # This ensures sidebar is collapsed by default
)

# ======================
# CUSTOM STYLING (Enhanced)
# ======================
st.markdown("""
    <style>
        /* Global background and fonts */
        .stApp {
            background: linear-gradient(180deg, #e0f7fa, #80deea);
            color: #004d40;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        /* Improved card style for containers */
        .card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            padding: 25px;
            margin-bottom: 25px;
            border-left: 5px solid #00796b; /* Accent color */
        }
        .card-header {
            color: #00796b;
            margin-bottom: 15px;
        }
        /* Enhanced button style */
        .stButton>button {
            background-color: #00796b !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 10px 20px !important;
            font-weight: bold !important;
            border: none !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: background-color 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #004d40 !important;
        }
        /* Metric styling */
        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #00796b;
        }
        .metric-label {
            color: #4db6ac;
            font-size: 0.9em;
        }
        /* Success and error messages */
        .stSuccess {
            color: #1b5e20;
            background-color: #e8f5e9;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .stError {
            color: #b71c1c;
            background-color: #ffebee;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .stInfo {
            color: #0d47a1;
            background-color: #e3f2fd;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        /* Refresh button container */
        .refresh-container {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# ======================
# MODEL LOADING
# ======================
try:
    model = joblib.load("water_quality_model.pkl")
except FileNotFoundError:
    st.error("Error: 'water_quality_model.pkl' not found. Please ensure the model file is in the correct directory.")
    model = None

# ======================
# DATA FUNCTIONS (Optimized with caching and error handling)
# ======================
@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_latest_record():
    try:
        response = supabase.table("lakefishcage").select("*").order("timestamp", desc=True).limit(1).execute()
        if response.data:
            data = response.data[0]
            return data["temperature"], data["turbidity"], data["ph"], pd.to_datetime(data["timestamp"])
        else:
            return None, None, None, None
    except Exception as e:
        st.error(f"Error fetching latest water quality data: {e}")
        return None, None, None, None

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_last_security_update():
    try:
        response = supabase.table("security_alerts").select("*").order("timestamp", desc=True).limit(1).execute()
        if response.data:
            data = response.data[0]
            return data["status"], pd.to_datetime(data["timestamp"])
        else:
            return None, None
    except Exception as e:
        st.error(f"Error fetching latest security update: {e}")
        return None, None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_historical_data(limit=50):
    try:
        response = supabase.table("lakefishcage").select("*").order("timestamp", desc=True).limit(limit).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df.sort_values("timestamp")
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching historical water quality data: {e}")
        return pd.DataFrame()

# Simulate real-time security status (replace with your actual implementation)
def get_realtime_security_status():
    # In a real application, this would connect to a WebSocket or a streaming API
    time.sleep(1)  # Simulate a delay
    # Example: Randomly change status
    status = np.random.choice([True, False], p=[0.1, 0.9])
    return {"status": status, "timestamp": pd.Timestamp.now()}

# State to hold the latest real-time status
if 'realtime_security_status' not in st.session_state:
    st.session_state['realtime_security_status'] = get_realtime_security_status()

def update_security_status():
    st.session_state['realtime_security_status'] = get_realtime_security_status()

# ======================
# MAIN CONTENT
# ======================
# Add refresh button at the top right
col1, col2 = st.columns([5, 1])
with col2:
    if st.button("🔄 Refresh Data & Predict"):
        st.cache_data.clear()  # Clear all cached data
        update_security_status()
        st.rerun()  # Rerun the app to fetch fresh data

# Tabs
tabs = st.tabs(["🏠 Overview", "🔒 Security Center", "ℹ️ About"])

# Home Tab (Renamed to Overview, Improved Layout)
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h2 class="card-header">🌊 Water Quality Overview</h2>', unsafe_allow_html=True)

    latest_temp, latest_turb, latest_ph, latest_ts = get_latest_record()

    if latest_temp is not None:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="metric-value">{latest_temp:.2f} °C</div>', unsafe_allow_html=True)
            st.markdown('<p class="metric-label">🌡 Temperature</p>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-value">{latest_turb:.2f}</div>', unsafe_allow_html=True)
            st.markdown('<p class="metric-label">💧 Turbidity</p>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-value">{latest_ph:.2f}</div>', unsafe_allow_html=True)
            st.markdown('<p class="metric-label">🧪 pH</p>', unsafe_allow_html=True)
        with col4:
            if latest_ts:
                st.markdown(f'<p class="metric-label">⏱️ Last Updated: {latest_ts.strftime("%Y-%m-%d %H:%M:%S")}</p>', unsafe_allow_html=True)

        if model:
            pred = model.predict(np.array([[latest_temp, latest_turb, latest_ph]]))[0]
            label_map = {0: "🌟 Excellent", 1: "👍 Good", 2: "⚠ Poor"}
            st.markdown(f"✨ **Predicted Water Quality:** <span style='font-size:1.2em; font-weight:bold;'>{label_map[pred]}</span>", unsafe_allow_html=True)

            # Gauge charts
            gauge_fig = make_subplots(rows=1, cols=3, specs=[[{'type':'indicator'},{'type':'indicator'},{'type':'indicator'}]])
            gauge_fig.add_trace(go.Indicator(mode="gauge+number", value=latest_temp, title={'text':'Temp (°C)'}, gauge={'axis':{'range':[0,40]}}), row=1, col=1)
            gauge_fig.add_trace(go.Indicator(mode="gauge+number", value=latest_turb, title={'text':'Turbidity'}, gauge={'axis':{'range':[0,100]}}), row=1, col=2)
            gauge_fig.add_trace(go.Indicator(mode="gauge+number", value=latest_ph, title={'text':'pH'}, gauge={'axis':{'range':[0,14]}}), row=1, col=3)
            gauge_fig.update_layout(margin={'t':20,'b':20,'l':20,'r':20}, height=300)
            st.plotly_chart(gauge_fig, use_container_width=True)
        else:
            st.warning("⚠️ Machine learning model not loaded.")

    else:
        st.info("No latest water quality data available.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Historical Trends (Improved Charting)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3 class="card-header">📈 Historical Water Quality Trends</h3>', unsafe_allow_html=True)
    df_historical = get_historical_data(limit=50)  # Using default value since sidebar control is removed
    if not df_historical.empty:
        fig_trends = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                                subplot_titles=('Temperature (°C)', 'Turbidity', 'pH'))
        fig_trends.add_trace(go.Scatter(x=df_historical['timestamp'], y=df_historical['temperature'], name='Temperature', line=dict(color='#26a69a')), row=1, col=1)
        fig_trends.add_trace(go.Scatter(x=df_historical['timestamp'], y=df_historical['turbidity'], name='Turbidity', line=dict(color='#00acc1')), row=2, col=1)
        fig_trends.add_trace(go.Scatter(x=df_historical['timestamp'], y=df_historical['ph'], name='pH', line=dict(color='#4dd0e1')), row=3, col=1)

        fig_trends.update_layout(height=600, title_text="Water Quality Trends Over Time", showlegend=False)
        st.plotly_chart(fig_trends, use_container_width=True)
    else:
        st.info("No historical water quality data available.")
    st.markdown('</div>', unsafe_allow_html=True)

# Security Tab (Improved Display with Simulated Real-time Update)
with tabs[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h2 class="card-header">🔒 Modern Security Center</h2>', unsafe_allow_html=True)

    st.subheader("Current Security Status")
    realtime_data = st.session_state['realtime_security_status']
    if realtime_data:
        ts_str = realtime_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        if realtime_data['status']:
            st.error(f"🚨 **REAL-TIME ALERT:** Not Safe (Updated: {ts_str})", unsafe_allow_html=True)
        else:
            st.markdown(f"✅ **REAL-TIME STATUS:** Safe (Updated: {ts_str})", unsafe_allow_html=True)
    else:
        st.info("Waiting for real-time security updates...")

    def update_status_periodically():
        while True:
            time.sleep(5)  # Simulate updates every 5 seconds
            st.session_state['realtime_security_status'] = get_realtime_security_status()
            st.experimental_rerun() # Trigger a rerun to update the UI

    # Run the update in a separate thread to avoid blocking the main Streamlit app
    import threading
    if 'security_updater_started' not in st.session_state:
        st.session_state['security_updater_started'] = True
        security_thread = threading.Thread(target=update_status_periodically, daemon=True)
        security_thread.start()

    st.markdown("---")
    st.subheader("Recent Security Alerts")
    def get_security_alerts(limit=20):
        try:
            response = supabase.table("security_alerts").select("*").order("timestamp", desc=True).limit(limit).execute()
            if response.data:
                df = pd.DataFrame(response.data)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df["status_label"] = df["status"].apply(lambda x: "🚨 Alert" if x else "✅ Normal")
                return df.sort_values("timestamp", ascending=False)
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching security alerts: {e}")
            return pd.DataFrame()

    sec_df = get_security_alerts(limit=20)  # Using default value since sidebar control is removed
    if not sec_df.empty:
        st.dataframe(
            sec_df[["timestamp","status_label"]].rename(columns={"timestamp":"Time","status_label":"Status"}), use_container_width=True
        )
        fig_alerts = px.scatter(sec_df, x="timestamp", y="status_label", color="status_label",
                                 title="Security Alert Timeline", labels={"timestamp":"Time","status_label":"Status"},
                                 color_discrete_map={"🚨 Alert": "#ef5350", "✅ Normal": "#66bb6a"})
        st.plotly_chart(fig_alerts, use_container_width=True)
    else:
        st.info("No recent security alerts found.")
    st.markdown('</div>', unsafe_allow_html=True)

# About Tab (Improved Content - COMPLETED)
with tabs[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h2 class="card-header">ℹ️ About This Smart Fish Cage Dashboard</h2>', unsafe_allow_html=True)
    st.markdown("**Developed by:** Phillip Mboya, EEE JKUAT © 2025")
    st.markdown("**Contact:** [itsmboya18@gmail.com](mailto:itsmboya18@gmail.com)")
    st.markdown("**Purpose:** This interactive dashboard provides real-time monitoring and predictive analysis of water quality within fish cages. By leveraging sensor data and a machine learning model, it aims to ensure a healthy environment for aquaculture.")
    st.markdown("---")
    st.markdown("### Key Features:")
    st.markdown("- **Real-time Water Quality Metrics:** Displays the latest temperature, turbidity, and pH levels.")
    st.markdown("- **Predictive Analysis:** Utilizes a machine learning model to predict the overall water quality (Excellent, Good, Poor).")
    st.markdown("- **Historical Trends:** Visualizes historical data for temperature, turbidity, and pH, allowing users to identify patterns and anomalies.")
    st.markdown("- **Security Alerts:** Provides a dedicated section for monitoring and reviewing security-related events.")
    st.markdown("- **Real-time Security Status:** Offers an immediate view of the current security status with automatic updates.")
    st.markdown("---")
    st.markdown("Feel free to explore the different tabs to gain insights into the fish cage environment.")
    st.markdown('</div>', unsafe_allow_html=True)