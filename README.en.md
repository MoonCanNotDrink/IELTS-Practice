# IELTS Practice

English • [中文](README.md)

Status: Beta

An end-to-end IELTS practice project for speaking and writing, pairing a FastAPI backend with a lightweight frontend. AI components provide scoring, transcription, and a voice examiner experience suitable for a portfolio demo.

Why this repo matters (first 20 lines): showcases a full-stack AI integration that recreates a realistic IELTS practice flow, with automated feedback and voice interaction, useful as a technical and product example.

## What it does

- Implements the full IELTS Speaking flow (Part 1 / Part 2 / Part 3) and Writing practice (Task 1 / Task 2)
- Provides multi-dimensional scoring and actionable feedback by combining transcription and audio analysis with LLM outputs
- Integrates TTS and transcription for a voice examiner experience and dynamic follow-up questions
- Tracks user history and progress, with JWT-based multi-user isolation for realistic usage scenarios

## Tech stack (short)

- Frontend: vanilla HTML, JavaScript, CSS
- Backend: FastAPI, Python
- AI / Speech: Gemini (scoring/feedback), Azure Speech (TTS/transcription), faster-whisper (local transcription), librosa (audio analysis)
- Infrastructure: SQLite / PostgreSQL, Docker, Cloud Run (examples)

## Quick start

See docs/dev-guide.md for full setup and deployment instructions.

Minimal three-step path for development:

```bash
corepack pnpm install        # install frontend and test deps
# configure environment variables as described in docs/dev-guide.md
corepack pnpm test           # run automated tests
# follow docs/dev-guide.md to start backend and frontend services
```

## Project layout (top-level)

- frontend/ — static pages and browser interaction
- backend/ — FastAPI application and business logic
- tests/ — automated tests (Playwright and unit)
- docs/ — developer and public documentation (see docs/dev-guide.md)

## Links

- Dev guide (run, configure, deploy): docs/dev-guide.md
- Documentation index: docs/README.md
- Collaboration rules: AGENTS.md

---

Note: this README is trimmed to serve as the public project landing page. Full developer and deployment details live in docs/dev-guide.md.
