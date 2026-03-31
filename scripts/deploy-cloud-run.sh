#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-ethereal-app-482708-i9}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-ielts-speaking}"
REPOSITORY="${REPOSITORY:-cloud-run-source-deploy}"
IMAGE="${IMAGE:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}}"
CLOUDSQL_INSTANCE="${CLOUDSQL_INSTANCE:-${PROJECT_ID}:${REGION}:ielts-db}"
PROJECT_NUMBER="${PROJECT_NUMBER:-}"
APP_BASE_URL="${APP_BASE_URL:-}"
ENV_VARS="${ENV_VARS:-GEMINI_MODEL=gemini-3-flash-preview,AZURE_SPEECH_REGION=japanwest,DEBUG=false,APP_BASE_URL=${APP_BASE_URL}}"
SECRET_VARS="${SECRET_VARS:-GEMINI_API_KEY=ielts-speaking-gemini-api-key:latest,AZURE_SPEECH_KEY=ielts-speaking-azure-speech-key:latest,JWT_SECRET=ielts-speaking-jwt-secret:latest,INVITE_CODE=ielts-speaking-invite-code:latest,DATABASE_URL=ielts-speaking-database-url:latest}"
USE_MIRROR=""

while (($# > 0)); do
  case "$1" in
    --use-mirror=*)
      USE_MIRROR="${1#*=}"
      ;;
    --use-mirror)
      shift
      USE_MIRROR="${1:-}"
      ;;
    --help|-h)
      cat <<'EOF'
Usage:
  bash scripts/deploy-cloud-run.sh
  bash scripts/deploy-cloud-run.sh --use-mirror=tsinghua

Optional env vars:
  PROJECT_ID
  REGION
  SERVICE_NAME
  REPOSITORY
  IMAGE
  CLOUDSQL_INSTANCE
  PROJECT_NUMBER
  APP_BASE_URL
  ENV_VARS
  SECRET_VARS
  PIP_INDEX_URL
  PIP_TRUSTED_HOST

Default behavior uses the official PyPI index.
Pass --use-mirror=tsinghua to use the Tsinghua PyPI mirror for the Cloud Build Docker step.
EOF
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      exit 1
      ;;
  esac
  shift
done

if [[ -n "${PIP_INDEX_URL:-}" ]]; then
  BUILD_PIP_INDEX_URL="$PIP_INDEX_URL"
  BUILD_PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST:-$(python3 - <<'PY'
from urllib.parse import urlparse
import os
print(urlparse(os.environ['PIP_INDEX_URL']).hostname or '')
PY
)}"
elif [[ "$USE_MIRROR" == "tsinghua" ]]; then
  BUILD_PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
  BUILD_PIP_TRUSTED_HOST="pypi.tuna.tsinghua.edu.cn"
else
  BUILD_PIP_INDEX_URL="https://pypi.org/simple"
  BUILD_PIP_TRUSTED_HOST="pypi.org"
fi

if [[ -z "$APP_BASE_URL" ]]; then
  EXISTING_SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --format='value(status.url)' 2>/dev/null || true)"
  if [[ -n "$EXISTING_SERVICE_URL" ]]; then
    APP_BASE_URL="$EXISTING_SERVICE_URL"
  else
    if [[ -z "$PROJECT_NUMBER" ]]; then
      PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
    fi
    APP_BASE_URL="https://${SERVICE_NAME}-${PROJECT_NUMBER}.${REGION}.run.app"
  fi
fi

if [[ "$ENV_VARS" == *"APP_BASE_URL="* ]]; then
  ENV_VARS="$(printf '%s' "$ENV_VARS" | sed -E "s#APP_BASE_URL=[^,]*#APP_BASE_URL=${APP_BASE_URL}#")"
else
  ENV_VARS="${ENV_VARS},APP_BASE_URL=${APP_BASE_URL}"
fi

gcloud builds submit \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --config=cloudbuild.yaml \
  --substitutions="_IMAGE=${IMAGE},_PIP_INDEX_URL=${BUILD_PIP_INDEX_URL},_PIP_TRUSTED_HOST=${BUILD_PIP_TRUSTED_HOST}" \
  .

gcloud run deploy "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --image="$IMAGE" \
  --port=8080 \
  --cpu=2 \
  --memory=2Gi \
  --min-instances=0 \
  --max-instances=20 \
  --concurrency=80 \
  --timeout=300 \
  --cpu-boost \
  --allow-unauthenticated \
  --add-cloudsql-instances="$CLOUDSQL_INSTANCE" \
  --update-env-vars="$ENV_VARS" \
  --update-secrets="$SECRET_VARS" \
  --quiet

echo ""
echo "Running post-deploy smoke checks..."
SMOKE_MAX_RETRIES=15
SMOKE_RETRY_INTERVAL=4

smoke_check() {
  local url="$1"
  local label="$2"

  for i in $(seq 1 "$SMOKE_MAX_RETRIES"); do
    HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")"
    if [[ "$HTTP_CODE" == "200" ]]; then
      printf '  [OK] %s (%s) - HTTP %s\n' "$label" "$url" "$HTTP_CODE"
      return 0
    fi

    if [[ "$i" -eq "$SMOKE_MAX_RETRIES" ]]; then
      printf '  [FAIL] %s (%s) - HTTP %s after %s attempts\n' "$label" "$url" "$HTTP_CODE" "$SMOKE_MAX_RETRIES" >&2
      return 1
    fi

    printf '  ... %s - attempt %s/%s (HTTP %s), retrying in %ss\n' "$label" "$i" "$SMOKE_MAX_RETRIES" "$HTTP_CODE" "$SMOKE_RETRY_INTERVAL"
    sleep "$SMOKE_RETRY_INTERVAL"
  done
}

SMOKE_FAILED=0
smoke_check "${APP_BASE_URL}/api/health" "Health endpoint" || SMOKE_FAILED=1
smoke_check "${APP_BASE_URL}/" "Homepage" || SMOKE_FAILED=1

if [[ "$SMOKE_FAILED" -ne 0 ]]; then
  echo ""
  echo "ERROR: One or more smoke checks failed. The service may not be healthy." >&2
  echo "Check Cloud Run logs: gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50" >&2
  exit 1
fi

echo ""
echo "All smoke checks passed. Deployment complete."
