"""
E1, step 2: calibration-free gaze-zone accuracy on MPIIFaceGaze.

Reads the per-subject CSVs from extract_features.py and writes tables,
figures and a markdown report to --out.

    python analyze.py --features features --out results

Protocol
--------
* Ground truth: the on-screen target (pixels) divided by that subject's
  screen size gives a position in [0, 1]^2; the zone is its grid cell.
* Every learned method is leave-one-subject-out (LOSO): trained on 14 people,
  tested on the 15th, so no calibration data from the test person is used.
* A frame with no detected face counts as WRONG in every accuracy figure.
* Headline = mean of the 15 per-subject accuracies, with a 95 % bootstrap CI
  over subjects. The pooled frame-level figure is reported alongside.
* Calibration reference: k frames of the test person correct the M2 output
  (k < 5: offset only; k >= 5: per-axis least-squares slope and offset,
  slope clipped to [0.5, 3]). Two draws of the k frames:
    - "first session": from the person's first recording day, scored on
      the other days (how a real calibration is used);
    - "random": from any day, scored on the rest.
  20 draws per k.
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

GRIDS = [(1, 2), (2, 1), (1, 3), (2, 2), (3, 3), (4, 4)]
CALIB_K = [1, 3, 5, 9, 16]
N_CALIB_DRAWS = 20
N_BOOT = 10000
SEED = 0

EYE = []
for e in ("reye", "leye"):
    EYE += [f"{e}_h", f"{e}_v", f"{e}_vlid", f"{e}_open"]
BS = ["bs_eyeLookInLeft", "bs_eyeLookInRight", "bs_eyeLookOutLeft", "bs_eyeLookOutRight",
      "bs_eyeLookUpLeft", "bs_eyeLookUpRight", "bs_eyeLookDownLeft", "bs_eyeLookDownRight",
      "bs_eyeBlinkLeft", "bs_eyeBlinkRight", "bs_eyeSquintLeft", "bs_eyeSquintRight"]
HEAD = ([f"R{i}{j}" for i in range(3) for j in range(3)]
        + ["tx", "ty", "tz", "yaw", "pitch", "roll", "nose_x", "nose_y", "interocular_norm"])
FEATURE_SETS = {
    "M0-fit": ["m0_cx", "m0_cy"],
    "M1": EYE + BS,
    "M2": EYE + BS + HEAD,
}


# ----------------------------------------------------------------------------
def load(features_dir: str) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(features_dir, "p[0-9][0-9].csv")))
    if not files:
        raise SystemExit(f"no pNN.csv in {features_dir}")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    counts = df.groupby("subject").size()
    print("frames per subject:", counts.to_dict(), flush=True)
    if counts.min() < 0.9 * counts.max():
        print("WARNING: some subjects have far fewer frames than others", flush=True)
    df["day"] = df["file"].str.split("/").str[0]
    df["gx"] = df["gt_px_x"] / df["screen_w_px"]
    df["gy"] = df["gt_px_y"] / df["screen_h_px"]
    df["detected"] = df["detected"].fillna(0).astype(int)
    return df


def zone_of(x, y, rows, cols):
    """Grid cell of normalised screen positions; NaN in -> -1 (always wrong)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    bad = ~(np.isfinite(x) & np.isfinite(y))
    c = np.clip(np.floor(np.nan_to_num(x) * cols), 0, cols - 1).astype(int)
    r = np.clip(np.floor(np.nan_to_num(y) * rows), 0, rows - 1).astype(int)
    z = r * cols + c
    z[bad] = -1
    return z


def m0_original_phi(cx, cy):
    """Repo's _phi for (3,3) with theta = 0.333, verbatim."""
    cx = np.asarray(cx, float)
    cy = np.asarray(cy, float)
    bad = ~(np.isfinite(cx) & np.isfinite(cy))
    col = np.clip(np.floor(np.nan_to_num(cx) / 0.333), 0, 2).astype(int)
    row = np.clip(np.floor(np.nan_to_num(cy) / 0.333), 0, 2).astype(int)
    z = row * 3 + col
    z[bad] = -1
    return z


