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
DEPLOY_STRATEGY="${DEPLOY_STRATEGY:-auto}"
SKIP_BUILD="${SKIP_BUILD:-false}"
PORT="${PORT:-8080}"
CPU="${CPU:-2}"
MEMORY="${MEMORY:-2Gi}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-20}"
CONCURRENCY="${CONCURRENCY:-80}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"
CPU_BOOST="${CPU_BOOST:-true}"
STARTUP_PROBE_TIMEOUT="${STARTUP_PROBE_TIMEOUT:-240}"
STARTUP_PROBE_PERIOD="${STARTUP_PROBE_PERIOD:-240}"
STARTUP_PROBE_FAILURE_THRESHOLD="${STARTUP_PROBE_FAILURE_THRESHOLD:-1}"
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
  DEPLOY_STRATEGY    auto|gcloud|api (default: auto)
  SKIP_BUILD         true to reuse the latest pushed image tag
  PORT
  CPU
  MEMORY
  MIN_INSTANCES
  MAX_INSTANCES
  CONCURRENCY
  TIMEOUT_SECONDS
  CPU_BOOST

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

resolve_image_with_digest() {
  local image_repo="$IMAGE"
  local image_tag="latest"
  local digest=""

  if [[ "$IMAGE" == *@sha256:* ]]; then
    printf '%s\n' "$IMAGE"
    return 0
  fi

  if [[ "${IMAGE##*/}" == *:* ]]; then
    image_repo="${IMAGE%:*}"
    image_tag="${IMAGE##*:}"
  fi

  digest="$(
    gcloud artifacts docker tags list "$image_repo" \
      --project="$PROJECT_ID" \
      --filter="tag~${image_tag}$" \
      --format='value(version)' \
      --limit=20 \
      | grep -Eo 'sha256:[0-9a-f]+' \
      | head -n1
  )"

  if [[ -z "$digest" ]]; then
    printf 'Unable to resolve image digest for %s (tag: %s)\n' "$image_repo" "$image_tag" >&2
    return 1
  fi

  printf '%s@%s\n' "$image_repo" "$digest"
}

deploy_with_gcloud() {
  local cpu_boost_flag="--cpu-boost"

  if [[ "$CPU_BOOST" != "true" ]]; then
    cpu_boost_flag="--no-cpu-boost"
  fi

  gcloud run deploy "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --image="$IMAGE" \
    --port="$PORT" \
    --cpu="$CPU" \
    --memory="$MEMORY" \
    --min-instances="$MIN_INSTANCES" \
    --max-instances="$MAX_INSTANCES" \
    --concurrency="$CONCURRENCY" \
    --timeout="$TIMEOUT_SECONDS" \
    "$cpu_boost_flag" \
    --allow-unauthenticated \
    --add-cloudsql-instances="$CLOUDSQL_INSTANCE" \
    --update-env-vars="$ENV_VARS" \
    --update-secrets="$SECRET_VARS" \
    --quiet
}

