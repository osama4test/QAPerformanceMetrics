import streamlit as st
import pandas as pd
import os
import sqlite3
import time
import sys

# ======================================================
# FIX PYTHON PATH
# ======================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import run_qa_analysis

# ======================================================
# Paths
# ======================================================

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_NAME = os.path.join(DATA_DIR, "qa_metrics.db")

DEVOPS_BASE_URL = "https://dev.azure.com/frontline-data-solutions/EHS/_workitems/edit/"

# ======================================================
# Page Config
# ======================================================

st.set_page_config(
    page_title="QA Execution Dashboard",
    layout="wide",
    page_icon="📊"
)

st.title("QA Performance Metrics Dashboard")

# ======================================================
# 🚀 Run QA Analysis (AUTO SPRINT DETECTION)
# ======================================================

st.subheader("🚀 Run New QA Analysis")

query_id = st.text_input("Enter Azure DevOps Query GUID")

if st.button("Run QA Analysis"):

    if not query_id:
        st.error("Please enter Query GUID.")
    else:
        progress_bar = st.progress(0)
        progress_text = st.empty()

        # 🔥 Live Progress Update Function
        def update_progress(percent, current, total):
            progress_bar.progress(percent)
            progress_text.markdown(
                f"### {percent}% Complete\n"
                f"Processing story {current} of {total}"
            )
            time.sleep(0.05)  # 🔥 REQUIRED for Streamlit UI refresh

        try:
            # 🔥 Execute analysis with progress callback
            result = run_qa_analysis(
                query_id,
                progress_callback=update_progress
            )

            # Ensure final 100% state
            progress_bar.progress(100)
            progress_text.markdown("### 100% Complete ✅")

            if result.get("status") == "Success":
                st.success(
                    f"✅ Sprint '{result.get('sprint')}' processed successfully. "
                    f"{result.get('stories_processed')} stories analyzed."
                )
                time.sleep(1)
                st.rerun()

            elif result.get("status") == "Skipped":
                st.warning(
                    f"⚠ Already executed today for sprint '{result.get('sprint')}'."
                )

            else:
                st.warning("No QA data processed.")

        except Exception as e:
            st.error(f"Error running analysis: {e}")

st.divider()

# ======================================================
# Load History
# ======================================================

def load_history():
    if os.path.exists(DB_NAME):
        try:
            conn = sqlite3.connect(DB_NAME)
            df = pd.read_sql_query("SELECT * FROM qa_history", conn)
            conn.close()

            if not df.empty:
                df.rename(columns={
                    "run_date": "Run_Date",
                    "sprint": "Sprint",
                    "qa": "QA",
                    "stories": "Stories",
                    "coverage": "Coverage %",
                    "scenario_coverage": "Scenario Coverage %",
                    "test_depth": "Test Depth Score",
                    "governance": "Governance Score",
                    "ac_quality": "AC Quality Score",
                    "qa_performance": "QA Performance Score",
                    "high_risk": "High Risk %",
                    "process_compliance": "Process Compliance %"
                }, inplace=True)

                df["Run_Date"] = pd.to_datetime(df["Run_Date"], errors="coerce")
                return df

        except Exception:
            pass

    return pd.DataFrame()


history_df = load_history()

if history_df.empty:
    st.warning("No history data found.")
    st.stop()

# ======================================================
# 🟢 ACTIVE SPRINT BADGE
# ======================================================

latest_row = history_df.sort_values("Run_Date", ascending=False).iloc[0]
active_sprint = latest_row["Sprint"]

st.success(f"🟢 Active Sprint: {active_sprint}")

st.divider()

# ======================================================
# Sprint Selector
# ======================================================

sprints = sorted(history_df["Sprint"].dropna().unique())

selected_sprint = st.selectbox(
    "📅 Select Sprint",
    sprints,
    index=sprints.index(active_sprint) if active_sprint in sprints else 0
)

# ======================================================
# 🗑️ Delete Sprint
# ======================================================

st.markdown("### 🗑️ Delete Sprint")

confirm_delete = st.checkbox(f"I confirm deletion of sprint: {selected_sprint}")

if st.button("Delete Selected Sprint"):

    if not confirm_delete:
        st.error("Please confirm deletion first.")
    else:
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM qa_history WHERE sprint = ?", (selected_sprint,))
            cursor.execute("DELETE FROM story_details WHERE sprint = ?", (selected_sprint,))

            conn.commit()
            conn.close()

            st.success(f"Sprint '{selected_sprint}' deleted successfully.")
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"Error deleting sprint: {e}")

st.divider()

# ======================================================
# KPI Cards
# ======================================================

