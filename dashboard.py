import os
import pandas as pd
import plotly.express as px
import streamlit as st
import psycopg2
from dotenv import load_dotenv

# Force Non-Interactive Matplotlib Backend to prevent Docker Segfaults
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

load_dotenv()

# ============================================================
#  PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Open Library Book Trends",
    page_icon="📚",
    layout="wide"
)

# ============================================================
#  DATABASE CONNECTION & LOADERS
# ============================================================

def get_connection():
    """Establishes and returns a fresh connection to PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        database=os.getenv("POSTGRES_DB", "books_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432))
    )

@st.cache_data(ttl=600)
def load_summary():
    """Loads the aggregated dbt mart model."""
    with get_connection() as conn:
        return pd.read_sql(
            "SELECT * FROM analytics.subject_decade_summary ORDER BY subject, decade",
            conn
        )

@st.cache_data(ttl=600)
def load_authors():
    """Loads top 10 authors from raw data."""
    query = """
        SELECT 
            an.value AS author, 
            COUNT(*) AS book_count
        FROM 
            raw.books__author_name an
        GROUP BY 
            an.value
        ORDER BY 
            book_count DESC
        LIMIT 10;
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn)

# ============================================================
#  LOAD DATA
# ============================================================

try:
    df = load_summary()
except Exception as e:
    st.error(f"Could not connect to database. Make sure PostgreSQL is running.\n\nError: {e}")
    st.stop()

# ============================================================
#  SIDEBAR FILTERS
# ============================================================

st.sidebar.title("Filters")

all_subjects = sorted(df["subject"].dropna().unique().tolist())

selected_subjects = st.sidebar.multiselect(
    "Select Subjects",
    options=all_subjects,
    default=all_subjects,
    key="selected_subjects_filter"
)

valid_decades = df["decade"].dropna()
if not valid_decades.empty:
    min_decade = int(valid_decades.min())
    max_decade = int(valid_decades.max())
else:
    min_decade, max_decade = 1900, 2020

decade_range = st.sidebar.slider(
    "Decade Range",
    min_value=min_decade,
    max_value=max_decade,
    value=(min_decade, max_decade),
    step=10,
    key="decade_range_slider"
)

# Filter Data in Memory
filtered_df = df[
    (df["subject"].isin(selected_subjects)) &
    (df["decade"] >= decade_range[0]) &
    (df["decade"] <= decade_range[1])
].copy()

# ============================================================
#  MAIN DASHBOARD
# ============================================================

st.title("📚 Open Library Book Trends")
st.markdown("Analysing publishing trends across subjects and decades using Open Library data.")

if filtered_df.empty:
    st.warning("⚠️ No data available for the selected filters. Please select more subjects or widen the decade range.")
    st.stop()

# ----------------------------------------------------------
#  KPI ROW
# ----------------------------------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="📖 Total Books",
        value=f"{int(filtered_df['book_count'].sum()):,}"
    )

with col2:
    st.metric(
        label="🧪 Subjects Covered",
        value=filtered_df["subject"].nunique()
    )

with col3:
    st.metric(
        label="📅 Decade Range",
        value=f"{decade_range[0]}s – {decade_range[1]}s"
    )

st.divider()

# ----------------------------------------------------------
#  CHART 1 — Bar Chart: Total books per subject
# ----------------------------------------------------------

st.subheader("📊 Most Published Subjects")

subject_totals = (
    filtered_df
    .groupby("subject")["book_count"]
    .sum()
    .reset_index()
    .sort_values("book_count", ascending=False)
    .head(10)
)

fig1 = px.bar(
    subject_totals,
    x="subject",
    y="book_count",
    color="subject",
    labels={"book_count": "Number of Books", "subject": "Subject"},
    title="Top 10 Most Published Subjects"
)
fig1.update_layout(showlegend=False)
st.plotly_chart(fig1, use_container_width=True, key="plotly_bar_subjects")

