#!/usr/bin/env bash
#
# APM エージェントのメモリ影響実験 トラフィックドライバー
#
# 前提: `kubectl port-forward svc/memlab 8080:8080` を別ターミナルで実行しておくこと
# (BASE_URL を変えれば port-forward 以外の経路でも可)
#
# 各ステップの開始・ルート追加・終了をログ(タイムスタンプ付き)に残す。
# このログと scripts/sample_memory.sh のメモリ CSV を突き合わせて、
# H_load / H_coverage / H_longtail を検証する。
#
# Usage: ./run_experiment.sh [A|B|C|D|ALL]
#   ALL (デフォルト) は A -> B -> C の順に流す。D は明示的に指定した時のみ実行する
#   (Step Bの直後にすぐ流すと "しばらく安定させてから" というH_longtailの前提が崩れるため)

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
N_ROUTES="${N_ROUTES:-200}"

# Step A: 単一ルートに対する負荷単体テスト (H_load)
STEP_A_ROUTE="${STEP_A_ROUTE:-1}"
STEP_A_RATES=(1 10 100)
STEP_A_DURATION="${STEP_A_DURATION:-180}"   # 各レート何秒維持するか

# Step B: カバレッジテスト (H_coverage)
STEP_B_RPS="${STEP_B_RPS:-5}"
STEP_B_INTERVAL="${STEP_B_INTERVAL:-20}"    # 新しいルートを解禁する間隔(秒)

# Step C: 高負荷下での再確認
STEP_C_RPS="${STEP_C_RPS:-100}"
STEP_C_DURATION="${STEP_C_DURATION:-300}"

LOG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_FILE:-$LOG_DIR/driver_$(date -u +%Y%m%dT%H%M%SZ).log}"

log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG_FILE"
}

# 一度のcurlで疎通確認
check_reachable() {
  if ! curl -s -o /dev/null -w '' --max-time 3 "$BASE_URL/healthz"; then
    echo "ERROR: $BASE_URL/healthz に到達できません。kubectl port-forward を確認してください。" >&2
    exit 1
  fi
}

# fire <rps> <duration_sec> <route1> [route2 ...]
# 指定ルート群にラウンドロビンで負荷をかける。rps<=20は逐次sleep、
# rps>20は1秒ごとにバックグラウンドcurlをrps個投げるバッチ方式(概算)。
fire() {
  local rps="$1" duration="$2"
  shift 2
  local routes=("$@")
  local n=${#routes[@]}
  local end=$(( $(date +%s) + duration ))
  if [ "$rps" -le 20 ]; then
    local interval
    interval=$(awk -v r="$rps" 'BEGIN{printf "%f", 1/r}')
    local i=0
    while [ "$(date +%s)" -lt "$end" ]; do
      curl -s -o /dev/null "$BASE_URL/route/${routes[$((i % n))]}" &
      i=$((i + 1))
      sleep "$interval"
    done
  else
    while [ "$(date +%s)" -lt "$end" ]; do
      for ((k = 0; k < rps; k++)); do
        curl -s -o /dev/null "$BASE_URL/route/${routes[$((RANDOM % n))]}" &
      done
      sleep 1
    done
  fi
  wait
}

step_a() {
  log "=== Step A 開始 (H_load検証: ルート${STEP_A_ROUTE}固定, RPSのみ変動) ==="
  for rate in "${STEP_A_RATES[@]}"; do
    log "Step A: RPS=${rate} を ${STEP_A_DURATION}秒間 維持 (route ${STEP_A_ROUTE} のみ)"
    fire "$rate" "$STEP_A_DURATION" "$STEP_A_ROUTE"
  done
  log "=== Step A 完了 ==="
}

step_b() {
  local resume_from="${STEP_B_RESUME_FROM:-1}"
  log "=== Step B 開始 (H_coverage検証: RPS=${STEP_B_RPS}固定, ルートを${STEP_B_INTERVAL}秒おきに1つずつ解禁, resume_from=${resume_from}) ==="
  local active=()
  if [ "$resume_from" -gt 1 ]; then
    for ((r = 1; r < resume_from; r++)); do active+=("$r"); done
    log "Step B: route 1..$((resume_from - 1)) は既に解禁済みとして再開 (累積アクティブルート数=${#active[@]})"
  fi
  for ((r = resume_from; r <= N_ROUTES; r++)); do
    active+=("$r")
    log "Step B: route ${r} を解禁 (累積アクティブルート数=${#active[@]})"
    fire "$STEP_B_RPS" "$STEP_B_INTERVAL" "${active[@]}"
  done
  log "=== Step B 完了 (全${N_ROUTES}ルートが既知の状態) ==="
}

step_c() {
  log "=== Step C 開始 (全ルート既知の状態でRPSを${STEP_C_RPS}へ急増、H_loadの反証テスト) ==="
  local all=()
  for ((r = 1; r <= N_ROUTES; r++)); do all+=("$r"); done
  fire "$STEP_C_RPS" "$STEP_C_DURATION" "${all[@]}"
  log "=== Step C 完了 ==="
}

step_d() {
  log "=== Step D 開始 (H_longtail検証: 一度も呼んでいない route 0 を初めて叩く) ==="
  curl -s -o /dev/null "$BASE_URL/route/0"
  log "Step D: route 0 を1回叩いた。以後しばらく観察を続けること (数分〜十数分、遅延して段差が出るか確認)"
}

check_reachable
log "実験開始。BASE_URL=$BASE_URL N_ROUTES=$N_ROUTES LOG_FILE=$LOG_FILE"

case "${1:-ALL}" in
  A) step_a ;;
  B) step_b ;;
  C) step_c ;;
  D) step_d ;;
  ALL)
    step_a
    step_b
    step_c
    log "Step D は明示的に './run_experiment.sh D' で実行すること(十分に安定させてから)"
    ;;
  *)
    echo "Usage: $0 [A|B|C|D|ALL]" >&2
    exit 1
    ;;
esac

log "実験終了。ログ: $LOG_FILE"
