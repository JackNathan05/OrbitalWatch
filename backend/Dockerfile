FROM python:3.13-slim

WORKDIR /app

# Install system deps needed by psycopg2-binary and others
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Remove local-only files
RUN rm -rf venv celerybeat-schedule* __pycache__ .env

# Railway injects PORT at runtime; use shell form so env var is expanded
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
