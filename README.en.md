# IELTS Speaking AI

An IELTS speaking practice platform covering full exam flows, free practice, dynamic follow-up questions, voice examiner playback, transcription, scoring feedback, and history review.

Its goal is not just to demonstrate isolated AI features, but to connect the key stages before, during, and after practice into a usable learning system.

> Status: Beta
> Last Updated: 2026-03-20

## Navigation

- [中文版 README](README.md)
- [文档目录（中文）](docs/README.md)
- [Documentation Index](docs/README.en.md)
- [Project Overview (Chinese)](docs/项目简介.md)
- [Project Overview (English)](docs/项目简介.en.md)
- [对外文档（中文）](documentation/README.md)
- [External Documentation](documentation/README.en.md)

## Start Here

| I want to... | Go to |
|---|---|
| understand the project quickly | [Project Overview](docs/项目简介.en.md) |
| read the public-facing docs | [External Documentation](documentation/README.en.md) |
| begin with the user guides | [Getting Started](documentation/user-guide/getting-started.en.md) |
| inspect plans and reports | [Documentation Index](docs/README.en.md) |

## Core Features

- Full IELTS Speaking flow: Part 1 / Part 2 / Part 3
- Free Practice mode with topic library, custom prompts, and custom speaking duration
- Dynamic follow-up questions powered by an LLM
- Voice examiner playback with TTS
- Multi-dimensional scoring based on transcription, audio analysis, and model output
- History and progress review for repeated practice
- Multi-user isolation with JWT-based authentication

## Quick Start

### Install dependencies

```bash
pnpm install
```

### Run tests

```bash
pnpm test
```

### Local development note

- The current root `package.json` exposes `pnpm test`.
- For broader local workflow details, see [AGENTS.md](AGENTS.md) and [docs/README.en.md](docs/README.en.md).

## Project Structure

- `frontend/`: frontend pages, interaction logic, and styles
- `backend/`: FastAPI backend, routes, services, and data models
- `tests/`: Playwright and related automated tests
- [`docs/plans/`](docs/plans/): implementation plans and solution notes
- [`docs/reports/`](docs/reports/): optimization reports, product summaries, and stage recaps
- [`AGENTS.md`](AGENTS.md): project development rules and collaboration constraints

## Documentation Entry Points

- [docs/README.en.md](docs/README.en.md): documentation index
- [docs/style-guide.en.md](docs/style-guide.en.md): documentation style guide
- [documentation/README.en.md](documentation/README.en.md): formal external-facing documentation entry
- [docs/plans/自由练习实现计划.en.md](docs/plans/自由练习实现计划.en.md): Free Practice implementation plan
- [docs/reports/自由练习界面优化报告.en.md](docs/reports/自由练习界面优化报告.en.md): Free Practice UI optimization summary
- [docs/reports/自由练习-产品设计摘要.en.md](docs/reports/自由练习-产品设计摘要.en.md): product/design summary for Free Practice
- [docs/reports/全阶段开发总结.en.md](docs/reports/全阶段开发总结.en.md): overall project development summary

## Tech Stack

- Frontend: vanilla HTML / JavaScript / CSS
- Backend: FastAPI / Python
- Database: SQLite / PostgreSQL
- Speech transcription: Azure Speech + faster-whisper
- Audio analysis: librosa
- LLM: Gemini
- Auth: JWT
- Deployment: Docker

## Notes

The root `README.md` serves as the primary Chinese entry document.

The `docs/` directory contains user-facing collaboration and delivery documents. Internal execution traces under `.sisyphus/` remain internal and are not part of the external documentation set.
