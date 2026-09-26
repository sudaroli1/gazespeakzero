"""
E1 follow-up analyses (run after analyze.py, on the same features):

1. Bits per selection (Wolpaw ITR) for each grid, from the per-subject accuracies.
2. Why calibration barely helps: split M2 hgb error into a per-person constant
   bias (what a calibration can remove) and frame-to-frame scatter (what it can't).
3. Horizontal vs vertical error.

    python extra_analysis.py --features features --results results --out results
"""
import argparse, os, sys, json
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import load, loso_predict, FEATURE_SETS  # noqa: E402


def wolpaw_bits(p, n):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    b = np.log2(n) + p * np.log2(p) + (1 - p) * np.log2((1 - p) / (n - 1))
    return np.where(p <= 1.0 / n, 0.0, b)          # at or below chance -> 0 bits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default="features")
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()

    ps = pd.read_csv(os.path.join(a.results, "e1_per_subject.csv"))
    rows = []
    for (g, m), d in ps.groupby(["grid", "method"]):
        r, c = map(int, g.split("x"))
        bits = wolpaw_bits(d["acc"].values, r * c)
        rows.append({"grid": g, "K": r * c, "method": m, "acc_mean": d["acc"].mean(),
                     "bits_per_selection_mean": bits.mean(),
                     "bits_min_subject": bits.min(), "bits_max_subject": bits.max()})
    bits = pd.DataFrame(rows).sort_values(["method", "K"])
    bits.to_csv(os.path.join(a.out, "e1_bits_per_selection.csv"), index=False)

    df = load(a.features)
    det = df["detected"].values == 1
    pred = loso_predict(df, FEATURE_SETS["M2"], "hgb")
    ex = (pred[:, 0] - df["gx"].values) * df["screen_w_mm"].values
    ey = (pred[:, 1] - df["gy"].values) * df["screen_h_mm"].values
    e = pd.DataFrame({"subject": df["subject"], "ex": ex, "ey": ey})[det]
    g = e.groupby("subject")
    bias = g[["ex", "ey"]].mean()
    within = g[["ex", "ey"]].std()
    dec = {
        "rms_total_x_mm": float(np.sqrt((e.ex ** 2).mean())),
        "rms_total_y_mm": float(np.sqrt((e.ey ** 2).mean())),
        "rms_person_bias_x_mm": float(np.sqrt((bias.ex ** 2).mean())),
        "rms_person_bias_y_mm": float(np.sqrt((bias.ey ** 2).mean())),
        "rms_frame_scatter_x_mm": float(np.sqrt((within.ex ** 2).mean())),
        "rms_frame_scatter_y_mm": float(np.sqrt((within.ey ** 2).mean())),
        "share_of_mse_removable_by_offset_x": float((bias.ex ** 2).mean() / (e.ex ** 2).mean()),
        "share_of_mse_removable_by_offset_y": float((bias.ey ** 2).mean() / (e.ey ** 2).mean()),
        "screen_w_mm_median": float(df["screen_w_mm"].median()),
        "screen_h_mm_median": float(df["screen_h_mm"].median()),
    }
    # the same in screen fractions (what decides a zone)
    fx = pred[:, 0] - df["gx"].values
    fy = pred[:, 1] - df["gy"].values
    dec["rms_frame_scatter_x_screen_frac"] = float(np.sqrt(pd.Series(fx[det]).groupby(df["subject"][det].values).std().pow(2).mean()))
    dec["rms_frame_scatter_y_screen_frac"] = float(np.sqrt(pd.Series(fy[det]).groupby(df["subject"][det].values).std().pow(2).mean()))
    per = pd.concat([bias.add_prefix("bias_"), within.add_prefix("scatter_")], axis=1)
    per.to_csv(os.path.join(a.out, "e1_bias_vs_scatter_per_subject.csv"))
    with open(os.path.join(a.out, "e1_bias_vs_scatter.json"), "w") as f:
        json.dump(dec, f, indent=2)

    print(bits[bits.method.isin(["M2 hgb", "M0 original", "M0 generalised"])].round(3).to_string(index=False))
    print(json.dumps(dec, indent=2))
    print(per.round(1).to_string())


if __name__ == "__main__":
    main()
