#!/usr/bin/env python3
"""chart_data.json (prepare_chart_data.py の出力) から README 用の PNG を描く。"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LAB_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

with open(os.path.join(LAB_DIR, "chart_data.json")) as f:
    d = json.load(f)

fig, ax = plt.subplots(figsize=(11, 5), dpi=150)
for key, label, color in [("memlab", "with agent", "#c2410c"), ("memlab_baseline", "without agent (control)", "#2563eb")]:
    pts = d[key]
    ax.plot([p["t"] / 60 for p in pts], [p["mib"] for p in pts], label=label, color=color, linewidth=1.6)

for m in d["milestones"]:
    x = m["t"] / 60
    ax.axvline(x, color="#9ca3af", linestyle=":", linewidth=0.9)

# Phase labels inside the plot (minutes, from the driver logs)
phases = [(0, 9.1, "A"), (9.1, 75.8, "B: unlock routes 1→200 one by one"),
          (75.8, 80.8, "C"), (86.1, 130.7, "D: first call to an unused route")]
for x0, x1, text in phases:
    ax.text((x0 + x1) / 2, 300, text, ha="center", va="center", fontsize=8, color="#4b5563")

ax.set_xlabel("active elapsed time (min)")
ax.set_ylabel("container memory.current (MiB)")
ax.set_title("JVM container memory with vs. without APM agent (same image, same load)")
ax.grid(axis="y", color="#e5e7eb")
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, loc="lower right")
fig.tight_layout()
out = os.path.join(LAB_DIR, "docs", "memory_timeline.png")
fig.savefig(out)
print(out)