st.divider()

# ----------------------------------------------------------
#  CHART 2 — Line Chart: Total books published per decade
# ----------------------------------------------------------

st.subheader("📈 Publishing Trend Over Time")

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
fig2.update_traces(line_color="#2563eb", line_width=3)
st.plotly_chart(fig2, use_container_width=True, key="plotly_line_decades")

st.divider()

# ----------------------------------------------------------
#  CHART 3 — Line Chart: Per-subject trend over decades
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
st.plotly_chart(fig3, use_container_width=True, key="plotly_line_subject_trends")

st.divider()

# ----------------------------------------------------------
#  TABLE — Top 10 most prolific authors
# ----------------------------------------------------------

st.subheader("✍️ Top 10 Most Prolific Authors")

try:
    top_authors = load_authors()
    if not top_authors.empty:
        top_authors.columns = ["Author", "Book Count"]
        top_authors.index = top_authors.index + 1
        st.dataframe(top_authors, use_container_width=True)
    else:
        st.info("No author data available.")
except Exception as e:
    st.info(f"Author data not available. (Error: {e})")

st.divider()

# ----------------------------------------------------------
#  STRETCH GOAL 1 — Subject Volume Ranking
# ----------------------------------------------------------

st.subheader("🏷️ Subject Volume Ranking")

fig_bar_sub = px.bar(
    subject_totals,
    x="book_count",
    y="subject",
    orientation="h",
    labels={"book_count": "Total Books", "subject": "Subject"},
    title="Subject Volume Ranking",
    color="book_count",
    color_continuous_scale="Viridis"
)
fig_bar_sub.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_bar_sub, use_container_width=True, key="plotly_bar_ranking")

st.divider()

# ----------------------------------------------------------
#  STRETCH GOAL 2 — Side by Side Comparison
# ----------------------------------------------------------

st.subheader("🔄 Compare Two Subjects Side by Side")

all_subjects_list = sorted(df["subject"].dropna().unique().tolist())

comp_col1, comp_col2 = st.columns(2)

with comp_col1:
    subject_a = st.selectbox(
        "Subject A",
        options=all_subjects_list,
        index=0,
        key="select_subject_a"
    )

with comp_col2:
    subject_b = st.selectbox(
        "Subject B",
        options=all_subjects_list,
        index=min(1, len(all_subjects_list) - 1),
        key="select_subject_b"
    )

comparison_df = df[df["subject"].isin([subject_a, subject_b])]

if subject_a == subject_b:
    st.warning("Please select two different subjects to compare.")
elif comparison_df.empty:
    st.info("No comparison data available for these specific subjects.")
else:
    kpi_a = int(comparison_df[comparison_df["subject"] == subject_a]["book_count"].sum())
    kpi_b = int(comparison_df[comparison_df["subject"] == subject_b]["book_count"].sum())

    kpi1, kpi2 = st.columns(2)
    with kpi1:
        st.metric(label=f"Total Books — {str(subject_a).title()}", value=f"{kpi_a:,}")
    with kpi2:
        st.metric(label=f"Total Books — {str(subject_b).title()}", value=f"{kpi_b:,}")

    fig_comp = px.line(
        comparison_df,
        x="decade",
        y="book_count",
        color="subject",
        markers=True,
        labels={"book_count": "Number of Books", "decade": "Decade", "subject": "Subject"},
        title=f"{str(subject_a).title()} vs {str(subject_b).title()} — Publishing Trend by Decade"
    )
    fig_comp.update_traces(line_width=3)
    st.plotly_chart(fig_comp, use_container_width=True, key="plotly_comp_line")

st.divider()

# ----------------------------------------------------------
#  TABLE — Full mart model data
# ----------------------------------------------------------

st.subheader("📋 Full Summary Table")
st.dataframe(
    filtered_df.sort_values(["subject", "decade"]),
    use_container_width=True,
    hide_index=True
)