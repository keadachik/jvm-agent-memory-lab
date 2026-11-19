#!/usr/bin/env bash
# memlab / memlab-baseline の cgroup v2 memory.current(page cache を含む)を
# 一定間隔でサンプリングし、CSV に記録する。監視製品側のメトリクスに頼らない一次データ。
#
# Usage: ./sample_memory.sh [interval_sec] [out_csv]

set -euo pipefail

INTERVAL="${1:-10}"
OUT_CSV="${2:-$(dirname "${BASH_SOURCE[0]}")/../driver/logs/memory_samples_$(date -u +%Y%m%dT%H%M%SZ).csv}"

mkdir -p "$(dirname "$OUT_CSV")"
echo "timestamp_utc,pod_label,bytes" > "$OUT_CSV"

echo "Sampling every ${INTERVAL}s into $OUT_CSV (Ctrl-C to stop)"

while true; do
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  for label in memlab memlab-baseline; do
    pod="$(kubectl get pod -l app="$label" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
    if [ -n "$pod" ]; then
      bytes="$(kubectl exec "$pod" -c memlab -- cat /sys/fs/cgroup/memory.current 2>/dev/null || echo "")"
      if [ -n "$bytes" ]; then
        echo "${ts},${label},${bytes}" >> "$OUT_CSV"
      fi
    fi
  done
  sleep "$INTERVAL"
done
