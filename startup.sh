#!/bin/bash

# Startup script for Railway deployment with error checking

echo "========================================="
echo "AIezzy Starting..."
echo "========================================="

# Check critical environment variables
echo "Checking environment variables..."

if [ -z "$SECRET_KEY" ]; then
    echo "ERROR: SECRET_KEY not set!"
    echo "Please set in Railway Variables tab"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY not set!"
    echo "Please set in Railway Variables tab"
    exit 1
fi

if [ -z "$FAL_KEY" ]; then
    echo "ERROR: FAL_KEY not set!"
    echo "Please set in Railway Variables tab"
    exit 1
fi

if [ -z "$TAVILY_API_KEY" ]; then
    echo "ERROR: TAVILY_API_KEY not set!"
    echo "Please set in Railway Variables tab"
    exit 1
fi

# Set defaults for optional variables
export BASE_URL=${BASE_URL:-https://aiezzy.com}
export FLASK_ENV=${FLASK_ENV:-production}
export PORT=${PORT:-8080}

echo "✓ All required environment variables set"
echo "✓ PORT: $PORT"
echo "✓ BASE_URL: $BASE_URL"
echo "✓ FLASK_ENV: $FLASK_ENV"

# Check if DATABASE_URL is set (PostgreSQL)
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL not set. Using SQLite."
    echo "Add PostgreSQL database in Railway for production!"
else
    echo "✓ DATABASE_URL configured (PostgreSQL)"
fi

echo "========================================="
echo "Starting Gunicorn..."
echo "========================================="

# Start gunicorn
exec gunicorn web_app:web_app \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info
