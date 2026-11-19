#!/usr/bin/env bash
# memlabをKubernetesにデプロイする。
# Usage: ACR_NAME=<acrname> KUBE_CONTEXT=<your-context> ./deploy.sh

set -euo pipefail

if [ -z "${ACR_NAME:-}" ]; then
  echo "ERROR: ACR_NAME を環境変数で指定してください" >&2
  exit 1
fi
KUBE_CONTEXT="${KUBE_CONTEXT:-$(kubectl config current-context)}"

cd "$(dirname "${BASH_SOURCE[0]}")/.."

sed "s#REPLACE_ME/memlab:latest#${ACR_NAME}.azurecr.io/memlab:latest#" k8s/deployment.yaml \
  | kubectl --context "$KUBE_CONTEXT" apply -f -

echo "Deployed. 確認:"
echo "  kubectl --context $KUBE_CONTEXT get pods -l app=memlab"
echo "  kubectl --context $KUBE_CONTEXT describe pod -l app=memlab   # エージェント注入用の init container などがあるか確認"
