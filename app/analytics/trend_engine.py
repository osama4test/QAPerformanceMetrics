import sqlite3
import pandas as pd
from pathlib import Path

from app.storage.database import DB_NAME


# ======================================================
# Correct Paths
# ======================================================

BASE_DIR = Path(__file__).resolve().parents[2]  # qa_sprint_coverage_tool
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "qa_history.csv"


# ======================================================
# Load History Data
# ======================================================

def _load_history_data():
    """
    Loads history data from:
    1️⃣ SQLite (preferred)
    2️⃣ CSV fallback (backward compatibility)
    """

    # --------------------------------------------
    # Try SQLite first
    # --------------------------------------------
    if Path(DB_NAME).exists():
        try:
            conn = sqlite3.connect(DB_NAME)
            df = pd.read_sql_query("SELECT * FROM qa_history", conn)
            conn.close()

            if not df.empty:
                return df

        except Exception:
            pass

    # --------------------------------------------
    # Fallback to CSV
    # --------------------------------------------
    if HISTORY_FILE.exists():
        try:
            return pd.read_csv(HISTORY_FILE)
        except Exception:
            return pd.DataFrame()

    return pd.DataFrame()


# ======================================================
# Trend Calculation
# ======================================================

def calculate_trends(window=3):
    """
    Analyze last N sprint runs per QA.

    Trends calculated on:
    - Coverage %
    - QA Performance Score
    """

    df = _load_history_data()

    if df.empty:
        return []

    # --------------------------------------------
    # Normalize DB column names to CSV format
    # --------------------------------------------

    if "run_date" in df.columns:
        df.rename(columns={
            "run_date": "Run_Date",
            "coverage": "Coverage %",
            "qa_performance": "QA Performance Score"
        }, inplace=True)

    required_columns = [
        "Run_Date",
        "QA",
        "Coverage %",
        "QA Performance Score"
    ]

    for col in required_columns:
        if col not in df.columns:
            return []

    # --------------------------------------------
    # Data Type Safety
    # --------------------------------------------

    df["Run_Date"] = pd.to_datetime(df["Run_Date"], errors="coerce")
    df["Coverage %"] = pd.to_numeric(df["Coverage %"], errors="coerce").fillna(0)
    df["QA Performance Score"] = pd.to_numeric(
        df["QA Performance Score"], errors="coerce"
    ).fillna(0)

    results = []

    # --------------------------------------------
    # Calculate Per QA
    # --------------------------------------------

    for qa in df["QA"].dropna().unique():

        qa_df = df[df["QA"] == qa].sort_values("Run_Date")

        recent = qa_df.tail(window)

        if len(recent) < 2:
            continue

        coverage_trend = (
            recent["Coverage %"].iloc[-1]
            - recent["Coverage %"].iloc[0]
        )

        performance_trend = (
            recent["QA Performance Score"].iloc[-1]
            - recent["QA Performance Score"].iloc[0]
        )

        coverage_std = recent["Coverage %"].std()

        # Leadership Flag
        flag = "Stable"

        if coverage_trend < -10:
            flag = "Coverage Declining"
        elif coverage_trend > 10:
            flag = "Improving"
        elif coverage_std and coverage_std > 15:
            flag = "Volatile"

        results.append({
            "QA": qa,
            "Coverage Trend": round(coverage_trend, 2),
            "Performance Trend": round(performance_trend, 2),
            "Coverage Volatility": round(coverage_std, 2) if coverage_std else 0,
            "Performance Flag": flag
        })

    return results