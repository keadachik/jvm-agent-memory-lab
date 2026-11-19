#!/usr/bin/env bash
# memlabアプリをビルドしてACRにpushする。
# Usage: ACR_NAME=<acrname> ./build_and_push.sh

set -euo pipefail

if [ -z "${ACR_NAME:-}" ]; then
  echo "ERROR: ACR_NAME を環境変数で指定してください (例: ACR_NAME=memlabacr $0)" >&2
  exit 1
fi

cd "$(dirname "${BASH_SOURCE[0]}")/../java-app"

IMAGE="${ACR_NAME}.azurecr.io/memlab:latest"

az acr build --registry "$ACR_NAME" --image memlab:latest .

echo "Built and pushed: $IMAGE"