def make_model(kind: str):
    if kind == "hgb":
        return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                             early_stopping=False, random_state=SEED)
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=1.0))


def loso_predict(df: pd.DataFrame, feats: list[str], kind: str) -> np.ndarray:
    """Returns an (N, 2) array of predicted (x, y); NaN where no face."""
    pred = np.full((len(df), 2), np.nan)
    det = df["detected"].values == 1
    for s in df["subject"].unique():
        tr = (df["subject"].values != s) & det
        te = (df["subject"].values == s) & det
        if te.sum() == 0:
            continue
        X_tr, X_te = df.loc[tr, feats].values, df.loc[te, feats].values
        for j, tgt in enumerate(("gx", "gy")):
            m = make_model(kind)
            m.fit(X_tr, df.loc[tr, tgt].values)
            pred[te, j] = m.predict(X_te)
    return pred


def per_subject_acc(df, zpred, rows, cols) -> pd.Series:
    zt = zone_of(df["gx"], df["gy"], rows, cols)
    ok = pd.Series(zpred == zt, index=df.index)
    return ok.groupby(df["subject"]).mean()


def boot_ci(v: np.ndarray, rng) -> tuple[float, float]:
    """BCa bootstrap CI of the mean over subjects; percentile if BCa is undefined."""
    from scipy.stats import bootstrap
    v = np.asarray(v, float)
    if np.allclose(v, v[0]):
        return float(v[0]), float(v[0])
    for method in ("BCa", "percentile"):
        r = bootstrap((v,), np.mean, n_resamples=N_BOOT, method=method, random_state=rng)
        lo, hi = r.confidence_interval
        if np.isfinite(lo) and np.isfinite(hi):
            return float(lo), float(hi)
    return float("nan"), float("nan")


def balanced_acc(zt, zp, K) -> float:
    return float(np.mean([np.mean(zp[zt == k] == k) for k in range(K) if np.any(zt == k)]))


def mm_error(df, pred) -> pd.Series:
    dx = (pred[:, 0] - df["gx"].values) * df["screen_w_mm"].values
    dy = (pred[:, 1] - df["gy"].values) * df["screen_h_mm"].values
    return pd.Series(np.sqrt(dx ** 2 + dy ** 2), index=df.index)


def fit_correction(p, t, k):
    if k < 5:
        return 1.0, float(np.mean(t - p))
    pm, tm = p.mean(), t.mean()
    sxx = np.sum((p - pm) ** 2)
    a = float(np.clip(np.sum((p - pm) * (t - tm)) / sxx, 0.5, 3.0)) if sxx > 1e-9 else 1.0
    return a, float(tm - a * pm)


def calibrate(df, base_pred, rows_cols, rng) -> list[dict]:
    """Per-subject k-shot correction of base_pred, scored on frames not used to calibrate."""
    out = []
    det = df["detected"].values == 1
    days = df["day"].values
    for s in df["subject"].unique():
        idx_all = np.where(df["subject"].values == s)[0]
        first_day = sorted(set(days[idx_all]))[0]
        pools = {
            "random": (idx_all[det[idx_all]], None),
            "first session": (idx_all[det[idx_all] & (days[idx_all] == first_day)],
                              idx_all[days[idx_all] != first_day]),
        }
        for scheme, (pool, test_fixed) in pools.items():
            for k in CALIB_K:
                if len(pool) < k or (test_fixed is not None and len(test_fixed) == 0):
                    continue
                for d in range(N_CALIB_DRAWS):
                    cal = rng.choice(pool, size=k, replace=False)
                    test = np.setdiff1d(idx_all, cal) if test_fixed is None else test_fixed
                    corr = np.empty((len(test), 2))
                    for j, tgt in enumerate(("gx", "gy")):
                        a, b = fit_correction(base_pred[cal, j], df[tgt].values[cal], k)
                        corr[:, j] = a * base_pred[test, j] + b   # NaN (no face) stays NaN -> wrong
                    sub = df.iloc[test]
                    for (r, c) in rows_cols:
                        acc = float(np.mean(zone_of(corr[:, 0], corr[:, 1], r, c)
                                            == zone_of(sub["gx"], sub["gy"], r, c)))
                        out.append({"scheme": scheme, "subject": s, "k": k, "draw": d,
                                    "grid": f"{r}x{c}", "acc": acc})
    return out


