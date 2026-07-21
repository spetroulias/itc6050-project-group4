"""
dashboard.py — Open Library Book Trends Dashboard
ITC6050 Final Project — Group 4

Presentation layer of the data pipeline. Reads transformed data from
PostgreSQL and renders an interactive dashboard using Streamlit.

Usage:
    docker-compose up streamlit
    Open: http://localhost:8501
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st
import psycopg2
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from dotenv import load_dotenv

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
#  DATABASE CONNECTION
# ============================================================

@st.cache_resource
def get_connection():
    """
    Establishes and returns a connection to the PostgreSQL database.
    Credentials are resolved from environment variables set in .env.
    """
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        database=os.getenv("POSTGRES_DB", "books_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.environ["POSTGRES_PASSWORD"],
        port=int(os.getenv("POSTGRES_PORT", 5432))
    )


@st.cache_data(ttl=300)
def load_summary():
    """
    Loads the dbt mart model: aggregated book counts by subject and decade.
    Primary data source for all charts on the dashboard.
    """
    conn = get_connection()
    return pd.read_sql(
        "SELECT * FROM analytics.subject_decade_summary ORDER BY subject, decade",
        conn
    )


@st.cache_data(ttl=300)
def load_books_raw():
    """
    Loads selected columns from the raw books table.
    Used for the year range KPI and word cloud generation.
    """
    conn = get_connection()
    return pd.read_sql(
        "SELECT title, searched_subject, first_publish_year FROM raw.books",
        conn
    )


@st.cache_data(ttl=300)
def load_authors():
    """
    Loads author names from the raw authors table.
    Used to generate the Top 10 Most Prolific Authors table.
    """
    conn = get_connection()
    return pd.read_sql("""
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
    """, conn)


# ============================================================
#  LOAD DATA
# ============================================================

try:
    df = load_summary()
    raw_books = load_books_raw()
except Exception as e:
    st.error(f"Could not connect to database. Make sure the pipeline has been run.\n\nError: {e}")
    st.stop()


# ============================================================
#  SIDEBAR FILTERS
# ============================================================

st.sidebar.title("Filters")

all_subjects = sorted(df["subject"].unique().tolist())

# Added a fixed key to prevent state loss on re-run
selected_subjects = st.sidebar.multiselect(
    "Select Subjects",
    options=all_subjects,
    default=all_subjects,
    key="selected_subjects_filter"
)

min_decade = int(df["decade"].min())
max_decade = int(df["decade"].max())
decade_range = st.sidebar.slider(
    "Decade Range",
    min_value=min_decade,
    max_value=max_decade,
    value=(min_decade, max_decade),
    step=10
)

# Apply filters to mart DataFrame
filtered_df = df[
    (df["subject"].isin(selected_subjects)) &
    (df["decade"] >= decade_range[0]) &
    (df["decade"] <= decade_range[1])
]

# Apply filters to raw books for year range KPI and word cloud
filtered_raw = raw_books[
    (raw_books["searched_subject"].isin(selected_subjects)) &
    (raw_books["first_publish_year"] >= decade_range[0]) &
    (raw_books["first_publish_year"] <= decade_range[1] + 9)
]


# ============================================================
#  MAIN DASHBOARD
# ============================================================

st.title("📚 Open Library Book Trends")
st.markdown("Analysing publishing trends across subjects and decades using Open Library data.")

# ----------------------------------------------------------
#  CRITICAL SAFETY CHECK: Stop processing if DataFrames are empty
# ----------------------------------------------------------
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
        value=f"{filtered_df['book_count'].sum():,}"
    )

with col2:
    st.metric(
        label="🧪 Subjects Covered",
        value=filtered_df["subject"].nunique()
    )

with col3:
    if not filtered_raw.empty and not filtered_raw["first_publish_year"].isna().all():
        min_year = int(filtered_raw["first_publish_year"].min())
        max_year = int(filtered_raw["first_publish_year"].max())
        st.metric(
            label="📅 Year Range",
            value=f"{min_year} – {max_year}"
        )
    else:
        st.metric(label="📅 Year Range", value="N/A")

st.divider()


# ----------------------------------------------------------
#  CHART 1 — Bar Chart: total books per subject
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
st.plotly_chart(fig1, use_container_width=True)

st.divider()


# ----------------------------------------------------------
#  CHART 2 — Line Chart: total books published per decade
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
st.plotly_chart(fig2, use_container_width=True)

st.divider()


# ----------------------------------------------------------
#  CHART 3 — Line Chart: per-subject trend over decades
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
        st.info("No author data available. Re-run the pipeline to load authors.")
except Exception as e:
    st.info(f"Author data not available. (Error: {e})")

st.divider()


# ============================================================
#  STRETCH GOAL 1 — Word Cloud of Most Common Subjects
# ============================================================

st.subheader("☁️ Word Cloud — Most Common Subjects")

if not filtered_raw.empty:
    subject_counts = (
        filtered_raw["searched_subject"]
        .value_counts()
        .to_dict()
    )

    if subject_counts:
        wc = WordCloud(
            width=1200,
            height=400,
            background_color="white",
            colormap="Blues",        
            max_font_size=120,       
            min_font_size=20         
        ).generate_from_frequencies(subject_counts)

        fig_wc, ax = plt.subplots(figsize=(14, 5))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")   
        st.pyplot(fig_wc)
    else:
        st.info("No data available for word cloud.")
else:
    st.info("No data available for word cloud.")

st.divider()


# ============================================================
#  STRETCH GOAL 2 — Side by Side Subject Comparison
# ============================================================

st.subheader("🔄 Compare Two Subjects Side by Side")

all_subjects_list = sorted(df["subject"].unique().tolist())

comp_col1, comp_col2 = st.columns(2)

with comp_col1:
    subject_a = st.selectbox(
        "Subject A",
        options=all_subjects_list,
        index=0   
    )

with comp_col2:
    subject_b = st.selectbox(
        "Subject B",
        options=all_subjects_list,
        index=min(1, len(all_subjects_list) - 1)   
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
        st.metric(label=f"Total Books — {subject_a.title()}", value=f"{kpi_a:,}")
    with kpi2:
        st.metric(label=f"Total Books — {subject_b.title()}", value=f"{kpi_b:,}")

    fig_comp = px.line(
        comparison_df,
        x="decade",
        y="book_count",
        color="subject",
        markers=True,
        labels={
            "book_count": "Number of Books",
            "decade": "Decade",
            "subject": "Subject"
        },
        title=f"{subject_a.title()} vs {subject_b.title()} — Publishing Trend by Decade"
    )
    fig_comp.update_traces(line_width=3)
    st.plotly_chart(fig_comp, use_container_width=True)

    fig_bar_comp = px.bar(
        comparison_df,
        x="decade",
        y="book_count",
        color="subject",
        barmode="group",   
        labels={
            "book_count": "Number of Books",
            "decade": "Decade",
            "subject": "Subject"
        },
        title=f"{subject_a.title()} vs {subject_b.title()} — Books per Decade"
    )
    st.plotly_chart(fig_bar_comp, use_container_width=True)

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