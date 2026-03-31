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

Then fill in required values in `backend/.env` (see `backend/.env.example`).

3) Start the app with auto-reload:

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

## Running Tests

From the repository root:

- Backend route tests:

```bash
cd backend
python -m unittest discover -p 'test*_route*.py' -v
```

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

## Alternative Paths

These are supported but not primary:

- `docker-compose up`: alternative for local containerized setup.
- `docker build -t ielts-practice . && docker run ...`: alternative/manual container path using the root `Dockerfile`.

## Environment Variables

Use `backend/.env.example` as the source of truth for required environment variables.
