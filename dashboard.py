import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

HISTORY_FILE = "qa_history.csv"

# ======================================================
# Page Config
# ======================================================

st.set_page_config(
    page_title="QA Intelligence Dashboard",
    layout="wide",
    page_icon="📊"
)

# ======================================================
# Executive Styling
# ======================================================

st.markdown("""
<style>
html, body, [class*="css"]  {
    font-family: 'Segoe UI', sans-serif;
}

.main {
    background: linear-gradient(180deg, #0f172a 0%, #0b1120 100%);
}

h1, h2, h3 {
    color: #ffffff;
}

.metric-card {
    background-color: #111827;
    padding: 25px;
    border-radius: 14px;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.4);
}

.section-card {
    background-color: #0f172a;
    padding: 25px;
    border-radius: 16px;
    margin-bottom: 25px;
    box-shadow: 0px 6px 25px rgba(0,0,0,0.35);
}
</style>
""", unsafe_allow_html=True)

st.title("QA Performance Metrics Dashboard")

# ======================================================
# Load Data Safely
# ======================================================

if not os.path.exists(HISTORY_FILE):
    st.warning("No history data found. Run main.py first.")
    st.stop()

df = pd.read_csv(HISTORY_FILE)

if df.empty:
    st.warning("History file is empty.")
    st.stop()

# Replace problematic "-" with None (Arrow safe)
df = df.replace("-", None)

# ======================================================
# Required Columns (Safe Defaults)
# ======================================================

required_columns = [
    "Sprint",
    "QA",
    "Stories",
    "QA Performance Score",
    "Governance Score",
    "AC Quality Score",
    "Coverage %",
    "High Risk %",
    "Coverage Contribution",
    "Scenario Contribution",
    "Test Depth Contribution",
    "Governance Contribution",
    "AC Quality Contribution",
    "Penalty Applied",
    "Complexity Multiplier"
]

for col in required_columns:
    if col not in df.columns:
        df[col] = 0

# Convert numeric columns safely
numeric_cols = [c for c in required_columns if c not in ["Sprint", "QA"]]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# ======================================================
# Sprint Selector
# ======================================================

sprints = sorted(df["Sprint"].dropna().unique())

if not sprints:
    st.warning("No sprint data available.")
    st.stop()

selected_sprint = st.selectbox("📅 Select Sprint", sprints)

sprint_df = df[df["Sprint"] == selected_sprint]

if sprint_df.empty:
    st.warning("No data for selected sprint.")
    st.stop()

# ======================================================
# Executive KPI Cards
# ======================================================

avg_qii = round(sprint_df["QA Performance Score"].mean(), 2)
avg_governance = round(sprint_df["Governance Score"].mean(), 2)
avg_ac_quality = round(sprint_df["AC Quality Score"].mean(), 2)
high_risk_ratio = round(sprint_df["High Risk %"].mean(), 2)

col1, col2, col3, col4 = st.columns(4)

col1.metric("🔥 QA Intelligence Index (0–100)", avg_qii)
col2.metric("🛡 Governance Health (0–100)", avg_governance)
col3.metric("📑 AC Quality (0–100)", avg_ac_quality)
col4.metric("⚠ High Risk %", f"{high_risk_ratio}%")

st.divider()

# ======================================================
# QA Performance Overview
# ======================================================

st.subheader("🏆 QA Performance Ranking")

qa_summary = sprint_df.groupby("QA").agg({
    "Stories": "sum",
    "QA Performance Score": "mean",
    "Governance Score": "mean",
    "AC Quality Score": "mean",
    "Coverage %": "mean",
    "High Risk %": "mean"
}).reset_index()

qa_summary = qa_summary.sort_values(
    "QA Performance Score",
    ascending=False
)

st.dataframe(qa_summary, width="stretch")

st.divider()

# ======================================================
# QII Breakdown
# ======================================================

st.subheader("🔎 QII Contribution Breakdown")

selected_qa = st.selectbox(
    "Select QA",
    qa_summary["QA"].unique()
)

qa_data = sprint_df[sprint_df["QA"] == selected_qa]
avg_values = qa_data.mean(numeric_only=True)

# Weight model (for transparency)
weights = {
    "Coverage": 25,
    "Scenario": 20,
    "Test Depth": 15,
    "Governance": 15,
    "AC Quality": 10
}

component_map = {
    "Coverage": "Coverage Contribution",
    "Scenario": "Scenario Contribution",
    "Test Depth": "Test Depth Contribution",
    "Governance": "Governance Contribution",
    "AC Quality": "AC Quality Contribution"
}

rows = []

for label, column in component_map.items():

    contribution = float(avg_values.get(column, 0))
    max_val = weights[label]

    utilization = round((contribution / max_val) * 100, 1) if max_val else 0

    rows.append({
        "Component": label,
        "Contribution (Points)": round(contribution, 2),
        "Max Possible (Points)": max_val,
        "Utilization %": utilization
    })

penalty = float(avg_values.get("Penalty Applied", 0))

if penalty > 0:
    rows.append({
        "Component": "Penalty Applied",
        "Contribution (Points)": -round(penalty, 2),
        "Max Possible (Points)": 0,
        "Utilization %": 0
    })

breakdown_df = pd.DataFrame(rows)

st.dataframe(breakdown_df, width="stretch")

# ======================================================
# Stacked Bar Chart
# ======================================================

fig = go.Figure()

for label, column in component_map.items():
    fig.add_bar(
        name=label,
        x=["QII"],
        y=[avg_values.get(column, 0)]
    )

if penalty > 0:
    fig.add_bar(
        name="Penalty",
        x=["QII"],
        y=[-penalty]
    )

fig.update_layout(
    barmode="relative",
    template="plotly_dark",
    height=450,
    title=f"QII Composition — {selected_qa}",
    yaxis_title="Contribution Points"
)

st.plotly_chart(fig, width="stretch")

st.markdown(
    f"**Complexity Multiplier Applied:** {round(avg_values.get('Complexity Multiplier',1),2)}"
)

st.divider()

# ======================================================
# QII Trend Over Time
# ======================================================

st.subheader("📈 QII Trend Over Time")

trend_df = df.groupby(["Sprint", "QA"])["QA Performance Score"].mean().reset_index()

pivot_df = trend_df.pivot(index="Sprint", columns="QA", values="QA Performance Score")

st.line_chart(pivot_df)

st.divider()

# ======================================================
# Governance Alerts
# ======================================================

st.subheader("🚨 Governance Alerts (Score < 70)")

gov_alerts = qa_summary[qa_summary["Governance Score"] < 70]

if gov_alerts.empty:
    st.success("No governance concerns detected.")
else:
    st.dataframe(gov_alerts[["QA", "Governance Score"]], width="stretch")

st.divider()

# ======================================================
# High Risk Alerts
# ======================================================

st.subheader("⚠ High Risk QAs (>30%)")

risk_alerts = qa_summary[qa_summary["High Risk %"] > 30]

if risk_alerts.empty:
    st.success("No high risk alerts detected.")
else:
    st.dataframe(risk_alerts[["QA", "High Risk %"]], width="stretch")
