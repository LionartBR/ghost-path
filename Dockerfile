# Stage 1: Build React frontend
FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/
RUN cd frontend && npm install
COPY frontend/ frontend/
RUN cd frontend && npm run build

# Stage 2: Python backend + static files
FROM python:3.13-slim
WORKDIR /app

# Install system deps for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy backend source and install (app goes to site-packages)
COPY backend/ backend-src/
RUN pip install --no-cache-dir ./backend-src

# Alembic needs its dir + ini in working dir; app is in site-packages
RUN cp -r backend-src/alembic alembic/ && \
    cp backend-src/alembic.ini . && \
    rm -rf backend-src

# Copy frontend build as static files
COPY --from=frontend-build /build/frontend/dist static/

EXPOSE 8000

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
