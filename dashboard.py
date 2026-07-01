"""
dashboard.py — Open Library Book Trends Dashboard
ITC6050 Final Project — Group 4

Run with:
  docker-compose up streamlit
Then open: http://localhost:8501
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# ============================================================
#  PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="📚 Open Library Book Trends",
    page_icon="📚",
    layout="wide"
)

# ============================================================
#  DATABASE CONNECTION
# ============================================================
@st.cache_resource   # caches the connection so it doesn't reconnect on every interaction
def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        database=os.getenv("POSTGRES_DB", "books_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "books1234"),
        port=int(os.getenv("POSTGRES_PORT", 5432))
    )

@st.cache_data(ttl=300)   # caches query results for 5 minutes
def load_data():
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM analytics.subject_decade_summary ORDER BY subject, decade",
        conn
    )
    return df

# ============================================================
#  LOAD DATA
# ============================================================
try:
    df = load_data()
except Exception as e:
    st.error(f"❌ Could not connect to database. Make sure PostgreSQL is running and the pipeline has been executed.\n\nError: {e}")
    st.stop()

# ============================================================
#  SIDEBAR FILTERS
# ============================================================
st.sidebar.title("🔍 Filters")

# Subject filter
all_subjects = sorted(df["subject"].unique().tolist())
selected_subjects = st.sidebar.multiselect(
    "Select Subjects",
    options=all_subjects,
    default=all_subjects   # all selected by default
)

# Decade range filter
min_decade = int(df["decade"].min())
max_decade = int(df["decade"].max())
decade_range = st.sidebar.slider(
    "Decade Range",
    min_value=min_decade,
    max_value=max_decade,
    value=(min_decade, max_decade),
    step=10
)

# Apply filters
filtered_df = df[
    (df["subject"].isin(selected_subjects)) &
    (df["decade"] >= decade_range[0]) &
    (df["decade"] <= decade_range[1])
]

# ============================================================
#  MAIN DASHBOARD
# ============================================================
st.title("📚 Open Library Book Trends")
st.markdown("Analysing publishing trends across subjects and decades using Open Library data.")

# ----------------------------------------------------------
#  KPI ROW — the 3 big numbers at the top
# ----------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="📖 Total Books",
        value=f"{filtered_df['book_count'].sum():,}"
    )

with col2:
    st.metric(
        label="📂 Subjects Covered",
        value=filtered_df["subject"].nunique()
    )

with col3:
    st.metric(
        label="📅 Decades Covered",
        value=filtered_df["decade"].nunique()
    )

st.divider()

# ----------------------------------------------------------
#  CHART 1 — Bar Chart: Top subjects by book count
# ----------------------------------------------------------
st.subheader("📊 Most Published Subjects")

subject_totals = (
    filtered_df
    .groupby("subject")["book_count"]
    .sum()
    .reset_index()
    .sort_values("book_count", ascending=False)
)

fig1 = px.bar(
    subject_totals,
    x="subject",
    y="book_count",
    color="subject",
    labels={"book_count": "Number of Books", "subject": "Subject"},
    title="Total Books by Subject"
)
st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ----------------------------------------------------------
#  CHART 2 — Line Chart: Books published per decade
# ----------------------------------------------------------
st.subheader("📈 Publishing Trends Over Time")

decade_totals = (
    filtered_df
    .groupby("decade")["book_count"]
    .sum()
    .reset_index()
)

fig2 = px.line(
    decade_totals,
    x="decade",
    y="book_count",
    markers=True,
    labels={"book_count": "Number of Books", "decade": "Decade"},
    title="Books Published Per Decade"
)
st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ----------------------------------------------------------
#  CHART 3 — Line Chart per subject (one line per subject)
# ----------------------------------------------------------
st.subheader("📉 Trends by Subject")

fig3 = px.line(
    filtered_df,
    x="decade",
    y="book_count",
    color="subject",
    markers=True,
    labels={"book_count": "Number of Books", "decade": "Decade", "subject": "Subject"},
    title="Publishing Trend per Subject Over Decades"
)
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ----------------------------------------------------------
#  TABLE — Raw mart data for reference
# ----------------------------------------------------------
st.subheader("📋 Full Summary Table")

st.dataframe(
    filtered_df.sort_values(["subject", "decade"]),
    use_container_width=True,
    hide_index=True
)
