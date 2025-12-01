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
    - **Maintenance View**: For managing active maintenance requests.
    - **Value Stream SQDC**: Tier-1 daily management board for value streams.
    - **Executive Summary**: Tier-2 aggregated dashboard and action tracking.
    """)

    st.info("This is a simple MVP andon system built with Streamlit.")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Quick Navigation")
        if hasattr(st, "page_link"):
            st.page_link("pages/1_Operator_Panel.py", label="Go to Operator Panel", icon="🏭")
            st.page_link("pages/5_Value_Stream_SQDC.py", label="View SQDC Board", icon="📊")
            st.page_link("pages/6_Executive_Summary.py", label="Executive Summary", icon="📈")
        else:
            st.write("Use the sidebar to navigate.")

if __name__ == "__main__":
    init_db()
    seed_db()
    main()
