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
    initial_sidebar_state="expanded"
)

# ======================
# CUSTOM STYLING
# ======================
st.markdown("""
    <style>
        /* Global background and fonts */
        .stApp {
            background: linear-gradient(180deg, #e0f7fa, #80deea);
            color: #004d40;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        /* Card style for containers */
        .card {
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        /* Button enhancement */
        .stButton>button {
            background-color: #00796b;
            color: white;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #004d40;
            transition: background-color 0.3s ease;
        }
        /* Sidebar style */
        .sidebar .sidebar-content {
            background: #b2dfdb;
            padding: 16px;
        }
    </style>
""", unsafe_allow_html=True)

# ======================
# MODEL LOADING
# ======================
model = joblib.load("water_quality_model.pkl")

# ======================
# DATA FUNCTIONS
# ======================
def get_latest_record():
    data = supabase.table("lakefishcage").select("*").order("timestamp", desc=True).limit(1).execute().data[0]
    return data["temperature"], data["turbidity"], data["ph"]

# New: fetch last security update
def get_last_security_update():
    data = supabase.table("security_alerts").select("*").order("timestamp", desc=True).limit(1).execute().data
    if data:
        return data[0]["status"], pd.to_datetime(data[0]["timestamp"])
    return None, None

# Historical data fetch for trends and predictions
def get_historical_data(limit=50, include_pred=False):
    data = supabase.table("lakefishcage").select("*").order("timestamp", desc=True).limit(limit).execute().data
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    if include_pred:
        preds = model.predict(df[["temperature", "turbidity", "ph"]].values)
        label_map = {0: "🌟 Excellent", 1: "👍 Good", 2: "⚠ Poor"}
        df["predicted_quality"] = [label_map[p] for p in preds]
    return df

# ======================
# SIDEBAR CONTROLS
# ======================
st.sidebar.markdown("<h2>⚙ Controls</h2>", unsafe_allow_html=True)
if st.sidebar.button("Fetch Latest Data & Predict"):
    st.session_state['fetch_now'] = True

st.sidebar.markdown("---")
st.sidebar.markdown("<h4>📊 Historical Data</h4>", unsafe_allow_html=True)
num_records = st.sidebar.selectbox("Records to View", [10, 25, 50, 100], index=2)
st.sidebar.markdown("---")
st.sidebar.markdown("[📂 View on Supabase](#)", unsafe_allow_html=True)

# ======================
# MAIN CONTENT
# ======================
# Tabs
tabs = st.tabs(["🏠 Home", "🔒 Security", "ℹ About"])

# Home Tab
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Smart Fish Cage Water Quality")
    st.markdown("---")
    if st.session_state.get('fetch_now', False):
        with st.spinner("Fetching latest data…"):
            time.sleep(1)
            try:
                temp, turb, ph = get_latest_record()
                pred = model.predict(np.array([[temp, turb, ph]]))[0]
                label_map = {0: "🌟 Excellent", 1: "👍 Good", 2: "⚠ Poor"}

                # Display metrics
                col1, col2, col3 = st.columns(3)
                col1.metric("🌡 Temperature (°C)", f"{temp:.2f}")
                col2.metric("💧 Turbidity", f"{turb:.2f}")
                col3.metric("🧪 pH", f"{ph:.2f}")

                # Display prediction
                st.success(f"*Predicted Quality:* {label_map[pred]}")

                # Gauge charts for immediate visualization
                gauge_fig = make_subplots(rows=1, cols=3, specs=[[{'type':'indicator'},{'type':'indicator'},{'type':'indicator'}]])
                gauge_fig.add_trace(go.Indicator(
                    mode="gauge+number", value=temp,
                    title={'text':'Temp (°C)'}, gauge={'axis':{'range':[0,40]}}), row=1, col=1)
                gauge_fig.add_trace(go.Indicator(
                    mode="gauge+number", value=turb,
                    title={'text':'Turbidity'}, gauge={'axis':{'range':[0,100]}}), row=1, col=2)
                gauge_fig.add_trace(go.Indicator(
                    mode="gauge+number", value=ph,
                    title={'text':'pH'}, gauge={'axis':{'range':[0,14]}}), row=1, col=3)
                gauge_fig.update_layout(margin={'t':20,'b':20,'l':20,'r':20}, height=300)
                st.plotly_chart(gauge_fig, use_container_width=True)

            except Exception as e:
                st.error(f"Error: {e}")
        st.session_state['fetch_now'] = False
    st.markdown('</div>', unsafe_allow_html=True)

    # Historical Trends
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Historical Trends 📈")
    try:
        df = get_historical_data(limit=num_records)
        # Combined line chart
        fig = px.line(df, x="timestamp", y=["temperature", "turbidity", "ph"],
                      labels={"value":"Reading","timestamp":"Time","variable":"Parameter"},
                      title="Water Quality Over Time")
        fig.update_layout(legend=dict(title="Parameter"))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading data: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# Security Tab
with tabs[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Security Alerts 🔒")

    # Button & widget for last update
    if st.button("Show Latest Security Status"):
        status, ts = get_last_security_update()
        if status is None:
            st.info("No security records found.")
        else:
            ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
            if status:
                st.error(f"🚨 Last update at {ts_str}: Not Safe")
            else:
                st.success(f"✅ Last update at {ts_str}: Safe")

    # Historical security alerts
    def get_security_alerts(limit=20):
        data = supabase.table("security_alerts").select("*").order("timestamp", desc=True).limit(limit).execute().data
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"]) if not df.empty else df
        return df.sort_values("timestamp", ascending=False)

    sec_df = get_security_alerts(limit=num_records)
    if not sec_df.empty:
        sec_df["status_label"] = sec_df["status"].apply(lambda x: "🚨 Alert" if x else "✅ Normal")
        st.dataframe(
            sec_df[["timestamp","status_label"]].rename(columns={"timestamp":"Time","status_label":"Status"}), use_container_width=True
        )
        fig2 = px.scatter(sec_df, x="timestamp", y="status_label", color="status_label",
                          title="Alert Timeline", labels={"timestamp":"Time","status_label":"Status"})
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No alerts found.")
    st.markdown('</div>', unsafe_allow_html=True)

# About Tab
with tabs[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("About This Dashboard")
    st.write("Built by Phillip Mboya, EEE JKUAT ©2025")
    st.write("Contact: [itsmboya18@gmail.com](mailto:itsmboya18@gmail.com)")
    st.write("This app visualizes real-time water quality data from fish cage sensors and predicts water health using a machine learning model.")
    st.markdown('</div>', unsafe_allow_html=True)