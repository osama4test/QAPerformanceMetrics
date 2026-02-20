import pandas as pd
from collections import defaultdict


def save_report(rows):
    """
    Generates:
    1) Story-level detailed sheet
    2) QA summary sheet
    3) Intelligent metrics aggregation
    """

    if not rows:
        print("⚠ No data to export.")
        return

    df = pd.DataFrame(rows)

    # ======================================================
    # Add Derived Columns (Safe Defaults)
    # ======================================================

    if "Estimation Accuracy %" not in df.columns:
        df["Estimation Accuracy %"] = None

    if "Test Depth Score" not in df.columns:
        df["Test Depth Score"] = None

    if "QA Performance Score" not in df.columns:
        df["QA Performance Score"] = None

    # ======================================================
    # QA Summary Aggregation
    # ======================================================

    qa_summary = defaultdict(lambda: {
        "Stories": 0,
        "Avg Coverage %": 0,
        "Avg Accuracy %": 0,
        "Avg Performance Score": 0,
        "High Risk Stories": 0
    })

    for _, row in df.iterrows():
        qa = row.get("QA")

        if not qa:
            continue

        qa_summary[qa]["Stories"] += 1
        qa_summary[qa]["Avg Coverage %"] += row.get("Coverage %", 0)
        qa_summary[qa]["Avg Accuracy %"] += row.get("Estimation Accuracy %", 0) or 0
        qa_summary[qa]["Avg Performance Score"] += row.get("QA Performance Score", 0) or 0

        if row.get("Risk") in ["High", "Critical"]:
            qa_summary[qa]["High Risk Stories"] += 1

    summary_rows = []

    for qa, data in qa_summary.items():
        stories = data["Stories"]

        summary_rows.append({
            "QA": qa,
            "Stories": stories,
            "Avg Coverage %": round(data["Avg Coverage %"] / stories, 2) if stories else 0,
            "Avg Estimation Accuracy %": round(data["Avg Accuracy %"] / stories, 2) if stories else 0,
            "Avg QA Performance Score": round(data["Avg Performance Score"] / stories, 2) if stories else 0,
            "High Risk Stories": data["High Risk Stories"]
        })

    summary_df = pd.DataFrame(summary_rows)

    # ======================================================
    # Write Excel (Multiple Sheets)
    # ======================================================

    output_file = "qa_intelligence_report.xlsx"

    with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Story Details", index=False)
        summary_df.to_excel(writer, sheet_name="QA Summary", index=False)

        workbook = writer.book

        # ----------------------------------------------
        # Conditional Formatting - Coverage %
        # ----------------------------------------------
        worksheet = writer.sheets["Story Details"]

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
        # Conditional Formatting - Estimation Accuracy
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
        # Conditional Formatting - Risk Column
        # ----------------------------------------------
        if "Risk" in df.columns:
            col_idx = df.columns.get_loc("Risk")

            worksheet.conditional_format(
                1, col_idx,
                len(df), col_idx,
                {
                    "type": "text",
                    "criteria": "containing",
                    "value": "Critical",
                    "format": workbook.add_format({"bg_color": "#F8696B"})
                }
            )

            worksheet.conditional_format(
                1, col_idx,
                len(df), col_idx,
                {
                    "type": "text",
                    "criteria": "containing",
                    "value": "High",
                    "format": workbook.add_format({"bg_color": "#FFB366"})
                }
            )

    print(f"\n✅ Intelligence report saved: {output_file}\n")