deploy_with_api() {
  local image_with_digest="$1"
  local access_token=""

  access_token="$(gcloud auth print-access-token)"

  ACCESS_TOKEN="$access_token" \
  IMAGE_WITH_DIGEST="$image_with_digest" \
  PROJECT_ID="$PROJECT_ID" \
  REGION="$REGION" \
  SERVICE_NAME="$SERVICE_NAME" \
  CLOUDSQL_INSTANCE="$CLOUDSQL_INSTANCE" \
  ENV_VARS="$ENV_VARS" \
  SECRET_VARS="$SECRET_VARS" \
  PORT="$PORT" \
  CPU="$CPU" \
  MEMORY="$MEMORY" \
  MIN_INSTANCES="$MIN_INSTANCES" \
  MAX_INSTANCES="$MAX_INSTANCES" \
  CONCURRENCY="$CONCURRENCY" \
  TIMEOUT_SECONDS="$TIMEOUT_SECONDS" \
  CPU_BOOST="$CPU_BOOST" \
  STARTUP_PROBE_TIMEOUT="$STARTUP_PROBE_TIMEOUT" \
  STARTUP_PROBE_PERIOD="$STARTUP_PROBE_PERIOD" \
  STARTUP_PROBE_FAILURE_THRESHOLD="$STARTUP_PROBE_FAILURE_THRESHOLD" \
  python3 - <<'PY'
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

MAX_HTTP_RETRIES = 5
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def parse_env_vars(raw: str) -> list[tuple[str, str]]:
    if not raw:
        return []

    items = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(f"Invalid ENV_VARS entry: {entry}")
        name, value = entry.split("=", 1)
        items.append((name, value))
    return items


def parse_secret_vars(raw: str) -> list[tuple[str, str, str]]:
    if not raw:
        return []

    items = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry or ":" not in entry:
            raise ValueError(f"Invalid SECRET_VARS entry: {entry}")
        name, secret_ref = entry.split("=", 1)
        secret_name, version = secret_ref.rsplit(":", 1)
        items.append((name, secret_name, version))
    return items


def request_json(url: str, *, headers: dict[str, str], method: str = "GET", payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    last_error = None

    for attempt in range(1, MAX_HTTP_RETRIES + 1):
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_STATUS_CODES or attempt == MAX_HTTP_RETRIES:
                raise
            last_error = exc
        except urllib.error.URLError as exc:
            if attempt == MAX_HTTP_RETRIES:
                raise
            last_error = exc

        time.sleep(attempt * 2)

    raise last_error  # pragma: no cover


project_id = os.environ["PROJECT_ID"]
region = os.environ["REGION"]
service_name = os.environ["SERVICE_NAME"]
cloudsql_instance = os.environ["CLOUDSQL_INSTANCE"]
service_url = f"https://run.googleapis.com/v2/projects/{project_id}/locations/{region}/services/{service_name}"
headers = {
    "Authorization": f"Bearer {os.environ['ACCESS_TOKEN']}",
    "Content-Type": "application/json",
}

try:
    service = request_json(service_url, headers=headers)
except urllib.error.HTTPError as exc:
    message = exc.read().decode("utf-8", errors="replace")
    if exc.code == 404:
        print("API fallback requires the Cloud Run service to already exist.", file=sys.stderr)
    else:
        print(message, file=sys.stderr)
    raise

template = service["template"]
container = template["containers"][0]

template["revision"] = f"{service_name}-manual-{int(time.time())}"
template["scaling"] = {
    "minInstanceCount": int(os.environ["MIN_INSTANCES"]),
    "maxInstanceCount": int(os.environ["MAX_INSTANCES"]),
}
template["timeout"] = f"{int(os.environ['TIMEOUT_SECONDS'])}s"
template["maxInstanceRequestConcurrency"] = int(os.environ["CONCURRENCY"])

container["image"] = os.environ["IMAGE_WITH_DIGEST"]
container["ports"] = [{"name": "http1", "containerPort": int(os.environ["PORT"])}]
container["resources"] = {
    "limits": {
        "cpu": os.environ["CPU"],
        "memory": os.environ["MEMORY"],
    },
    "cpuIdle": True,
    "startupCpuBoost": os.environ["CPU_BOOST"].lower() == "true",
}
container["startupProbe"] = {
    "timeoutSeconds": int(os.environ["STARTUP_PROBE_TIMEOUT"]),
    "periodSeconds": int(os.environ["STARTUP_PROBE_PERIOD"]),
    "failureThreshold": int(os.environ["STARTUP_PROBE_FAILURE_THRESHOLD"]),
    "tcpSocket": {"port": int(os.environ["PORT"])},
}

existing_env = {item["name"]: item for item in container.get("env", [])}
ordered_names = [item["name"] for item in container.get("env", [])]

for name, value in parse_env_vars(os.environ["ENV_VARS"]):
    existing_env[name] = {"name": name, "value": value}
    if name not in ordered_names:
        ordered_names.append(name)

for name, secret_name, version in parse_secret_vars(os.environ["SECRET_VARS"]):
    existing_env[name] = {
        "name": name,
        "valueSource": {
            "secretKeyRef": {
                "secret": secret_name,
                "version": version,
            }
        },
    }
    if name not in ordered_names:
        ordered_names.append(name)

container["env"] = [existing_env[name] for name in ordered_names]

if cloudsql_instance:
    volumes = [volume for volume in template.get("volumes", []) if volume.get("name") != "cloudsql"]
    volumes.append(
        {
            "name": "cloudsql",
            "cloudSqlInstance": {"instances": [cloudsql_instance]},
        }
    )
    template["volumes"] = volumes
    volume_mounts = [mount for mount in container.get("volumeMounts", []) if mount.get("name") != "cloudsql"]
    volume_mounts.append({"name": "cloudsql", "mountPath": "/cloudsql"})
    container["volumeMounts"] = volume_mounts

payload = {
    "template": template,
    "traffic": [{"type": "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST", "percent": 100}],
    "etag": service.get("etag"),
}
patch_url = service_url + "?" + urllib.parse.urlencode({"updateMask": "template,traffic"})
operation = request_json(patch_url, headers=headers, method="PATCH", payload=payload)

while not operation.get("done", False):
    time.sleep(5)
    operation = request_json(f"https://run.googleapis.com/v2/{operation['name']}", headers=headers)

if "error" in operation:
    print(json.dumps(operation["error"], indent=2), file=sys.stderr)
    raise SystemExit(1)

print(f"API fallback deployment completed for {service_name}.")
PY
}

if [[ "$SKIP_BUILD" != "true" ]]; then
  gcloud builds submit \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --config=cloudbuild.yaml \
    --substitutions="_IMAGE=${IMAGE},_PIP_INDEX_URL=${BUILD_PIP_INDEX_URL},_PIP_TRUSTED_HOST=${BUILD_PIP_TRUSTED_HOST}" \
    .
else
  echo "Skipping Cloud Build and reusing the latest pushed image tag."
fi

case "$DEPLOY_STRATEGY" in
  auto)
    if ! deploy_with_gcloud; then
      echo ""
      echo "gcloud run deploy failed. Falling back to the Cloud Run API patch flow..." >&2
      deploy_with_api "$(resolve_image_with_digest)"
    fi
    ;;
  gcloud)
    deploy_with_gcloud
    ;;
  api)
    deploy_with_api "$(resolve_image_with_digest)"
    ;;
  *)
    printf 'Unsupported DEPLOY_STRATEGY: %s\n' "$DEPLOY_STRATEGY" >&2
    exit 1
    ;;
esac

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
