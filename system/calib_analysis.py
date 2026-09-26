"""
Is the live failure the MAPPING or the FEATURES?

    python calib_analysis.py --pid P00

Reads sessions/calib_frames_<pid>.csv (written by the calibration) and asks, on this person's
own camera, three questions:

1. does the population model's output move with the dot at all (correlation, per-dot means)?
2. does a straight-line correction of that output recover the three zones?
3. does refitting a small model on the calibration frames themselves do better?

Pass 1 of the calibration fits; pass 2 is held out. Nothing here is fitted and tested on the
same frames.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EYE = ["reye_h", "reye_v", "reye_vlid", "reye_open", "leye_h", "leye_v", "leye_vlid", "leye_open"]
BS = ["bs_eyeLookInLeft", "bs_eyeLookInRight", "bs_eyeLookOutLeft", "bs_eyeLookOutRight",
      "bs_eyeLookUpLeft", "bs_eyeLookUpRight", "bs_eyeLookDownLeft", "bs_eyeLookDownRight",
      "bs_eyeBlinkLeft", "bs_eyeBlinkRight", "bs_eyeSquintLeft", "bs_eyeSquintRight"]
HEAD = ["R00", "R01", "R02", "R10", "R11", "R12", "R20", "R21", "R22", "tx", "ty", "tz",
        "yaw", "pitch", "roll", "nose_x", "nose_y", "interocular_norm"]


def zacc(pred, target, zones=3):
    p = np.clip((np.clip(pred, 0, 1) * zones).astype(int), 0, zones - 1)
    t = np.clip((np.clip(target, 0, 1) * zones).astype(int), 0, zones - 1)
    return float((p == t).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", default="P00")
    ap.add_argument("--sessions", default=os.path.join(HERE, "sessions"))
    a = ap.parse_args()
    f = os.path.join(a.sessions, f"calib_frames_{a.pid}.csv")
    if not os.path.exists(f):
        raise SystemExit(f"no {f} - run   python gaze_ui.py --calibrate --pid {a.pid}   first")
    d = pd.read_csv(f)
    d = d[d.get("detected", 1) == 1] if "detected" in d.columns else d
    print(f"{len(d)} frames, {d.target_x.nunique()} dot positions, passes {sorted(d['pass'].unique())}")

    print("\n1. does the population model follow the dot?")
    print(d.groupby("target_x").px_raw.agg(["size", "mean", "std"]).round(3).to_string())
    r = float(np.corrcoef(d.px_raw, d.target_x)[0, 1])
    print(f"   correlation(pred_x, dot position) = {r:+.3f}"
          f"   ({'useless' if abs(r) < 0.3 else 'weak' if abs(r) < 0.6 else 'usable'})")
    print(f"   raw output uses {d.px_raw.min():.2f}-{d.px_raw.max():.2f} of the screen")

    print("\n1b. is there anything to detect? the iris signal against the landmark noise")
    ew = [c for c in ("reye_width_px", "leye_width_px") if c in d.columns]
    if ew:
        print(f"   eye width in the image: {d[ew].mean(axis=1).mean():.1f} px "
              f"(more pixels = more gaze signal; this is the hard limit on accuracy)")
    for c in ("reye_h", "leye_h"):
        if c not in d.columns:
            continue
        per_dot = d.groupby("target_x")[c].mean()
        signal = float(per_dot.max() - per_dot.min())        # shift across the whole screen
        noise = float(d.groupby("target_x")[c].std().mean())  # jitter while staring at one dot
        snr = signal / noise if noise else float("nan")
        verdict = ("nothing to recover" if snr < 1.5 else
                   "marginal" if snr < 3 else "workable")
        print(f"   {c}: moves {signal:.4f} across the whole screen, jitter {noise:.4f} "
              f"-> signal-to-noise {snr:.2f} ({verdict})")
    print("   a three-zone decision needs roughly a third of that shift to beat the jitter.")

    tr, te = d[d["pass"] == 0], d[d["pass"] == 1]
    if not len(te):
        raise SystemExit("only one calibration pass in this file - rerun the calibration")

    print("\n2/3. three-zone accuracy, fitted on pass 1, tested on pass 2")
    rows = [("population model, raw", zacc(te.px_raw.values, te.target_x.values))]

    ax, bx = np.polyfit(tr.px_raw.values, tr.target_x.values, 1)
    rows.append((f"+ correction fitted the WRONG way (target on prediction), x' = {ax:.2f}x + {bx:.2f}",
                 zacc(ax * te.px_raw.values + bx, te.target_x.values)))
    a_f, b_f = np.polyfit(tr.target_x.values, tr.px_raw.values, 1)      # inverse fit
    if abs(a_f) > 1e-3:
        ai, bi = 1.0 / a_f, -b_f / a_f
        rows.append((f"+ correction fitted correctly (prediction on target), x' = {ai:.2f}x + {bi:.2f}",
                     zacc(ai * te.px_raw.values + bi, te.target_x.values)))

    try:
        from sklearn.linear_model import RidgeCV
        from sklearn.ensemble import HistGradientBoostingRegressor
    except ImportError:
        print("   (scikit-learn not available - skipping the refits)")
        rows = rows
    else:
        for name, cols in (("eye features only", EYE + BS),
                           ("eye + head features", EYE + BS + HEAD)):
            cols = [c for c in cols if c in d.columns]
            Xtr = tr[cols].astype(float).fillna(0).values
            Xte = te[cols].astype(float).fillna(0).values
            m = RidgeCV(alphas=np.logspace(-3, 3, 13)).fit(Xtr, tr.target_x.values)
            rows.append((f"refit on THIS session, ridge, {name}",
                         zacc(m.predict(Xte), te.target_x.values)))
        cols = [c for c in EYE + BS + HEAD if c in d.columns]
        g = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.08, random_state=0)
        g.fit(tr[cols].astype(float).values, tr.target_x.values)
        rows.append(("refit on THIS session, gradient boosting",
                     zacc(g.predict(te[cols].astype(float).values), te.target_x.values)))

    print()
    for name, v in rows:
        bar = "#" * int(round(v * 40))
        print(f"   {v:5.3f}  {bar:<40} {name}")
    print("\n   chance is 0.333. E1b reports 0.838 on the public data, other people's frames.")
    out = pd.DataFrame(rows, columns=["method", "held_out_3zone_accuracy"])
    out.to_csv(os.path.join(a.sessions, f"calib_analysis_{a.pid}.csv"), index=False)
    print(f"\nwrote sessions/calib_analysis_{a.pid}.csv")


if __name__ == "__main__":
    main()
