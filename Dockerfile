# Use Python 3.9 slim image as base with specific platform
FROM --platform=linux/amd64 python:3.12.8-slim

# Set working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
COPY .env /app/.env

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY ./backend /app/backend
# COPY ./frontend /app/frontend
COPY ./features /app/features
COPY ./services /app/services

# Expose port
EXPOSE 8080

# Run FastAPI application
# CMD ["bash", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 & python backend/redis/worker.py"]
CMD ["bash", "-c", "python backend/redis/worker.py & uvicorn backend.app.main:app --host 0.0.0.0 --port 8080"]
