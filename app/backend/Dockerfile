FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# DuckDB might need some, but usually wheels are self-contained.
# curl is useful for healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY app/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
# We copy the entire app directory structure to maintain imports
COPY app/backend /app/app/backend

# Set python path to include root
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
