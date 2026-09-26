"""Figure for Section 4.6: the same software on two machines.

Palette, fonts and figure size match study4_simulation/e4_figures.py so the new figure sits with the
others. Two labelled bars per panel - with n=2 a trend line would imply a fitted
relationship that two points cannot support, so none is drawn.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# A PDF carries its creation time, so two identical figures differ byte for byte
# unless the date is suppressed. Suppressing it means "re-run and diff" is a check a
# reader can actually use.
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED = "#0b0b0b", "#52514e"

def style(ax):
    ax.set_facecolor("#fcfcfb")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d8d7d2")
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(True, axis="y", color="#ececea", linewidth=0.8)
    ax.set_axisbelow(True)

plt.rcParams.update({"font.family": "DejaVu Sans", "figure.dpi": 150})
fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.4, 3.1))

# --- Panel A: the mechanism
machines = ["P1\n14.7 ms/frame", "P2\n88.9 ms/frame"]
readings = [15.1, 5.6]
b = a1.bar(machines, readings, color=[BLUE, ORANGE], width=0.55,
           edgecolor="#fcfcfb", linewidth=1.2)
a1.axhline(8, color=MUTED, linewidth=1, linestyle=":")
a1.text(1.46, 8.5, "8 readings", fontsize=7, color=MUTED, ha="right")
for r, v in zip(b, readings):
    a1.text(r.get_x() + r.get_width() / 2, v + 0.5, f"{v:.1f}", ha="center",
            fontsize=8.5, color=INK)
a1.set_ylabel("gaze readings per 500 ms dwell", fontsize=9, color=INK)
a1.set_ylim(0, 19)
a1.set_title("How many readings a decision rests on", fontsize=9.5, color=INK)
style(a1)

# --- Panel B: the consequence
import numpy as np
x = np.arange(2); w = 0.36
per_sel = [0.752, 0.629]
per_tri = [0.957, 0.754]
a2.bar(x - w/2, per_sel, w, label="per selection", color=BLUE,
       edgecolor="#fcfcfb", linewidth=1.2)
a2.bar(x + w/2, per_tri, w, label="per trial", color=ORANGE,
       edgecolor="#fcfcfb", linewidth=1.2)
for xi, v in zip(x - w/2, per_sel):
    a2.text(xi, v + 0.02, f"{v:.2f}", ha="center", fontsize=8, color=INK)
for xi, v in zip(x + w/2, per_tri):
    a2.text(xi, v + 0.02, f"{v:.2f}", ha="center", fontsize=8, color=INK)
a2.set_xticks(x); a2.set_xticklabels(["P1", "P2"], fontsize=8.5, color=MUTED)
a2.set_ylabel("accuracy", fontsize=9, color=INK)
a2.set_ylim(0, 1.34)
a2.set_title("What it costs", fontsize=9.5, color=INK)
a2.legend(fontsize=8, frameon=False, loc="upper left", labelcolor=INK,
          handlelength=1.1, handleheight=0.9, borderaxespad=0.2)
style(a2)

fig.tight_layout()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "figures")
os.makedirs(out, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(out, f"fig_deployment.{ext}"), bbox_inches="tight",
                metadata={"CreationDate": None} if ext == "pdf" else None)
print("wrote", os.path.join(out, "fig_deployment.pdf"))
