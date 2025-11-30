import streamlit as st
from db import init_db, seed_db

st.set_page_config(
    page_title="Digital Andon",
    layout="wide",
)

def main():
    st.title("Digital Andon / Downtime Tracker")
    
    st.markdown("""
    Welcome to the Digital Andon System.
    
    Use the sidebar to navigate between:
    - **Operator Panel**: For logging downtime and quality events.
    - **Supervisor Dashboard**: For viewing shift performance and metrics.
    - **Admin Config**: For managing lines, machines, and master data.
    """)

    st.info("This is a simple MVP andon system built with Streamlit.")

if __name__ == "__main__":
    init_db()
    seed_db()
    main()

