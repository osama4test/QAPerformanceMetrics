import pandas as pd
import os

HISTORY_FILE = "qa_history.csv"


def calculate_trends(window=3):
    """
    Analyze last N sprint runs per QA.

    Trends calculated on:
    - Coverage %
    - QA Performance Score

    Uses Run_Date for proper chronological ordering.
    """

    if not os.path.exists(HISTORY_FILE):
        return []

    df = pd.read_csv(HISTORY_FILE)

    if df.empty:
        return []

    # Ensure Run_Date exists and is datetime
    if "Run_Date" not in df.columns:
        return []

    df["Run_Date"] = pd.to_datetime(df["Run_Date"])

    results = []

    for qa in df["QA"].unique():

        # Sort chronologically (IMPORTANT)
        qa_df = df[df["QA"] == qa].sort_values("Run_Date")

        recent = qa_df.tail(window)

        if len(recent) < 2:
            continue

        # --------------------------------------------------
        # Coverage Trend
        # --------------------------------------------------
        coverage_trend = (
            recent["Coverage %"].iloc[-1]
            - recent["Coverage %"].iloc[0]
        )

        # --------------------------------------------------
        # QA Performance Trend
        # --------------------------------------------------
        performance_trend = (
            recent["QA Performance Score"].iloc[-1]
            - recent["QA Performance Score"].iloc[0]
        )

        # --------------------------------------------------
        # Volatility (stability indicator)
        # --------------------------------------------------
        coverage_std = recent["Coverage %"].std()

        # --------------------------------------------------
        # Leadership Flag Logic
        # --------------------------------------------------
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
