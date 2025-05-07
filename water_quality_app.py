# water_quality_app.py
import os
import time
import logging
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from dotenv import load_dotenv
import joblib

# --- Configuration & Constants ---
load_dotenv("links.env")  # Load environment variables from .env file

MODEL_PATH = "water_quality_model.pkl"
HISTORICAL_DATA_LIMIT = 50
MAX_RETRIES = 3
RETRY_DELAY = 1

# --- Initialize Logging ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Streamlit Config ---
st.set_page_config(
    page_title="Water Quality Predictor",
    page_icon="💧",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Style Constants ---
COLOR_SCHEME = {
    'primary': '#2e8b57',
    'secondary': '#3aa573',
    'background': 'rgba(255, 255, 255, 0.9)',
    'text': '#333333'
}

# --- Helper Functions ---
@st.cache_resource
def load_model(model_path: str):
    """Load and cache the trained ML model"""
    try:
        model = joblib.load(model_path)
        logger.info("Model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Model loading failed: {str(e)}")
        raise e

# Update the fetch_data function in your code
@st.cache_data(ttl=300)
def fetch_data(_query, retries: int = MAX_RETRIES):  # Add underscore to query parameter
    """Generic data fetcher with retry logic"""
    for attempt in range(retries):
        try:
            data = _query.execute().data  # Use the underscored parameter
            logger.info(f"Data fetched successfully (attempt {attempt+1})")
            return data
        except Exception as e:
            if attempt == retries - 1:
                raise e
            time.sleep(RETRY_DELAY * (attempt + 1))
    return None

# --- Data Service Class ---
class WaterQualityDataService:
    def __init__(self):
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        
    def get_latest_record(self):
        """Fetch latest sensor readings with error handling"""
        query = self.supabase.table("lakefishcage").select("*").order("timestamp", desc=True).limit(1)
        data = fetch_data(query)
        return data[0]["temperature"], data[0]["turbidity"], data[0]["ph"]
    
    def get_historical_data(self, limit=50, include_pred=False):
        """Retrieve historical data with optional predictions"""
        query = self.supabase.table("lakefishcage").select("*").order("timestamp", desc=True).limit(limit)
        data = fetch_data(query)
        df = pd.DataFrame(data)
        
        if df.empty:
            return df
        
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
        
        if include_pred:
            model = load_model(MODEL_PATH)
            preds = model.predict(df[["temperature", "turbidity", "ph"]].values)
            label_map = {0: "🌟 Excellent", 1: "👍 Good", 2: "⚠️ Poor"}
            df["predicted_quality"] = [label_map[p] for p in preds]
        
        return df

# --- UI Components ---
def apply_custom_styles():
    """Inject custom CSS styles"""
    st.markdown(f"""
        <style>
            .stApp {{
                background-image: url("Aquaculture2/fishcages2.png");
                background-size: cover;
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-position: center;
            }}
            .metric-card {{
                background: {COLOR_SCHEME['background']};
                border-radius: 10px;
                padding: 15px;
                margin: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .prediction-banner {{
                background: {COLOR_SCHEME['secondary']};
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                margin: 20px 0;
            }}
        </style>
    """, unsafe_allow_html=True)

def display_metrics(temp: float, turb: float, ph: float):
    """Display sensor metrics in styled cards"""
    st.markdown("### 📱 Latest Sensor Readings")
    cols = st.columns(3)
    with cols[0]:
        st.markdown(f"""
            <div class="metric-card">
                <h4>🌡 Temperature (°C)</h4>
                <h2>{temp:.2f}</h2>
            </div>
        """, unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"""
            <div class="metric-card">
                <h4>💧 Turbidity (cm)</h4>
                <h2>{turb:.2f}</h2>
            </div>
        """, unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"""
            <div class="metric-card">
                <h4>🧪 pH</h4>
                <h2>{ph:.2f}</h2>
            </div>
        """, unsafe_allow_html=True)

def display_quality_prediction(pred: int):
    """Show prediction result with visual emphasis"""
    label_map = {
        0: ("🌟 Excellent", "#4CAF50"),
        1: ("👍 Good", "#FFC107"),
        2: ("⚠️ Poor", "#F44336")
    }
    text, color = label_map[pred]
    st.markdown(f"""
        <div class="prediction-banner" style="background: {color}">
            <h2 style="margin:0; padding:0">{text}</h2>
        </div>
    """, unsafe_allow_html=True)

# --- Main Application ---
def main():
    apply_custom_styles()
    data_service = WaterQualityDataService()
    model = load_model(MODEL_PATH)
    
    st.title("💧 Smart Fish Cage: Live Water Quality Prediction")
    
    # Main interaction section
    if st.button("Fetch Latest & Predict", type="primary"):
        with st.spinner("Fetching latest data..."):
            try:
                temp, turb, ph = data_service.get_latest_record()
                
                # Input validation
                if not all([isinstance(v, (int, float)) for v in [temp, turb, ph]]):
                    raise ValueError("Invalid sensor readings")
                
                display_metrics(temp, turb, ph)
                pred = model.predict(np.array([[temp, turb, ph]]))[0]
                display_quality_prediction(pred)
                
                # Visualization Section
                st.plotly_chart(go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=turb,
                    title={'text': "Turbidity Level"},
                    gauge={'axis': {'range': [0, 100]}, 'bar': {'color': COLOR_SCHEME['primary']}}
                )))
                
            except Exception as e:
                logger.error(f"Application error: {str(e)}")
                st.error("⚠️ Error fetching or processing data. Please try again later.")

    # Historical Data Section
    with st.expander("📈 Historical Trends Analysis"):
        try:
            num_records = st.select_slider(
                "Select time window",
                options=[10, 25, 50, 100],
                value=50
            )
            
            df = data_service.get_historical_data(limit=num_records)
            
            if not df.empty:
                tab1, tab2, tab3 = st.tabs(["Temperature", "Turbidity", "pH"])
                
                with tab1:
                    fig = px.line(df, x="timestamp", y="temperature", 
                                title="Temperature Trend",
                                labels={"temperature": "Temperature (°C)"})
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    fig = px.area(df, x="timestamp", y="turbidity",
                                title="Turbidity Trend",
                                color_discrete_sequence=[COLOR_SCHEME['primary']])
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab3:
                    fig = go.Figure(go.Scatter(
                        x=df["timestamp"],
                        y=df["ph"],
                        mode='markers+lines',
                        name="pH Levels"
                    ))
                    fig.update_layout(title="pH Level Variations")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No historical data available")
                
        except Exception as e:
            logger.error(f"Historical data error: {str(e)}")
            st.error("Could not load historical data")

    # Footer
    st.markdown("---")
    st.markdown("""
        <center>
            <small>Created by Phillip Mboya | Autonomous Fish Cage Monitoring System For Lakes</small><br>
            <small>System Version: 1.1.0 | Data updates every 5 minutes</small>
        </center>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()