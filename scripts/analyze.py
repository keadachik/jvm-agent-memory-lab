#!/usr/bin/env python3
"""
memory_samples_*.csv と driver_*.log を突き合わせて、Step境界ごとのメモリ値を
サマリ表として出力する。
"""
import csv
import os
import glob
import re
import sys
from datetime import datetime, timezone

LAB_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def parse_ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def load_samples():
    csv_path = sorted(glob.glob(f"{LAB_DIR}/driver/logs/memory_samples_*.csv"))[-1]
    samples = {"memlab": [], "memlab-baseline": []}
    with open(csv_path) as f:
        r = csv.DictReader(f)
        for row in r:
            samples[row["pod_label"]].append((parse_ts(row["timestamp_utc"]), int(row["bytes"])))
    return csv_path, samples


def value_at(samples, ts, tolerance_sec=30):
    best = None
    best_diff = None
    for t, v in samples:
        diff = abs((t - ts).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best = v
    if best_diff is not None and best_diff <= tolerance_sec:
        return best
    return None


def load_events(pattern):
    events = []
    for path in sorted(glob.glob(pattern)):
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
                events.append((ts, msg))
    events.sort(key=lambda x: x[0])
    return events


def mib(b):
    return b / 1024 / 1024


def main():
    csv_path, samples = load_samples()
    print(f"# CSV: {csv_path}")
    print(f"# samples: memlab={len(samples['memlab'])} memlab-baseline={len(samples['memlab-baseline'])}")
    print()

    main_events = load_events(f"{LAB_DIR}/driver/logs/driver_main*.log")
    base_events = load_events(f"{LAB_DIR}/driver/logs/driver_baseline*.log")

    # 主要マイルストーン: Step A各レート開始, Step B route解禁(20刻み), Step C開始/終了, Step D
    milestones = []
    for ts, msg in main_events:
        if "Step A: RPS=" in msg or "Step B 開始" in msg or "Step B 完了" in msg \
           or "Step C 開始" in msg or "Step C 完了" in msg or "Step D" in msg or "実験開始" in msg:
            milestones.append((ts, "main", msg))
        m = re.search(r"route (\d+) を解禁 \(累積アクティブルート数=(\d+)\)", msg)
        if m and int(m.group(2)) % 20 == 0:
            milestones.append((ts, "main", msg))

    milestones.sort(key=lambda x: x[0])

    print(f"{'timestamp':20} {'memlab(MiB)':>12} {'baseline(MiB)':>14} {'diff(MiB)':>10}  event")
    for ts, src, msg in milestones:
        mv = value_at(samples["memlab"], ts)
        bv = value_at(samples["memlab-baseline"], ts)
        mv_s = f"{mib(mv):.1f}" if mv else "?"
        bv_s = f"{mib(bv):.1f}" if bv else "?"
        diff_s = f"{mib(mv - bv):.1f}" if (mv and bv) else "?"
        print(f"{ts.isoformat():20} {mv_s:>12} {bv_s:>14} {diff_s:>10}  {msg[:80]}")

    print()
    print("# 全体レンジ")
    for label in ["memlab", "memlab-baseline"]:
        vals = [v for _, v in samples[label]]
        if vals:
            print(f"{label}: min={mib(min(vals)):.1f}MiB max={mib(max(vals)):.1f}MiB "
                  f"first={mib(vals[0]):.1f}MiB last={mib(vals[-1]):.1f}MiB")


if __name__ == "__main__":
    main()
