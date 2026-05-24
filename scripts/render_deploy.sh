#!/usr/bin/env bash
# Simplified Render Deployment Script
set -e

echo "--- STARTING DEPLOYMENT ---"

cd web_api

# Run standard migrations
echo "Step 1: Running migrations..."
python manage.py migrate --noinput

# Setup Warehouse Tables
echo "Step 2: Setting up warehouse tables..."
python manage.py setup_warehouse

# Bootstrap Demo Data
echo "Step 3: Bootstrapping demo data..."
python manage.py bootstrap_demo_data

# Perform final check
echo "Step 4: Performing final check..."
python manage.py check

echo "--- DEPLOYMENT SUCCESSFUL ---"
