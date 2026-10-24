# Dockerfile for BuergerAI (Combined development)

# Use this for local development with both backend and frontend
# For production, use separate Dockerfiles for backend and frontend

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -e ".[dev]" && \
    pip install fastapi uvicorn

# Copy source code
COPY src/ ./src/
COPY data/ ./data/

# Set PYTHONPATH
ENV PYTHONPATH=/app/src

# Install frontend dependencies
WORKDIR /app/frontend
COPY frontend/package.json ./package.json
COPY frontend/package-lock.json ./package-lock.json 2>/dev/null || true
RUN npm ci --only=production

# Copy frontend files
COPY frontend/ ./

# Build frontend
RUN npm run build

# Back to app directory
WORKDIR /app

# Expose ports
EXPOSE 8000 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the backend (frontend will be served by Next.js in production)
CMD ["uvicorn", "buergerai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
