# =============================================================
# TerraSpectra - Render Production Multi-Stage Dockerfile
# =============================================================

# -------------------------------------------------------------
# Stage 1: Build React 18 + Deck.gl 9 Frontend
# -------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# -------------------------------------------------------------
# Stage 2: Python 3.11 FastAPI Inference Engine
# -------------------------------------------------------------
FROM python:3.11-slim
WORKDIR /app

# System dependencies for GDAL & geospatial algorithms
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    gdal-bin \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU + Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code, configs, artifacts
COPY configs/ ./configs/
COPY ml/ ./ml/
COPY api/ ./api/
COPY scripts/ ./scripts/
COPY artifacts/ ./artifacts/

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /web/dist ./web/dist

# Ensure writable data directory exists
RUN mkdir -p data/raw data/results

# Dynamic port handling for Render ($PORT)
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
