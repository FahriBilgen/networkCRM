FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY fortress_director/ ./fortress_director/
COPY settings.py .
COPY pytest.ini .

# Create necessary directories
RUN mkdir -p data db logs cache tmp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
    --retries=3 CMD python -c \
    "import requests; requests.get('http://localhost:8000/health', timeout=5)"

# Run FastAPI server
CMD ["python", "-m", "uvicorn", "fortress_director.api:app", \
     "--host", "0.0.0.0", "--port", "8000"]
