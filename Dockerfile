# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies in a single layer to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/uploads /app/assets /app/videos /app/documents

# Expose port (Railway will set $PORT dynamically)
EXPOSE $PORT

# Run the application with gunicorn (production server)
CMD gunicorn web_app:web_app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --preload
