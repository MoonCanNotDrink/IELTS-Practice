# Configuration reference

This document lists all environment variables used by the backend application, their defaults, whether they are required in production, and a short description.

Notes
- The application reads configuration from `backend/.env` (see `backend/.env.example`) and environment variables.
- Do not change variable names without updating `backend/app/config.py`.

Application Settings

| Name | Default | Required (prod) | Description |
|---|---|---:|---|
| APP_NAME | "IELTS Speaking Practice" | optional | Human friendly app name used in logs and emails |
| APP_BASE_URL | "http://localhost:8000" | yes | Public base URL of the app, used to build links in emails and redirects |
| DEBUG | false | no | Enable debug mode (development only). Accepts true/false or common truthy strings |
| DB_PATH | "data/ielts.db" | no | Local SQLite path (used when DATABASE_URL is empty) |
| RECORDINGS_DIR | "data/recordings" | no | Local path where uploaded recordings are stored |
| DATABASE_URL | "" | yes (production) | Full SQLAlchemy-compatible URL for the production database (Postgres). If empty, the app falls back to a local SQLite file (DB_PATH). |

Whisper (Local ASR Fallback)

| Name | Default | Required (prod) | Description |
|---|---|---:|---|
| WHISPER_MODEL_PATH | "whisper_base_model" | no | Filesystem path or identifier for the local faster-whisper model |
| WHISPER_MODEL_SIZE | "base" | no | Model size label (tiny, base, small, medium, large) |
| WHISPER_DEVICE | "cpu" | no | Device for inference (cpu, cuda, mps, etc.) |
| WHISPER_COMPUTE_TYPE | "int8" | no | Compute type hint for performance (int8, fp16, fp32) |

Google Gemini (LLM Scoring)

| Name | Default | Required (prod) | Description |
|---|---|---:|---|
| GEMINI_API_KEY | "" | recommended | API key for Google Gemini. Required for AI scoring and feedback when using Gemini |
| GEMINI_MODEL | "gemini-2.5-flash" | no | Model name used for scoring |
| GEMINI_TIMEOUT_SECONDS | 25 | no | Timeout (seconds) for requests to Gemini |

Azure Speech (Pronunciation)

| Name | Default | Required (prod) | Description |
|---|---|---:|---|
| AZURE_SPEECH_KEY | "" | recommended | Azure Speech API key used for pronunciation assessment and TTS |
| AZURE_SPEECH_REGION | "eastasia" | no | Azure region for the speech resource |
| PRONUNCIATION_TIMEOUT_SECONDS | 15 | no | Request timeout (seconds) for pronunciation assessment |

Recording

| Name | Default | Required (prod) | Description |
|---|---|---:|---|
| MAX_RECORDING_SECONDS | 150 | no | Maximum accepted recording length in seconds |
| ALLOWED_AUDIO_FORMATS | ["webm","wav","mp3","ogg"] | no | Comma-separated or JSON-style list of allowed audio file extensions |

Authentication (JWT)

| Name | Default | Required (prod) | Description |
|---|---|---:|---|
| JWT_SECRET | "" | required | Secret used to sign JWTs. MUST be set in production. The app warns if empty. |
| JWT_ALGORITHM | "HS256" | no | Signing algorithm for JWT tokens |
| ACCESS_TOKEN_EXPIRE_MINUTES | 30 | no | Access token lifetime in minutes |
| REFRESH_TOKEN_EXPIRE_DAYS | 30 | no | Refresh token lifetime in days |
| INVITE_CODE | "" | required | Invite code used to gate account creation in production |
| PASSWORD_RESET_EXPIRE_MINUTES | 15 | no | Expiration for password reset tokens |

Email (SMTP)

| Name | Default | Required (prod) | Description |
|---|---|---:|---|
| EMAIL_FROM | "no-reply@example.com" | recommended | From address used for transactional emails |
| SMTP_HOST | "" | required if email enabled | SMTP server hostname |
| SMTP_PORT | 587 | no | SMTP port (typically 587 for STARTTLS) |
| SMTP_USERNAME | "" | required if SMTP auth | SMTP username |
| SMTP_PASSWORD | "" | required if SMTP auth | SMTP password |
| SMTP_USE_TLS | true | no | Use TLS/STARTTLS when connecting to SMTP server |

CORS

| Name | Default | Required (prod) | Description |
|---|---|---:|---|
| CORS_ORIGINS | [] | no | JSON-style list of allowed origins. Example: ["http://localhost:8000","https://example.com"]

Deployment (Cloud Run and packaging helpers)

These variables are not required by the Python app directly but are used by deployment scripts and build tooling.

| Name | Default | Required (prod) | Description |
|---|---|---:|---|
| PROJECT_ID | "" | required for Cloud Run deploy scripts | GCP project id used by deploy scripts |
| REGION | "" | required for Cloud Run deploy scripts | GCP region to deploy to |
| SERVICE_NAME | "" | required for Cloud Run deploy scripts | Cloud Run service name |
| PORT | 8000 | no | Port the app listens on in container/runtime |
| PIP_INDEX_URL | "" | no | Custom pip index URL for private packages during build |
| PIP_TRUSTED_HOST | "" | no | Trusted host for pip when using custom index |

Cloud Run Secrets mapping

The deploy script maps Cloud Run secrets to environment variables. Mappings in this project:

- GEMINI_API_KEY -> ielts-speaking-gemini-api-key
- AZURE_SPEECH_KEY -> ielts-speaking-azure-speech-key
- JWT_SECRET -> ielts-speaking-jwt-secret
- INVITE_CODE -> ielts-speaking-invite-code
- DATABASE_URL -> ielts-speaking-database-url

Production-required summary

The minimal set of variables you should set for a production deployment depends on which features you enable. The absolute minimum recommended for a locked-down production service:

- JWT_SECRET (required) — sign tokens
- INVITE_CODE (required) — prevent open signups
- DATABASE_URL (required) — use a managed Postgres or other production DB; required if you need multi-instance persistence
- APP_BASE_URL (recommended) — correct public URL for email links and redirects

Recommended for feature completeness in production:

- GEMINI_API_KEY — enable AI scoring and richer feedback
- AZURE_SPEECH_KEY — enable pronunciation assessment and TTS
- SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD/EMAIL_FROM — enable password reset and transactional email

If you intentionally run a single-node, local-only deployment you may keep DATABASE_URL empty and rely on DB_PATH, but that is not recommended for production.