sprint_df = history_df[history_df["Sprint"] == selected_sprint]

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("🎯 QA Execution Score", round(sprint_df["QA Performance Score"].mean(), 2))
col2.metric("📊 Avg Coverage %", round(sprint_df["Coverage %"].mean(), 2))
col3.metric("🛡 Governance Health", round(sprint_df["Governance Score"].mean(), 2))
col4.metric("⚙ Process Compliance %", f"{round(sprint_df['Process Compliance %'].mean(), 2)}%")
col5.metric("⚠ High Risk %", f"{round(sprint_df['High Risk %'].mean(), 2)}%")

st.divider()

# ======================================================
# QA Ranking (Executive Version Only)
# ======================================================

st.subheader("🏆 QA Execution Ranking")

qa_summary = (
    sprint_df
    .groupby("QA")
    .agg(
        Stories=("Stories", "sum"),
        Avg_Performance=("QA Performance Score", "mean"),
        High_Risk_Percent=("High Risk %", "mean"),
        Compliance_Percent=("Process Compliance %", "mean")
    )
    .reset_index()
    .sort_values("Avg_Performance", ascending=False)
)

qa_summary = qa_summary.round(2)

qa_summary.columns = [
    "QA",
    "Stories",
    "Avg Performance",
    "High Risk %",
    "Compliance %"
]


st.dataframe(qa_summary, width="stretch")

st.divider()

# ======================================================
# Deep Dive (UNCHANGED)
# ======================================================
# ======================================================
# Violation Dialog
# ======================================================

@st.dialog("🚨 Story Violations")
def show_violations_dialog(story_id, violations):
    st.markdown(f"### Violations for Story {story_id}")
    st.divider()

    if not violations:
        st.success("No violations found.")
        return

    for idx, v in enumerate(violations, 1):
        st.markdown(f"**{idx}.** {v}")

    st.divider()
    st.caption(f"Total Violations: {len(violations)}")

st.subheader("🔎 QA Deep Dive")

conn = sqlite3.connect(DB_NAME)
story_df = pd.read_sql_query(
    "SELECT * FROM story_details WHERE sprint = ?",
    conn,
    params=(selected_sprint,)
)
conn.close()

if not story_df.empty:

    selected_qa = st.selectbox("Select QA", sorted(story_df["qa"].unique()))
    qa_story_df = story_df[story_df["qa"] == selected_qa]

# ======================================================
# Deep Dive With Clickable Violation Count (Stable)
# ======================================================

executive_df = qa_story_df.copy()

def split_violations(text):
    if not text or text == "Compliant":
        return []
    return [v.strip() for v in text.split("|") if v.strip()]

executive_df["Violation List"] = executive_df["compliance"].apply(split_violations)
executive_df["Violations"] = executive_df["Violation List"].apply(len)

display_df = executive_df[[
    "story_id",
    "title",
    "coverage",
    "scenario_coverage",
    "test_depth",
    "governance",
    "ac_quality",
    "qa_performance",
    "Violations"
]].copy()

display_df.columns = [
    "Story",
    "Title",
    "Coverage %",
    "Scenario Coverage %",
    "Test Depth",
    "Governance",
    "AC Quality",
    "Execution Score",
    "Violations"
]

# Convert Story ID to DevOps link
display_df["Story"] = display_df["Story"].apply(
    lambda x: f"{DEVOPS_BASE_URL}{int(x)}"
)

# Render table normally
st.dataframe(
    display_df.sort_values("Execution Score", ascending=False),
    column_config={
        "Story": st.column_config.LinkColumn(
            "Story",
            display_text=r".*/(\d+)$"
        ),
        "Violations": st.column_config.NumberColumn(
            "Violations",
            help="Number of governance violations"
        )
    },
    hide_index=True,
    width="stretch"
)

# ======================================================
# Separate Violation Viewer Section
# ======================================================

st.markdown("### 🔍 View Story Violations")

stories_with_violations = executive_df[executive_df["Violations"] > 0]

if not stories_with_violations.empty:

    selected_story_id = st.selectbox(
        "Select Story to View Violations",
        stories_with_violations["story_id"].astype(str)
    )

    selected_story = executive_df[
        executive_df["story_id"].astype(str) == selected_story_id
    ].iloc[0]

    if st.button("Show Violations"):

        show_violations_dialog(
            selected_story["story_id"],
            selected_story["Violation List"]
        )
else:
    st.success("No violations found for this QA.")
# ======================================================
# Trends (UNCHANGED)
# ======================================================

st.subheader("📈 QA Execution Trend")

trend_df = history_df.groupby(["Sprint", "QA"])["QA Performance Score"].mean().reset_index()
pivot_df = trend_df.pivot(index="Sprint", columns="QA", values="QA Performance Score")
st.line_chart(pivot_df)

st.divider()

st.subheader("📊 Coverage Trend")

coverage_df = history_df.groupby(["Sprint", "QA"])["Coverage %"].mean().reset_index()
coverage_pivot = coverage_df.pivot(index="Sprint", columns="QA", values="Coverage %")
st.line_chart(coverage_pivot)