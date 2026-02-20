import os
import pandas as pd
from datetime import datetime

HISTORY_FILE = "qa_history.csv"


def append_history(sprint_name, rows):
    """
    Append QA-level intelligence summary per sprint.

    Tracks (per QA per sprint):
        - Stories count
        - Avg Coverage %
        - Avg Scenario Coverage %
        - Avg Test Depth Score
        - Avg Governance Score
        - Avg AC Quality Score
        - Avg QA Performance Score (QII)
        - High Risk %
        - QII Breakdown Contributions
        - Run timestamp
    """

    if not rows:
        return

    df = pd.DataFrame(rows)

    if df.empty:
        return

    # --------------------------------------------------
    # Ensure required columns exist (safe fallback)
    # --------------------------------------------------

    required_cols = [
        "Coverage %",
        "Scenario Coverage %",
        "Test Depth Score",
        "Governance Score",
        "AC Quality Score",
        "QA Performance Score",
        "Risk",
        "Coverage Contribution",
        "Scenario Contribution",
        "Test Depth Contribution",
        "Governance Contribution",
        "AC Quality Contribution",
        "Penalty Applied"
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    # Convert numeric columns safely
    numeric_cols = [
        "Coverage %",
        "Scenario Coverage %",
        "Test Depth Score",
        "Governance Score",
        "AC Quality Score",
        "QA Performance Score",
        "Coverage Contribution",
        "Scenario Contribution",
        "Test Depth Contribution",
        "Governance Contribution",
        "AC Quality Contribution",
        "Penalty Applied"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # --------------------------------------------------
    # Aggregate per QA
    # --------------------------------------------------

    grouped = df.groupby("QA")

    summary = grouped.agg({
        "Coverage %": "mean",
        "Scenario Coverage %": "mean",
        "Test Depth Score": "mean",
        "Governance Score": "mean",
        "AC Quality Score": "mean",
        "QA Performance Score": "mean",
        "Coverage Contribution": "mean",
        "Scenario Contribution": "mean",
        "Test Depth Contribution": "mean",
        "Governance Contribution": "mean",
        "AC Quality Contribution": "mean",
        "Penalty Applied": "mean"
    }).reset_index()

    # Stories count
    summary["Stories"] = grouped.size().values

    # High Risk %
    high_risk_counts = grouped["Risk"].apply(
        lambda x: x.isin(["Critical", "High"]).sum()
    ).values

    summary["High Risk %"] = (
        (high_risk_counts / summary["Stories"]) * 100
    ).round(2)

    # --------------------------------------------------
    # Add Metadata
    # --------------------------------------------------

    summary["Sprint"] = sprint_name
    summary["Run_Date"] = datetime.now()

    # Reorder columns cleanly
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

        "Coverage Contribution",
        "Scenario Contribution",
        "Test Depth Contribution",
        "Governance Contribution",
        "AC Quality Contribution",
        "Penalty Applied"
    ]]

    # Round metrics nicely
    numeric_cols = summary.select_dtypes(include=["number"]).columns
    summary[numeric_cols] = summary[numeric_cols].round(2)

    # --------------------------------------------------
    # Append or Replace Sprint Cleanly
    # --------------------------------------------------

    if os.path.exists(HISTORY_FILE):
        try:
            history_df = pd.read_csv(HISTORY_FILE)

            # Remove old records of same sprint (prevents duplication)
            history_df = history_df[history_df["Sprint"] != sprint_name]

            history_df = pd.concat([history_df, summary], ignore_index=True)

        except Exception:
            history_df = summary
    else:
        history_df = summary

    history_df.to_csv(HISTORY_FILE, index=False)
