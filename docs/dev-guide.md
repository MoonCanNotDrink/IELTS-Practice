# Developer Guide

This project has one canonical local development path and one canonical deployment path.

## Prerequisites

- Python 3.12
- Node.js 20
- pnpm (via Corepack)

Install JavaScript dependencies from the repository root:

```bash
corepack pnpm install
```

## Local Development (Canonical)

Use direct `uvicorn` with auto-reload.

1) Install backend Python dependencies:

```bash
cd backend
pip install -r requirements.txt
```

2) Create your local environment file from the template:

```bash
cp .env.example .env
```

Then fill in required values in `backend/.env`. See docs/configuration.md for a complete env var reference and `backend/.env.example` for a minimal template.

3) Start the app with auto-reload:

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

## Database Migrations

Use Alembic from the `backend/` directory.

- Create a new migration:

```bash
cd backend && alembic revision --autogenerate -m "description"
```

- Apply migrations locally:

```bash
cd backend && alembic upgrade head
```

- Check current migration state:

```bash
cd backend && alembic current
```

- Roll back one revision:

```bash
cd backend && alembic downgrade -1
```

Production behavior: migrations run automatically on container startup via the Dockerfile `CMD` (`alembic upgrade head` runs before `uvicorn`).

Note: for local SQLite development, `init_db()` in `app/database.py` creates tables from SQLAlchemy models. Alembic is primarily needed for production PostgreSQL schema changes.

## Running Tests

From the repository root:

- Backend route tests:

```bash
cd backend
python -m unittest discover -p 'test*_route*.py' -v
```

- Backend smoke test (real app + isolated test DB):

```bash
corepack pnpm test:backend:smoke
```

This test boots the real FastAPI app via uvicorn, waits for `/api/health`, then exercises core speaking flow endpoints (register/login, create session, upload audio, score, history/detail). It uses a temporary SQLite DB and recordings directory so local/dev data is not modified.

- Frontend unit tests:

```bash
corepack pnpm test:unit
```

- End-to-end tests:

```bash
corepack pnpm test
```

- Lint:

```bash
corepack pnpm lint
```

## Deployment (Canonical)

Use the Cloud Run deployment script:

```bash
bash scripts/deploy-cloud-run.sh
```

This is the primary deploy path (Cloud Build -> Cloud Run).

If `gcloud run deploy` is flaky in your local environment, the script also supports:

```bash
DEPLOY_STRATEGY=api bash scripts/deploy-cloud-run.sh
```

To reuse the latest pushed image without rebuilding:

```bash
SKIP_BUILD=true DEPLOY_STRATEGY=api bash scripts/deploy-cloud-run.sh
```

## Alternative Paths

These are supported but not primary:

- `docker-compose up`: alternative for local containerized setup.
- `docker build -t ielts-practice . && docker run ...`: alternative/manual container path using the root `Dockerfile`.

## Environment Variables

Use `backend/.env.example` as the source of truth for required environment variables.
