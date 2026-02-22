import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

from app.storage.database import DB_NAME


# ======================================================
# Correct Project Paths
# ======================================================

# history_engine.py is inside:
# qa_sprint_coverage_tool/app/analytics/

BASE_DIR = Path(__file__).resolve().parents[2]  # qa_sprint_coverage_tool
DATA_DIR = BASE_DIR / "data"

# Ensure data folder exists inside qa_sprint_coverage_tool
DATA_DIR.mkdir(exist_ok=True)

HISTORY_FILE = DATA_DIR / "qa_history.csv"


# ======================================================
# Append History
# ======================================================

def append_history(sprint_name, rows):
    """
    Append QA-level execution summary per sprint.

    Writes:
    ✅ CSV (dashboard compatibility)
    ✅ SQLite (primary storage)
    """

    if not rows:
        return

    df = pd.DataFrame(rows)

    if df.empty:
        return

    # --------------------------------------------------
    # Required Columns Safety
    # --------------------------------------------------

    required_cols = [
        "Coverage %",
        "Scenario Coverage %",
        "Test Depth Score",
        "Governance Score",
        "AC Quality Score",
        "QA Performance Score",
        "Risk"
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    if "Compliance Status" not in df.columns:
        df["Compliance Status"] = "Compliant"

    numeric_cols = [
        "Coverage %",
        "Scenario Coverage %",
        "Test Depth Score",
        "Governance Score",
        "AC Quality Score",
        "QA Performance Score"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # --------------------------------------------------
    # Aggregate Per QA
    # --------------------------------------------------

    grouped = df.groupby("QA")

    summary = grouped.agg({
        "Coverage %": "mean",
        "Scenario Coverage %": "mean",
        "Test Depth Score": "mean",
        "Governance Score": "mean",
        "AC Quality Score": "mean",
        "QA Performance Score": "mean"
    }).reset_index()

    summary["Stories"] = grouped.size().values

    # High Risk %
    high_risk_counts = grouped["Risk"].apply(
        lambda x: x.isin(["Critical", "High"]).sum()
    ).values

    summary["High Risk %"] = (
        (high_risk_counts / summary["Stories"]) * 100
    ).round(2)

    # Process Compliance %
    compliance_counts = grouped["Compliance Status"].apply(
        lambda x: (x == "Compliant").sum()
    ).values

    summary["Process Compliance %"] = (
        (compliance_counts / summary["Stories"]) * 100
    ).round(2)

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    run_date = datetime.now()
    summary["Sprint"] = sprint_name
    summary["Run_Date"] = run_date

    summary = summary[[
        "Run_Date",
        "Sprint",
        "QA",
        "Stories",
        "Coverage %",
        "Scenario Coverage %",
        "Test Depth Score",
        "Governance Score",
        "AC Quality Score",
        "QA Performance Score",
        "High Risk %",
        "Process Compliance %"
    ]]

    # Round numeric columns cleanly
    numeric_cols_summary = summary.select_dtypes(include=["number"]).columns
    summary[numeric_cols_summary] = summary[numeric_cols_summary].round(2)

    # ==================================================
    # 1️⃣ CSV Persistence (Correct Folder)
    # ==================================================

    if HISTORY_FILE.exists():
        try:
            history_df = pd.read_csv(HISTORY_FILE)

            if "Sprint" in history_df.columns:
                history_df = history_df[history_df["Sprint"] != sprint_name]

            if not history_df.empty:
                history_df = pd.concat([history_df, summary], ignore_index=True)
            else:
                history_df = summary

        except Exception:
            history_df = summary
    else:
        history_df = summary

    history_df.to_csv(HISTORY_FILE, index=False)

    # ==================================================
    # 2️⃣ SQLite Persistence (Primary Storage)
    # ==================================================

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qa_history (
            run_date TEXT,
            sprint TEXT,
            qa TEXT,
            stories INTEGER,
            coverage REAL,
            scenario_coverage REAL,
            test_depth REAL,
            governance REAL,
            ac_quality REAL,
            qa_performance REAL,
            high_risk REAL,
            process_compliance REAL,
            PRIMARY KEY (sprint, qa)
        )
    """)

    # Remove existing sprint entries (prevent duplicates)
    cursor.execute(
        "DELETE FROM qa_history WHERE sprint = ?",
        (sprint_name,)
    )

    for _, row in summary.iterrows():

        run_date_str = (
            row["Run_Date"].isoformat()
            if hasattr(row["Run_Date"], "isoformat")
            else str(row["Run_Date"])
        )

        cursor.execute("""
            INSERT INTO qa_history (
                run_date,
                sprint,
                qa,
                stories,
                coverage,
                scenario_coverage,
                test_depth,
                governance,
                ac_quality,
                qa_performance,
                high_risk,
                process_compliance
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_date_str,
            row["Sprint"],
            row["QA"],
            int(row["Stories"]),
            float(row["Coverage %"]),
            float(row["Scenario Coverage %"]),
            float(row["Test Depth Score"]),
            float(row["Governance Score"]),
            float(row["AC Quality Score"]),
            float(row["QA Performance Score"]),
            float(row["High Risk %"]),
            float(row["Process Compliance %"])
        ))

    conn.commit()
    conn.close()