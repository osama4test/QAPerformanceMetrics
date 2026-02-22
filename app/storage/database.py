# database.py

import sqlite3
from pathlib import Path


# ======================================================
# Base Paths (Corrected)
# ======================================================

# database.py is inside:
# qa_sprint_coverage_tool/app/storage/

BASE_DIR = Path(__file__).resolve().parents[2]  # qa_sprint_coverage_tool
DATA_DIR = BASE_DIR / "data"

# Ensure data folder exists inside qa_sprint_coverage_tool
DATA_DIR.mkdir(exist_ok=True)

# Database full path
DB_NAME = DATA_DIR / "qa_metrics.db"


# ======================================================
# Initialize Database
# ======================================================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # --------------------------------------------------
    # Story Details Table
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS story_details (
            sprint TEXT NOT NULL,
            story_id INTEGER NOT NULL,
            title TEXT,
            qa TEXT,
            coverage REAL,
            scenario_coverage REAL,
            test_depth REAL,
            governance REAL,
            ac_quality REAL,
            qa_performance REAL,
            risk TEXT,
            compliance TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (story_id, sprint)
        )
    """)

    # --------------------------------------------------
    # Indexes (Performance Optimization)
    # --------------------------------------------------

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_story_sprint
        ON story_details (sprint)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_story_qa
        ON story_details (qa)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_story_risk
        ON story_details (risk)
    """)

    conn.commit()
    conn.close()