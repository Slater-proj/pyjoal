# Multi-stage Dockerfile for PyJOAL
# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build


# Stage 2: Python Runtime
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app ./app

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy client update script
COPY update_clients.py ./

# Create necessary directories first
RUN mkdir -p /app/config /app/torrents /app/clients

# Copy default client files (fallback if GitHub is unreachable)
COPY clients/ ./clients/

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DOCKER_CONTAINER=1

# Expose port
EXPOSE 8080

# Copy entrypoint script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Use entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]
