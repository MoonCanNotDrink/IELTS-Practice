# Project rules

## Setup
- Install dependencies: corepack pnpm install
- Run dev server: see backend/ and frontend/ for local start instructions (no single pnpm dev)
- Run tests: corepack pnpm test
- Run lint: corepack pnpm lint

## Conventions
- Keep changes minimal
- Do not rename public APIs unless explicitly requested
- Add or update tests for behavior changes
- Prefer fixing root causes over superficial patches

## Important paths
- backend/app: backend logic (FastAPI)
- frontend/: frontend pages, JS and CSS
- tests/: automated tests (Playwright / unit tests)

## Safety
- Ask before changing CI, release config, or database migrations
