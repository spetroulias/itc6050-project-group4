# ITC6050 — Project 4: Open Library Book Trends
**Group 4 | MS in Data Science | Spring 2026**

## What This Project Does
Ingests book metadata from the Open Library API, stores it in PostgreSQL,
transforms it with dbt, and displays publishing trends on a Streamlit dashboard.

---

## Prerequisites
- Docker Desktop installed and running
- Git

---

## Setup (First Time Only)

**1. Clone the repository**
```bash
git clone https://github.com/your-username/itc6050-project-group4.git
cd itc6050-project-group4
```

**2. Create your `.env` file**
```bash
cp .env.example .env
# Open .env and fill in your values if you want to change the defaults
```

**3. Build the Docker containers**
```bash
docker-compose build
```

---

## Running the Project (In Order)

**Step 1 — Start PostgreSQL and pgAdmin**
```bash
docker-compose up -d postgres pgadmin
```
Wait about 10 seconds for PostgreSQL to be ready.

**Step 2 — Run the pipeline (fetch data and load to PostgreSQL)**
```bash
docker-compose run app python pipeline.py
```
This takes a few minutes — it fetches books and authors from the Open Library API.

**Step 3 — Run dbt transformations**
```bash
docker-compose run app dbt run --project-dir analytics --profiles-dir analytics
```

**Step 4 — Run dbt tests**
```bash
docker-compose run app dbt test --project-dir analytics --profiles-dir analytics
```
All tests should show ✅ PASS.

**Step 5 — Open the dashboard**
```bash
docker-compose up streamlit
```
Then open your browser at: **http://localhost:8501**

**Optional — Open pgAdmin to browse the database**
Open: **http://localhost:8080**
Login: see PGADMIN_EMAIL and PGADMIN_PASSWORD in your `.env` file
Connect to server: host=`postgres`, port=`5432`

---

## Project Structure
```
itc6050-project-group4/
├── pipeline.py              ← dlt ingestion script
├── dashboard.py             ← Streamlit dashboard
├── requirements.txt         ← Python dependencies
├── Dockerfile               ← Python container definition
├── docker-compose.yml       ← All services (postgres, pgadmin, app, streamlit)
├── .env                     ← Your credentials (never committed to GitHub)
├── .env.example             ← Template for .env
├── .gitignore
└── analytics/               ← dbt project
    ├── dbt_project.yml
    ├── profiles.yml
    └── models/
        ├── sources.yml
        ├── schema.yml
        ├── stg_books.sql              ← staging model
        └── subject_decade_summary.sql ← mart model
```

---

## Tech Stack
| Layer | Tool |
|---|---|
| Ingestion | dlt + Open Library API |
| Storage | PostgreSQL (Docker) |
| Transformation | dbt |
| Quality | dbt tests |
| Dashboard | Streamlit + Plotly |
| Version Control | Git + GitHub |
