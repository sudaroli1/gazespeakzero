"""
E4 figures for the paper.

    python e4_figures.py --results results --out results

fig_e4_tradeoff.(pdf|png): time to a correct message against how often the wrong message is
spoken, one point per interface, directly labelled (no legend, no colour-only identity).
fig_e4_accuracy.(pdf|png): the same error rate as per-selection gaze accuracy varies, which
is the figure that carries the design rule.
"""
import argparse
import os

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# A PDF carries its creation time, so two identical figures differ byte for byte
# unless the date is suppressed. Suppressing it means "re-run and diff" is a check a
# reader can actually use.
NO_DATE = {"CreationDate": None}

BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"
INK, MUTED = "#0b0b0b", "#52514e"
SHOW = {                                   # interface -> (label, colour)
    "look_to_speak": ("Look to Speak (96 items)", ORANGE),
    "look_to_speak_16": ("Look to Speak (16 items)", ORANGE),
    "grid9_fixed": ("3x3 grid, fixed list", VIOLET),
    "row3_fixed_double": ("row of 3, fixed list, repeat", VIOLET),
    "row3_scene": ("row of 3, scene", BLUE),
    "row3_scene_confirm": ("row of 3, scene, confirm", BLUE),
    "row3_scene_double": ("row of 3, scene, repeat", BLUE),
    "scan3_scene_double": ("scanning row of 3, scene, repeat", AQUA),
}
SWEEP = {"row3_scene": ("row of 3, scene", BLUE, "-"),
         "row3_scene_double": ("row of 3, scene, repeat", BLUE, "--"),
         "scan3_scene": ("scanning, scene", AQUA, "-"),
         "scan3_scene_double": ("scanning, scene, repeat", AQUA, "--")}


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d8d7d2")
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(True, color="#ececea", linewidth=0.8)
    ax.set_axisbelow(True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.dpi": 150})
    d = pd.read_csv(os.path.join(a.results, "e4_interfaces.csv")).set_index("interface")
    s = pd.read_csv(os.path.join(a.results, "e4_sensitivity.csv"))

    # --- figure 1: the trade-off
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    style(ax)
    for name, (label, colour) in SHOW.items():
        if name not in d.index:
            continue
        r = d.loc[name]
        ax.scatter(r.seconds_mean, 100 * r.wrong_message_rate, s=70, color=colour,
                   edgecolor="#fcfcfb", linewidth=1.5, zorder=3)
        text = f"{label}\n({r.coverage:.0%} of messages sayable)" if r.coverage < 0.99 else label
        right = r.seconds_mean > 0.6 * d.seconds_mean.max()          # keep labels inside the axes
        ax.annotate(text, (r.seconds_mean, 100 * r.wrong_message_rate), textcoords="offset points",
                    xytext=(-9 if right else 9, 4), fontsize=8, color=INK,
                    ha="right" if right else "left")
    ax.axhline(5, color=MUTED, linewidth=1, linestyle=":")
    ax.text(0.5, 6, "5% wrong messages", fontsize=7.5, color=MUTED)
    ax.set_xlabel("seconds per message attempt", fontsize=9, color=INK)
    ax.set_ylabel("wrong message spoken (%)", fontsize=9, color=INK)
    ax.set_title("Speed against error, at the gaze accuracy measured in Study 1", fontsize=10, color=INK)
    ax.set_xlim(left=0)
    ax.set_ylim(-3, 95)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(a.out, f"fig_e4_tradeoff.{ext}"), bbox_inches="tight",
                    metadata=NO_DATE if ext == "pdf" else None)
    plt.close(fig)

    # --- figure 2: the design rule
    sw = s[s.knob == "accuracy_3zones"]
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    style(ax)
    for name, (label, colour, ls) in SWEEP.items():
        g = sw[sw.interface == name].sort_values("value")
        if not len(g):
            continue
        ax.plot(g.value, 100 * g.wrong_message_rate, color=colour, linestyle=ls, linewidth=2,
                marker="o", markersize=4, zorder=3)
        ax.annotate(label, (g.value.iloc[0], 100 * g.wrong_message_rate.iloc[0]),
                    textcoords="offset points", xytext=(6, 4), fontsize=8, color=INK)
    ax.axhline(5, color=MUTED, linewidth=1, linestyle=":")
    ax.text(0.605, 6.5, "5% wrong messages", fontsize=7.5, color=MUTED)
    meas = 0.838
    ax.axvline(meas, color=MUTED, linewidth=1, linestyle=":")
    ax.text(meas + 0.004, 62, "measured\n(Study 1, no calibration)", fontsize=7.5, color=MUTED)
    ax.set_xlabel("per-selection gaze accuracy, 3 zones", fontsize=9, color=INK)
    ax.set_ylabel("wrong message spoken (%)", fontsize=9, color=INK)
    ax.set_title("How accurate must the gaze be?", fontsize=10, color=INK)
    ax.set_xlim(0.58, 1.02)
    ax.set_ylim(-3, 80)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(a.out, f"fig_e4_accuracy.{ext}"), bbox_inches="tight",
                    metadata=NO_DATE if ext == "pdf" else None)
    plt.close(fig)
    print("wrote fig_e4_tradeoff and fig_e4_accuracy (pdf + png) in", a.out)


if __name__ == "__main__":
    main()
