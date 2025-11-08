FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create directories for uploads, outputs, and database
RUN mkdir -p /tmp/uploads /tmp/outputs /app/data

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.main
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

# Run the application with Gunicorn (production WSGI server)
# --max-requests: Restart worker after N requests to prevent memory leaks
# --max-requests-jitter: Add randomness to prevent all workers restarting at once
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "7200", "--worker-class", "gthread", "--max-requests", "50", "--max-requests-jitter", "10", "app.main:app"]
