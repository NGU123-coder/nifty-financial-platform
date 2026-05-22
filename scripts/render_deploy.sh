#!/usr/bin/env bash
# Simplified Render Deployment Script
set -e

echo "--- STARTING DEPLOYMENT ---"

cd web_api

# Run standard migrations only
echo "Step 1: Running migrations..."
python manage.py migrate --noinput

# Perform final check
echo "Step 2: Performing final check..."
python manage.py check

echo "--- DEPLOYMENT SUCCESSFUL ---"
