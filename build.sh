#!/usr/bin/env bash
# Render build script

set -o errexit

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Running database migrations..."
python -c "from app.database import init_db; init_db()"

echo "Build completed successfully!"