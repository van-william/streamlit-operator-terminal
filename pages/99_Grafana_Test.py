import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Grafana Test", layout="wide")
st.title("Grafana Embedding Test")

st.markdown("""
This page tests embedding Grafana dashboards using an iframe.
Ensure your Grafana instance allows embedding (set `allow_embedding = true` in Grafana config).
""")

# --- Configuration ---
# In a real app, these might come from config.py or secrets
GRAFANA_BASE_URL = st.text_input("Grafana URL", value="http://localhost:3000")
DASHBOARD_UID = st.text_input("Dashboard UID", value="")
THEME = st.selectbox("Theme", ["light", "dark"], index=1)
REFRESH = st.selectbox("Refresh Rate", ["5s", "10s", "30s", "1m"], index=0)

# Construct URL
# Example: http://localhost:3000/d/UID/slug?orgId=1&refresh=5s&theme=dark&kiosk
if GRAFANA_BASE_URL and DASHBOARD_UID:
    # Basic URL construction - might need adjustment based on specific Grafana setup
    dashboard_url = f"{GRAFANA_BASE_URL}/d/{DASHBOARD_UID}?orgId=1&refresh={REFRESH}&theme={THEME}&kiosk"
    
    st.subheader("Generated Embed URL")
    st.code(dashboard_url)
    
    st.subheader("Preview")
    
    # Render IFrame
    try:
        components.iframe(dashboard_url, height=600, scrolling=True)
    except Exception as e:
        st.error(f"Error embedding iframe: {e}")
else:
    st.info("Please enter Grafana URL and Dashboard UID to see the preview.")

st.divider()

st.markdown("### Troubleshooting")
st.markdown("""
1. **Refused to connect**: Check if `allow_embedding = true` is set in `grafana.ini` under `[security]`.
2. **Cookie/Auth issues**: You might need to enable anonymous access or use an auth proxy if not logged in to Grafana in this browser.
3. **Mixed Content**: If this app is HTTPS, Grafana must also be HTTPS.
""")

