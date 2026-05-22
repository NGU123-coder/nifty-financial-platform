#!/usr/bin/env bash
# Render Deployment Script
set -e # Exit on error

echo "--- Starting Deployment Steps ---"

# 1. Navigate to the project root (should be here)
echo "Working directory: $(pwd)"

# 2. Run Schema Initialization
echo "Step 1: Initializing warehouse schema..."
cd web_api
python manage.py init_schema

# 3. Run Django Migrations
echo "Step 2: Running Django migrations..."
python manage.py migrate

# 4. Bootstrap Data
echo "Step 3: Seeding production demo data..."
python manage.py bootstrap_data

echo "--- Deployment Steps Completed Successfully ---"
