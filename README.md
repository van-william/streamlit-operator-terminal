# Digital Andon & Downtime Tracker

A simple, tablet-friendly Streamlit application for tracking manufacturing downtime, quality issues, and production counts. Designed as a starting point for digital transformation on the factory floor.

## Features

- **Operator Panel**:
    - Log downtime events with reasons (Planned/Unplanned).
    - Real-time downtime timer.
    - Log scrap/quality issues and good production counts.
    - View recent activity history.
    - URL parameter support for setting default context (e.g., `?line=Line A&machine=Robot 1`).
- **Supervisor Dashboard**:
    - Shift performance overview.
    - Pareto charts for Downtime (minutes) and Scrap (quantity).
    - Machine-level summary metrics (Uptime %, Good vs Scrap).
- **Maintenance View**:
    - Real-time queue of active/open downtime events.
    - Acknowledge dispatch (timestamps response time).
    - Log resolution notes and close tickets directly.
- **Admin Config**:
    - Manage Master Data: Lines, Machines, Operators, and Reason Codes.

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd andon-app
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the App

1.  Start the Streamlit server:
    ```bash
    streamlit run app.py
    ```

2.  Open your browser to the URL shown (usually `http://localhost:8501`).
3.  **First Run**: The application will automatically create a SQLite database (`andon.db`) and seed it with sample data (Lines, Machines, Reasons, etc.).

## Project Structure

```text
.
├── app.py                   # Main entry point & landing page
├── config.py                # Configuration (Shifts, DB path)
├── db.py                    # Database helpers & schema definition
├── requirements.txt         # Python dependencies
├── pages/
│   ├── 1_Operator_Panel.py       # Operator interface
│   ├── 2_Supervisor_Dashboard.py # Metrics & Charts
│   ├── 3_Admin_Config.py         # Master data management
│   └── 4_Maintenance_View.py     # Maintenance ticket management
└── README.md
```

## Usage Tips

- **URL Params for Tablets**: You can bookmark specific machine contexts for operators:
  `http://localhost:8501/Operator_Panel?line=Line%20A&machine=Conveyor%201&operator=John%20Doe`
- **Database**: The app uses a local `andon.db` SQLite file. To reset the data, simply delete this file and restart the app; it will re-seed automatically.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

