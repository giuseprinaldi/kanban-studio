# Stage 1: Build the frontend Next.js application
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Create the Python backend and serve static assets
FROM python:3.11-slim
WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependencies first for caching
COPY backend/requirements.txt ./backend/
RUN uv pip install --system --no-cache -r backend/requirements.txt

# Copy backend codebase
COPY backend/ ./backend/

# Copy frontend compiled static export to backend/static
COPY --from=frontend-builder /app/frontend/out/ ./backend/static/

# Expose FastAPI port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Start the FastAPI server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
