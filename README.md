# TRIZ — Knowledge Creation Engine

Knowledge creation engine powered by Claude Opus 4.6. It decomposes problems, explores solutions via dialectical method (thesis -> antithesis -> synthesis), validates claims with web evidence, and crystallizes findings into a final document.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose (included in Docker Desktop)
- An [Anthropic API key](https://console.anthropic.com/settings/keys)

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd ghost-path
```

### 2. Configure the API key

Copy the example file and add your key:

```bash
cp .env.example .env
```

Edit `.env` and replace the `ANTHROPIC_API_KEY` value:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

> The `.env` file goes in the **project root** (same directory as `docker-compose.yml`). Other variables can stay with their defaults.

### 3. Start the app

```bash
docker compose up --build
```

Wait until you see in the logs:

```
backend-1   | Starting uvicorn...
backend-1   | INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4. Open the app

Open your browser at **http://localhost**

The API is at **http://localhost:8000** (health check: `http://localhost:8000/api/v1/health/`).

## Ports

| Service  | Port | Description                  |
|----------|------|------------------------------|
| Frontend | 80   | React UI (nginx)             |
| Backend  | 8000 | FastAPI API (uvicorn)        |
| Postgres | 5432 | Database (internal)          |

> If port 80 is taken, change it in `docker-compose.yml`: `"3000:80"` and access at `http://localhost:3000`.

## Stopping the app

```bash
# Stop (keeps database data)
docker compose down

# Stop and delete database data
docker compose down -v
```

## Environment variables

All configured in `.env` at the project root:

| Variable             | Required | Description                                            | Default |
|----------------------|----------|--------------------------------------------------------|---------|
| `ANTHROPIC_API_KEY`  | Yes      | Anthropic API key                                      | —       |
| `LOG_LEVEL`          | No       | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)        | `INFO`  |
| `LOG_FORMAT`         | No       | Log format (`json` or `text`)                          | `json`  |

> `DATABASE_URL` and `CORS_ORIGINS` are set automatically by Docker Compose — no need to change them.

## Troubleshooting

**Port 80 in use**: Change the mapping in `docker-compose.yml` from `"80:80"` to `"3000:80"`.

**Database connection error**: The backend waits for Postgres to be ready (up to 60s). If it persists, check if port 5432 is occupied by another local Postgres.

**Invalid API key**: Make sure you copied the full key in `.env` (starts with `sk-ant-`).

**Rebuild after changes**: `docker compose up --build` rebuilds the images.
