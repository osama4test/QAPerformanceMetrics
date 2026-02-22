import os
import pandas as pd

# 🔥 Single source of truth for data path
from app.storage.database import DATA_DIR


# ======================================================
# Output Path (inside qa_sprint_coverage_tool/data)
# ======================================================

OUTPUT_FILE = os.path.join(DATA_DIR, "qa_intelligence_report.xlsx")


# ======================================================
# Save Report
# ======================================================

def save_report(rows):
    """
    Generates:
    1) Story-level detailed sheet
    2) QA summary sheet
    3) Intelligent metrics aggregation

    ✅ Stored inside qa_sprint_coverage_tool/data
    """

    if not rows:
        print("⚠ No data to export.")
        return

    df = pd.DataFrame(rows)

    # ======================================================
    # Safe Default Columns
    # ======================================================

    if "Estimation Accuracy %" not in df.columns:
        df["Estimation Accuracy %"] = None

    if "Test Depth Score" not in df.columns:
        df["Test Depth Score"] = None

    if "QA Performance Score" not in df.columns:
        df["QA Performance Score"] = None

    # Ensure numeric columns are numeric
    numeric_cols = [
        "Coverage %",
        "Estimation Accuracy %",
        "QA Performance Score"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ======================================================
    # QA Summary (Vectorized)
    # ======================================================

    summary_df = (
        df.groupby("QA")
        .agg(
            Stories=("Story ID", "count"),
            Avg_Coverage=("Coverage %", "mean"),
            Avg_Accuracy=("Estimation Accuracy %", "mean"),
            Avg_Performance=("QA Performance Score", "mean"),
            High_Risk_Stories=("Risk", lambda x: x.isin(["High", "Critical"]).sum())
        )
        .reset_index()
    )

    summary_df["Avg_Coverage"] = summary_df["Avg_Coverage"].round(2)
    summary_df["Avg_Accuracy"] = summary_df["Avg_Accuracy"].round(2)
    summary_df["Avg_Performance"] = summary_df["Avg_Performance"].round(2)

    summary_df.rename(columns={
        "Avg_Coverage": "Avg Coverage %",
        "Avg_Accuracy": "Avg Estimation Accuracy %",
        "Avg_Performance": "Avg QA Performance Score"
    }, inplace=True)

    # ======================================================
    # Write Excel
    # ======================================================

    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:

        df.to_excel(writer, sheet_name="Story Details", index=False)
        summary_df.to_excel(writer, sheet_name="QA Summary", index=False)

        workbook = writer.book
        worksheet = writer.sheets["Story Details"]

        # ----------------------------------------------
        # Coverage Conditional Formatting
        # ----------------------------------------------

        if "Coverage %" in df.columns:
            col_idx = df.columns.get_loc("Coverage %")

            worksheet.conditional_format(
                1, col_idx,
                len(df), col_idx,
                {
                    "type": "3_color_scale",
                    "min_color": "#F8696B",
                    "mid_color": "#FFEB84",
                    "max_color": "#63BE7B"
                }
            )

        # ----------------------------------------------
        # Estimation Accuracy Formatting
        # ----------------------------------------------

        if "Estimation Accuracy %" in df.columns:
            col_idx = df.columns.get_loc("Estimation Accuracy %")

            worksheet.conditional_format(
                1, col_idx,
                len(df), col_idx,
                {
                    "type": "3_color_scale",
                    "min_color": "#F8696B",
                    "mid_color": "#FFEB84",
                    "max_color": "#63BE7B"
                }
            )

        # ----------------------------------------------
        # Risk Highlighting
        # ----------------------------------------------

        if "Risk" in df.columns:
            col_idx = df.columns.get_loc("Risk")

            critical_format = workbook.add_format({"bg_color": "#F8696B"})
            high_format = workbook.add_format({"bg_color": "#FFB366"})

            worksheet.conditional_format(
                1, col_idx,
                len(df), col_idx,
                {
                    "type": "text",
                    "criteria": "containing",
                    "value": "Critical",
                    "format": critical_format
                }
            )

            worksheet.conditional_format(
                1, col_idx,
                len(df), col_idx,
                {
                    "type": "text",
                    "criteria": "containing",
                    "value": "High",
                    "format": high_format
                }
            )

    print(f"\n✅ Intelligence report saved: {OUTPUT_FILE}\n")