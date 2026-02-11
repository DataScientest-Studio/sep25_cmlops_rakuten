FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-api.txt /app/requirements-api.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-api.txt

# Download NLTK data (for text preprocessing)
RUN python -m nltk.downloader punkt stopwords -d /usr/local/share/nltk_data

# Copy source code
COPY src/ /app/src/
COPY src/serve/ /app/

# Create monitoring directory
RUN mkdir -p /app/data/monitoring

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