def confusion_png(df, zpred, rows, cols, title, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    K = rows * cols
    zt = zone_of(df["gx"], df["gy"], rows, cols)
    M = np.zeros((K, K + 1))
    for t, p in zip(zt, zpred):
        M[t, p if p >= 0 else K] += 1
    M = M / M.sum(axis=1, keepdims=True).clip(min=1)
    fig, ax = plt.subplots(figsize=(0.55 * K + 2.5, 0.55 * K + 1.8))
    im = ax.imshow(M, vmin=0, vmax=1, cmap="Blues")
    ax.set_xticks(range(K + 1), [str(i) for i in range(K)] + ["no face"], rotation=45)
    ax.set_yticks(range(K))
    ax.set_xlabel("predicted zone")
    ax.set_ylabel("true zone")
    ax.set_title(title, fontsize=9)
    for i in range(K):
        for j in range(K + 1):
            if M[i, j] >= 0.005:
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=6,
                        color="white" if M[i, j] > 0.5 else "black")
    fig.colorbar(im, ax=ax, fraction=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default="features")
    ap.add_argument("--out", default="results")
    ap.add_argument("--skip-calibration", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = np.random.default_rng(SEED)

    df = load(args.features)
    subjects = sorted(df["subject"].unique())
    det = df["detected"].values == 1

    # ---- data QA -------------------------------------------------------------
    qa = {
        "n_subjects": len(subjects),
        "n_frames": int(len(df)),
        "detection_rate": float(det.mean()),
        "detection_rate_min_subject": float(df.groupby("subject")["detected"].mean().min()),
        "gt_outside_screen_frac": float(((df.gx < 0) | (df.gx >= 1) | (df.gy < 0) | (df.gy >= 1)).mean()),
        "median_landmark_ms": float(df["landmark_ms"].median()),
        "unreadable_images": int(df["read_error"].fillna(0).sum()),
        "frames_per_subject": {k: int(v) for k, v in df.groupby("subject").size().items()},
        "median_R_scale": float(df.loc[det, "R_scale"].median()) if "R_scale" in df else None,
        "median_reye_h": float(df.loc[det, "reye_h"].median()),
    }
    # MediaPipe eye corners vs the dataset's hand-annotated eye corners (first 4 landmarks)
    if det.any():
        d = df[det]
        mp_c = np.stack([d[[f"{k}_x", f"{k}_y"]].values for k in ("mp_rout", "mp_rin", "mp_lout", "mp_lin")], 1)
        an_c = np.stack([d[[f"ann_lm{i}_x", f"ann_lm{i}_y"]].values for i in range(4)], 1)
        dist = np.linalg.norm(an_c[:, :, None, :] - mp_c[:, None, :, :], axis=-1).min(axis=2).mean(axis=1)
        io = d["interocular_norm"].values * d["img_w"].values
        rel = dist / np.maximum(io, 1e-6)
        qa["eye_corner_err_median_rel_interocular"] = float(np.median(rel))
        qa["eye_corner_err_gt_0.2_frac"] = float(np.mean(rel > 0.2))

    # ---- M0 diagnostics: where does the original feature actually land? ---------
    m0_zone = m0_original_phi(df["m0_cx"], df["m0_cy"])
    m0_hist = pd.Series(m0_zone).value_counts(normalize=True).sort_index()
    qa["m0_zone_distribution"] = {int(k): round(float(v), 4) for k, v in m0_hist.items()}
    qa["m0_cx_quantiles"] = df.loc[det, "m0_cx"].quantile([0.01, 0.5, 0.99]).round(4).tolist()
    qa["m0_cy_quantiles"] = df.loc[det, "m0_cy"].quantile([0.01, 0.5, 0.99]).round(4).tolist()
    true33 = zone_of(df["gx"], df["gy"], 3, 3)
    qa["gt_zone_distribution_3x3"] = {int(k): round(float(v), 4)
                                      for k, v in pd.Series(true33).value_counts(normalize=True).sort_index().items()}

    # ---- predictions -----------------------------------------------------------
    preds = {}
    preds["M0 original"] = np.c_[df["m0_cx"], df["m0_cy"]]
    preds["M0 original (x flipped)"] = np.c_[1 - df["m0_cx"], df["m0_cy"]]
    for name, feats in FEATURE_SETS.items():
        for kind in ("ridge", "hgb"):
            print(f"LOSO {name} {kind} ...", flush=True)
            preds[f"{name} {kind}"] = loso_predict(df, feats, kind)

    # majority zone of the training subjects, per grid (LOSO)
    rows_out, per_subj_rows = [], []
    for (r, c) in GRIDS:
        g = f"{r}x{c}"
        zt = zone_of(df["gx"], df["gy"], r, c)
        maj = np.full(len(df), -1)
        for s in subjects:
            tr = df["subject"].values != s
            maj[~tr] = pd.Series(zt[tr]).mode().iloc[0]
        maj = np.where(det, maj, -1)                       # needs a face like every other method
        method_z = {"chance (1/K)": None, "majority zone": maj}
        for name, p in preds.items():
            if name.startswith("M0 original") and (r, c) == (3, 3):
                z = m0_original_phi(p[:, 0], p[:, 1])
            else:
                z = zone_of(p[:, 0], p[:, 1], r, c)
            if name.startswith("M0 original"):
                z = np.where(det, z, -1)
                if (r, c) != (3, 3):
                    name = name.replace("M0 original", "M0 generalised")
            method_z[name] = z
        for name, z in method_z.items():
            if z is None:
                rows_out.append({"grid": g, "method": name, "acc_mean_subj": 1 / (r * c),
                                 "ci_lo": np.nan, "ci_hi": np.nan, "acc_pooled": 1 / (r * c),
                                 "acc_detected_only": 1 / (r * c), "balanced_acc": 1 / (r * c),
                                 "acc_min_subj": np.nan, "acc_max_subj": np.nan})
                continue
            ps = per_subject_acc(df, z, r, c)
            lo, hi = boot_ci(ps.values, rng)
            rows_out.append({"grid": g, "method": name, "acc_mean_subj": ps.mean(),
                             "ci_lo": lo, "ci_hi": hi, "acc_pooled": float(np.mean(z == zt)),
                             "acc_detected_only": float(np.mean(z[det] == zt[det])),
                             "balanced_acc": balanced_acc(zt, z, r * c),
                             "acc_min_subj": ps.min(), "acc_max_subj": ps.max()})
            for s, a in ps.items():
                per_subj_rows.append({"grid": g, "method": name, "subject": s, "acc": a})
        if (r, c) in [(3, 3), (2, 2), (1, 3)]:
            m0 = "M0 original" if (r, c) == (3, 3) else "M0 generalised"
            for name, fname in ((m0, "M0"), ("M2 hgb", "M2_hgb")):
                confusion_png(df, method_z[name], r, c, f"{name}, {g} (rows: true, cols: predicted)",
                              os.path.join(args.out, f"confusion_{fname}_{g}.png"))

    acc = pd.DataFrame(rows_out)
    acc.to_csv(os.path.join(args.out, "e1_zone_accuracy.csv"), index=False)
    pd.DataFrame(per_subj_rows).to_csv(os.path.join(args.out, "e1_per_subject.csv"), index=False)

    mm = []
    for name, p in preds.items():
        if name.startswith("M0"):
            continue
        e = mm_error(df, p)[det]
        mm.append({"method": name, "median_mm": e.median(), "mean_mm": e.mean(),
                   "p90_mm": e.quantile(0.9)})
    mm = pd.DataFrame(mm)
    mm.to_csv(os.path.join(args.out, "e1_mm_error.csv"), index=False)

    cal = None
    if not args.skip_calibration:
        print("calibration reference ...", flush=True)
        cal = pd.DataFrame(calibrate(df, preds["M2 hgb"], [(1, 3), (2, 2), (3, 3), (4, 4)], rng))
        cal.to_csv(os.path.join(args.out, "e1_calibration_raw.csv"), index=False)
        cal = (cal.groupby(["scheme", "grid", "k", "subject"])["acc"].mean()
                  .groupby(["scheme", "grid", "k"]).agg(["mean", "min", "max"]).reset_index())
        cal.to_csv(os.path.join(args.out, "e1_calibration.csv"), index=False)

    with open(os.path.join(args.out, "e1_qa.json"), "w") as f:
        json.dump(qa, f, indent=2)

    # ---- report ------------------------------------------------------------------
    L = ["# E1: calibration-free gaze-zone accuracy on MPIIFaceGaze", "",
         f"{qa['n_subjects']} subjects, {qa['n_frames']} frames. Face detected in "
         f"{qa['detection_rate']:.1%} of frames (lowest subject {qa['detection_rate_min_subject']:.1%}); "
         "undetected frames count as wrong.", "",
         "Accuracy = mean of per-subject accuracies (95% bootstrap CI over subjects). "
         "All learned methods are leave-one-subject-out.", ""]
    for g in [f"{r}x{c}" for r, c in GRIDS]:
        L += [f"## Grid {g}", "",
              "| Method | Accuracy | 95% CI | Pooled | Face-found frames only | Balanced | Worst subject | Best subject |",
              "|---|---|---|---|---|---|---|---|"]
        for _, x in acc[acc.grid == g].iterrows():
            ci = "" if np.isnan(x.ci_lo) else f"{x.ci_lo:.3f}–{x.ci_hi:.3f}"
            mn = "" if np.isnan(x.acc_min_subj) else f"{x.acc_min_subj:.3f}"
            mx = "" if np.isnan(x.acc_max_subj) else f"{x.acc_max_subj:.3f}"
            L.append(f"| {x.method} | {x.acc_mean_subj:.3f} | {ci} | {x.acc_pooled:.3f} | "
                     f"{x.acc_detected_only:.3f} | {x.balanced_acc:.3f} | {mn} | {mx} |")
        L.append("")
    L += ["## On-screen error (detected frames, mm)", "", "| Method | Median | Mean | 90th pct |",
          "|---|---|---|---|"]
    for _, x in mm.iterrows():
        L.append(f"| {x.method} | {x.median_mm:.0f} | {x.mean_mm:.0f} | {x.p90_mm:.0f} |")
    if cal is not None:
        L += ["", "## With k calibration frames from the test person (M2 hgb + correction)", "",
              "k < 5: offset only; k >= 5: slope and offset per axis. "
              "'first session' calibrates on day 1 and scores the other days.", "",
              "| Scheme | Grid | k | Mean acc | Worst subject | Best subject |", "|---|---|---|---|---|---|"]
        for _, x in cal.iterrows():
            L.append(f"| {x.scheme} | {x.grid} | {x.k} | {x['mean']:.3f} | {x['min']:.3f} | {x['max']:.3f} |")
    L += ["", "## Data QA and M0 diagnostics", "", "```", json.dumps(qa, indent=2), "```"]
    with open(os.path.join(args.out, "E1_REPORT.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
