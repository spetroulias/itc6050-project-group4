# Use official Python 3.11 slim image (lightweight)
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies needed for psycopg2 (PostgreSQL driver)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker caches this layer — speeds up rebuilds)
COPY requirements.txt .

# Install all Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project files into the container
COPY . .

# Tell dbt where to find your profiles.yml
ENV DBT_PROFILES_DIR=/app/analytics
