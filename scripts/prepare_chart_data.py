#!/usr/bin/env python3
"""
memory_samples_*.csv + driver_*.log から、チャート描画用のJSONを作る。

外部要因でドライバーが停止していた無効期間(2026-09-03 04:07頃-07:15頃)は
「経過時間(active elapsed)」から差し引き、実験として連続した時間軸に補正する
(その旨は生成データにも明記する)。
"""
import csv
import os
import glob
import json
import re
from datetime import datetime, timezone

LAB_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# 中断期間 (外部要因でdriverが停止していた区間)。実験の一部ではないため経過時間から除外する。
GAP_START = datetime(2026, 9, 3, 4, 7, 9, tzinfo=timezone.utc)
GAP_END = datetime(2026, 9, 3, 7, 15, 53, tzinfo=timezone.utc)
GAP_SECONDS = (GAP_END - GAP_START).total_seconds()

EXPERIMENT_START = datetime(2026, 9, 3, 3, 30, 22, tzinfo=timezone.utc)


def parse_ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def active_elapsed(ts):
    """GAPを差し引いた経過秒数。GAP中のタイムスタンプはNoneを返し、呼び出し側で除外する。"""
    if ts <= GAP_START:
        return (ts - EXPERIMENT_START).total_seconds()
    if GAP_START < ts < GAP_END:
        return None
    return (ts - EXPERIMENT_START).total_seconds() - GAP_SECONDS


def load_samples():
    csv_path = sorted(glob.glob(f"{LAB_DIR}/driver/logs/memory_samples_*.csv"))[-1]
    series = {"memlab": [], "memlab-baseline": []}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            ts = parse_ts(row["timestamp_utc"])
            t = active_elapsed(ts)
            if t is None:
                continue
            series[row["pod_label"]].append(
                {"t": round(t, 1), "mib": round(int(row["bytes"]) / 1024 / 1024, 2)}
            )
    for k in series:
        series[k].sort(key=lambda p: p["t"])
    return series


def load_milestones():
    events = []
    for path in sorted(glob.glob(f"{LAB_DIR}/driver/logs/driver_main*.log")):
        with open(path) as f:
            for line in f:
                m = re.match(r"^(\S+) (.+)$", line.strip())
                if not m:
                    continue
                ts_str, msg = m.groups()
                try:
                    ts = parse_ts(ts_str)
                except ValueError:
                    continue
                label = None
                if "Step A: RPS=1 " in msg:
                    label = "Step A: RPS=1 (route1のみ)"
                elif "Step A: RPS=10 " in msg:
                    label = "Step A: RPS=10 (route1のみ)"
                elif "Step A: RPS=100 " in msg:
                    label = "Step A: RPS=100 (route1のみ)"
                elif "Step B 開始" in msg and "resume" not in path:
                    label = "Step B開始 (ルートを1つずつ解禁)"
                elif "Step B 完了" in msg:
                    label = "Step B完了 (全200ルート既知)"
                elif "Step C 開始" in msg:
                    label = "Step C: RPS100へ急増"
                elif "Step C 完了" in msg:
                    label = "Step C完了"
                elif "Step D 開始" in msg:
                    label = "Step D: 未使用ルートを初めて実行"
                if label:
                    events.append({"t": round(active_elapsed(ts), 1), "label": label})
    # 重複除去(同じlabelは最初の1回のみ)
    seen = set()
    uniq = []
    for e in events:
        if e["label"] in seen:
            continue
        seen.add(e["label"])
        uniq.append(e)
    uniq.sort(key=lambda e: e["t"])
    return uniq


def downsample(points, step=3):
    return points[::step] if len(points) > 400 else points


def main():
    series = load_samples()
    milestones = load_milestones()
    out = {
        "note": "経過時間(active_elapsed_sec)は、外部要因でドライバーが停止していた"
                f"約{int(GAP_SECONDS/60)}分間を差し引いた連続時間軸。",
        "memlab": downsample(series["memlab"]),
        "memlab_baseline": downsample(series["memlab-baseline"]),
        "milestones": milestones,
    }
    with open(f"{LAB_DIR}/chart_data.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"memlab points: {len(out['memlab'])}, baseline points: {len(out['memlab_baseline'])}, "
          f"milestones: {len(out['milestones'])}")
    print(f"max t: {out['memlab'][-1]['t']:.0f}s (~{out['memlab'][-1]['t']/60:.1f}min)")


if __name__ == "__main__":
    main()
