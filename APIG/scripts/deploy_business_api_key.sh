#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="agentkit-camera-demo"
SECRET_NAME="yingteng-camera-business-api-key"
KEY_VALUE="$(sed -n 's/^BUSINESS_API_KEY=//p' "${ROOT_DIR}/../.env" | head -n 1)"

if [[ -z "${KEY_VALUE}" ]]; then
  echo "BUSINESS_API_KEY is missing from the ignored project .env" >&2
  exit 1
fi

tmp_env="$(mktemp)"
cleanup() { rm -f "${tmp_env}"; }
trap cleanup EXIT
printf 'BUSINESS_API_KEY=%s\n' "${KEY_VALUE}" > "${tmp_env}"

kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
  --from-env-file="${tmp_env}" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

kubectl apply -f "${ROOT_DIR}/deploy/vke-camera-web.yaml"
kubectl -n "${NAMESPACE}" rollout status deployment/yingteng-camera-web --timeout=180s

echo "Deployment updated with BUSINESS_API_KEY Secret injection (value omitted)."
