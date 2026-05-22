#!/usr/bin/env bash
# Render Deployment Script - Robust Version
set -e

echo "--- STARTING DEPLOYMENT ---"

# Navigate to app directory
cd web_api

# 1. Run Standard Django Migrations
echo "Step 1: Running migrations..."
python manage.py migrate --noinput

# 2. Setup Warehouse Tables (Unmanaged Models)
echo "Step 2: Setting up reliable warehouse tables..."
python manage.py setup_warehouse

# 3. Bootstrap Demo Data
echo "Step 3: Seeding production demo data..."
python manage.py bootstrap_demo_data

# 4. Final System Check
echo "Step 4: Performing final check..."
python manage.py check

echo "--- DEPLOYMENT SUCCESSFUL ---"
