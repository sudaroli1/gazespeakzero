"""
E1b, step 2: does averaging over a dwell remove the frame-level scatter found in E1?

Inputs: the per-participant frame and Tobii CSVs written by eott_extract.py.

Protocol (fixed before seeing any EOTT result)
----------------------------------------------
* Ground truth comes from the Tobii Pro X3-120 (120 Hz), not from on-screen dots.
* v2 (21 Sep, after v1 found only 106 windows): dwell windows are consecutive
  non-overlapping windows of length L (0.5 s, 1 s) over each Tobii stream,
  kept when >= 70% of samples are valid and the gaze is stable,
  sqrt(var x + var y) <= 0.03 of the screen (primary; 0.02 and 0.05 reported
  as sensitivity). The window's true position is the mean of its Tobii samples.
* v2: the per-frame model is trained on every labelled frame of the other
  participants (v1 used only frames inside windows: 1,537 frames).
* Per-frame gaze model: the E1 "M2" feature set, gradient boosting, trained with
  10-fold GroupKFold over participants (no participant is ever in both train and
  test).
  Laptop and PC participants are pooled, with setup as a feature.
* A window's prediction from its frames, in four ways:
    single = the middle frame only;
    mean / median = mean or median of the per-frame predicted positions;
    vote = majority of the per-frame zones.
  Frames without a face are skipped. A window with fewer than
  MIN_FRAME_FRAC of the expected frames is WRONG (the system would not
  have answered).
* Accuracy = mean of per-participant accuracies, BCa 95% CI over participants.
* How much error is shared within a dwell: for each window, per-frame errors
  e_t are split into the window mean (shared) and deviations (independent).
  shared_frac = var(window means) / var(all frame errors). If this is near 1,
  averaging cannot help.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "study1_zone_classification"))
from analyze import EYE, BS, HEAD, zone_of, boot_ci   # noqa: E402

GRIDS = [(1, 2), (2, 1), (1, 3), (2, 2), (3, 3), (4, 4)]
DWELLS_MS = [500, 1000]
DISP = 0.04            # v1 (I-DT), kept for the record
DISP_STD = [0.03, 0.02, 0.05]   # primary first, then sensitivity
MARGIN_MS = 150
MIN_FRAME_FRAC = 0.5
N_FOLDS = 10
SEED = 0
FEATS = EYE + BS + HEAD + ["is_laptop"]


def load(d: str):
    fr = sorted(glob.glob(os.path.join(d, "P_*_frames.csv")))
    tb = sorted(glob.glob(os.path.join(d, "P_*_tobii.csv")))
    if not fr:
        raise SystemExit(f"no P_*_frames.csv in {d}")
    F = pd.concat([pd.read_csv(f) for f in fr], ignore_index=True)
    T = pd.concat([pd.read_csv(f) for f in tb], ignore_index=True)
    F["detected"] = F["detected"].fillna(0).astype(int)
    F["is_laptop"] = (F["setup"].str.lower() == "laptop").astype(int)
    return F, T


def fixations(t: pd.DataFrame, min_ms: float) -> list[tuple[float, float]]:
    """Dispersion-threshold (I-DT) fixations on one task's Tobii stream.
    Returns (start_ms, end_ms) for every fixation lasting at least min_ms."""
    t = t[t.tvalid == 1].dropna(subset=["tx", "ty"])
    ts, xs, ys = t.t_ms.values, t.tx.values, t.ty.values
    n = len(ts)

    def disp(i, j):
        return (xs[i:j + 1].max() - xs[i:j + 1].min()) + (ys[i:j + 1].max() - ys[i:j + 1].min())

    out, i = [], 0
    while i < n:
        j = np.searchsorted(ts, ts[i] + min_ms)          # first sample at or beyond min_ms
        if j >= n:
            break
        if disp(i, j) <= DISP and np.diff(ts[i:j + 1]).max(initial=0) <= 50:
            while j + 1 < n and ts[j + 1] - ts[j] < 50 and disp(i, j + 1) <= DISP:
                j += 1
            out.append((float(ts[i]), float(ts[j])))
            i = j + 1
        else:
            i += 1
    return out


def make_windows(T: pd.DataFrame, L: float, disp_std: float) -> pd.DataFrame:
    """Non-overlapping windows of length L laid end to end over each video's Tobii
    stream. A window is a dwell if >= 70% of its Tobii samples are valid and the
    gaze is stable: sqrt(var x + var y) <= disp_std (normalised screen units).
    (v1 required a whole I-DT fixation of L + 300 ms; on EOTT that left only 106
    windows of 0.5 s in 51 people, too few to estimate anything.)"""
    out = []
    for (p, task, video), t in T.groupby(["participant", "task", "video"]):
        t = t.sort_values("t_ms")
        t0 = t.t_ms.min()
        k = ((t.t_ms - t0) // L).astype(int)
        v = t[t.tvalid == 1]
        g = v.groupby(k[v.index])
        st = pd.DataFrame({"n": g.size(), "gx": g.tx.mean(), "gy": g.ty.mean(),
                           "sx": g.tx.std(), "sy": g.ty.std()})
        st = st[(st.n >= 0.7 * L / 1000 * 120) & (np.sqrt(st.sx ** 2 + st.sy ** 2) <= disp_std)]
        for kk, r in st.iterrows():
            out.append({"participant": p, "task": task, "video": video, "w_start": t0 + kk * L,
                        "w_end": t0 + (kk + 1) * L, "gx": r.gx, "gy": r.gy})
    cols = ["participant", "task", "video", "w_start", "w_end", "gx", "gy"]
    W = pd.DataFrame(out, columns=cols)
    return W[np.isfinite(W.gx) & np.isfinite(W.gy)].sort_values(["participant", "video", "w_start"]).reset_index(drop=True)


def assign_frames(F: pd.DataFrame, W: pd.DataFrame) -> pd.Series:
    """window id for each frame (or -1)."""
    wid = pd.Series(-1, index=F.index)
    for (p, video), w in W.groupby(["participant", "video"]):
        m = (F.participant == p) & (F.video == video)
        e = F.loc[m, "epoch_ms"].values
        k = np.searchsorted(w.w_start.values, e, side="right") - 1
        inside = (k >= 0) & (e < w.w_end.values[np.clip(k, 0, len(w) - 1)])
        wid.loc[m] = np.where(inside, w.index.values[np.clip(k, 0, len(w) - 1)], -1)
    return wid


def fit_predict(F: pd.DataFrame, train_mask: np.ndarray, n_folds: int = N_FOLDS) -> np.ndarray:
    pred = np.full((len(F), 2), np.nan)
    det = F.detected.values == 1
    groups = F.participant.values
    n_groups = len(np.unique(groups))
    gkf = GroupKFold(n_splits=min(n_folds, n_groups))
    X = F[FEATS].values
    for k, (tr, te) in enumerate(gkf.split(X, groups=groups)):
        trm = np.zeros(len(F), bool); trm[tr] = True
        trm &= train_mask & det
        tem = np.zeros(len(F), bool); tem[te] = True
        tem &= det
        for j, tgt in enumerate(("tobii_x", "tobii_y")):
            m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                              early_stopping=False, random_state=SEED)
            m.fit(X[trm], F[tgt].values[trm])
            pred[tem, j] = m.predict(X[tem])
        print(f"  fold {k + 1}/{gkf.get_n_splits()}", flush=True)
    return pred


def window_predictions(F, pred, W, L, fps_by_video):
    out = {}
    Fw = F.assign(px=pred[:, 0], py=pred[:, 1])
    Fw = Fw[Fw.wid >= 0]
    g = Fw.groupby("wid")
    for method in ("single", "mean", "median", "vote"):
        out[method] = {}
    expected = {i: max(1.0, fps_by_video.get(v, 30.0) * L / 1000) for i, v in zip(W.index, W.video)}
    centre = ((W.w_start + W.w_end) / 2).to_dict()
    for wid, d in g:
        d = d[d.detected == 1]
        if len(d) < MIN_FRAME_FRAC * expected[wid]:
            continue
        mid = d.iloc[int(np.argmin(np.abs(d.epoch_ms.values - centre[wid])))]
        out["single"][wid] = (mid.px, mid.py)
        out["mean"][wid] = (d.px.mean(), d.py.mean())
        out["median"][wid] = (d.px.median(), d.py.median())
        out["vote"][wid] = d[["px", "py"]].values          # zone vote done per grid
    return out


def score_windows(F, pred, W, L, fps_by_video, rng, setup_of=None):
    """Accuracy per grid and aggregation method, plus the shared-error ICC."""
    rows, shared = [], []
    F = F.copy()
    F["wid"] = assign_frames(F, W)
    wp = window_predictions(F, pred, W, L, fps_by_video)
    for (r, c) in GRIDS:
        zt = pd.Series(zone_of(W.gx, W.gy, r, c), index=W.index)
        for method, d in wp.items():
            zp = pd.Series(-1, index=W.index)          # unanswered windows are wrong
            for wid, v in d.items():
                if method == "vote":
                    z = zone_of(v[:, 0], v[:, 1], r, c)
                    z = z[z >= 0]
                    if len(z):
                        cnt = np.bincount(z, minlength=r * c)
                        top = np.flatnonzero(cnt == cnt.max())
                        zp[wid] = top[0] if len(top) == 1 else zone_of([v[:, 0].mean()], [v[:, 1].mean()], r, c)[0]
                else:
                    zp[wid] = zone_of([v[0]], [v[1]], r, c)[0]
            ok = ((zp == zt) & (zp >= 0) & (zt >= 0)).groupby(W.participant).mean()
            lo, hi = boot_ci(ok.values, rng)
            su = ok.groupby(ok.index.map(setup_of)).mean() if setup_of else {}
            rows.append({"grid": f"{r}x{c}", "method": method, "acc": ok.mean(), "ci_lo": lo, "ci_hi": hi,
                         "worst": ok.min(), "best": ok.max(), "answered_frac": len(d) / max(len(W), 1),
                         "acc_laptop": su.get("Laptop", np.nan), "acc_pc": su.get("PC", np.nan)})
    d = F[(F.wid >= 0) & (F.detected == 1)].join(W[["gx", "gy"]], on="wid")
    for ax, g in (("x", "gx"), ("y", "gy")):
        e = d[f"p{ax}"] - d[g]
        grp = e.groupby(d.wid)
        wm = grp.transform("mean")
        k, N = grp.ngroups, len(e)
        n_i = grp.size().values
        msb = float((n_i * (grp.mean().values - e.mean()) ** 2).sum() / max(k - 1, 1))
        msw = float(((e - wm) ** 2).sum() / max(N - k, 1))
        n0 = (N - (n_i ** 2).sum() / N) / max(k - 1, 1)
        icc = (msb - msw) / (msb + (n0 - 1) * msw) if (msb + (n0 - 1) * msw) > 0 else np.nan
        shared.append({"axis": ax, "shared_frac_icc": float(icc), "shared_frac_naive": float(wm.var() / e.var()),
                       "frames_per_window_mean": float(n_i.mean()),
                       "rmse_frame": float(np.sqrt((e ** 2).mean())),
                       "rmse_window_mean": float(np.sqrt((grp.mean() ** 2).mean()))})
    return rows, shared


def lag_check(F, T, pred):
    """Per participant: lag (ms) at which predicted x best matches Tobii x.
    Near 0 means webcam frames and Tobii samples are correctly aligned in time."""
    out = []
    Fp = F.assign(px=pred[:, 0])
    for p, d in Fp[Fp.px.notna()].groupby("participant"):
        best = (np.nan, -np.inf)
        tp = T[(T.participant == p) & (T.tvalid == 1)].dropna(subset=["tx"])
        rs = {}
        for v, dv in d.groupby("video"):
            tv = tp[tp.video == v].sort_values("t_ms")
            dv = dv.sort_values("epoch_ms")
            if len(tv) < 100 or len(dv) < 100:
                continue
            for lag in range(-600, 601, 33):
                j = np.interp(dv.epoch_ms.values + lag, tv.t_ms.values, tv.tx.values)
                rs.setdefault(lag, []).append(np.corrcoef(dv.px.values, j)[0, 1])
        if rs:
            lag, r = max(((l, float(np.nanmean(v))) for l, v in rs.items()), key=lambda z: z[1])
            r0 = float(np.nanmean(rs[min(rs, key=abs)]))
            out.append({"participant": p, "best_lag_ms": lag, "r_at_best": r, "r_at_zero": r0})
    return pd.DataFrame(out)


def estimate_lags(F, T, signal, step=10, span=800):
    """Clock offset between each participant's webcam frames and Tobii: the lag at
    which `signal` (a per-frame horizontal gaze signal from the webcam) correlates
    best with Tobii x, averaged over that participant's videos. Positive lag = the
    frame shows the eye at epoch_ms + lag. Only the Tobii time series is used, as
    in any two-sensor clock alignment; no zone labels are involved."""
    out = []
    Fh = F.assign(h=np.asarray(signal, float))
    for p, d in Fh[Fh.h.notna()].groupby("participant"):
        tp = T[(T.participant == p) & (T.tvalid == 1)].dropna(subset=["tx"])
        rs = {}
        for v, dv in d.groupby("video"):
            tv = tp[tp.video == v].sort_values("t_ms")
            dv = dv.sort_values("epoch_ms")
            if len(tv) < 100 or len(dv) < 100:
                continue
            for lag in range(-span, span + 1, step):
                j = np.interp(dv.epoch_ms.values + lag, tv.t_ms.values, tv.tx.values)
                rs.setdefault(lag, []).append(np.corrcoef(dv.h.values, j)[0, 1])
        if not rs:
            continue
        mean_r = {l: float(np.nanmean(v)) for l, v in rs.items()}
        lag = max(mean_r, key=lambda l: mean_r[l])
        out.append({"participant": p, "setup": d.setup.iloc[0], "lag_ms": lag,
                    "r_at_lag": mean_r[lag], "r_at_zero": mean_r[0]})
    return pd.DataFrame(out)


def apply_sync(F, T, lags: dict):
    """Shift each participant's frame times by its lag and re-attach the nearest
    valid Tobii sample (within 20 ms), exactly as the extractor did."""
    F = F.copy()
    F["epoch_ms"] = F["epoch_ms"] + F["participant"].map(lags).fillna(0.0)
    F["tobii_x"] = np.nan; F["tobii_y"] = np.nan; F["tobii_dt_ms"] = np.nan
    for (p, v), idx in F.groupby(["participant", "video"]).groups.items():
        tv = T[(T.participant == p) & (T.video == v)].sort_values("t_ms")
        if len(tv) < 2:
            continue
        tt = tv.t_ms.values
        e = F.loc[idx, "epoch_ms"].values
        j = np.clip(np.searchsorted(tt, e), 1, len(tt) - 1)
        jn = np.where(np.abs(tt[j - 1] - e) <= np.abs(tt[j] - e), j - 1, j)
        dt = np.abs(tt[jn] - e)
        ok = (dt <= 20) & (tv.tvalid.values[jn] == 1)
        F.loc[idx, "tobii_x"] = np.where(ok, tv.tx.values[jn], np.nan)
        F.loc[idx, "tobii_y"] = np.where(ok, tv.ty.values[jn], np.nan)
        F.loc[idx, "tobii_dt_ms"] = dt
    return F


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default="eott_features")
    ap.add_argument("--out", default="e1b_results")
    ap.add_argument("--sync", choices=["setup", "participant", "none"], default="setup",
                    help="clock correction between webcam and Tobii (v3). 'setup' = one median lag for Laptop and "
                         "one for PC (primary); 'participant' = each person's own lag; 'none' = v2 behaviour")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(SEED)

    F, T = load(a.features)
    # stage 1: out-of-fold predictions on the uncorrected data give a clean horizontal gaze
    # signal per frame; its best-matching lag against Tobii x is the clock offset
    print("stage 1: model on uncorrected clocks, to estimate the lag ...", flush=True)
    pred0 = fit_predict(F, F.tobii_x.notna().values & F.tobii_y.notna().values, n_folds=5)
    lags = estimate_lags(F, T, pred0[:, 0])
    lags.to_csv(os.path.join(a.out, "e1b_clock_lags.csv"), index=False)
    print(lags.groupby("setup").lag_ms.describe().round(0).to_string(), flush=True)
    if a.sync == "participant":
        F = apply_sync(F, T, dict(zip(lags.participant, lags.lag_ms)))
    elif a.sync == "setup":
        med = lags.groupby("setup").lag_ms.median().to_dict()
        F = apply_sync(F, T, {p: med[s_] for p, s_ in zip(lags.participant, lags.setup)})
    parts = sorted(F.participant.unique(), key=lambda s: int(s.split("_")[1]))
    qa = {"version": f"v3 (clock correction: {a.sync}; stability windows; model on all labelled frames)",
          "clock_lag_median_ms_by_setup": lags.groupby("setup").lag_ms.median().to_dict(),
          "n_participants": len(parts),
          "setups": F.groupby("setup").participant.nunique().to_dict(),
          "n_frames": int(len(F)),
          "face_detected": float(F.detected.mean()),
          "frames_with_tobii_label": float(F.tobii_x.notna().mean()),
          "median_tobii_dt_ms": float(F.tobii_dt_ms.median())}
    fps_by_video = {}
    for v, d in F.groupby(["participant", "video"]):
        span = (d.t_rel_ms.max() - d.t_rel_ms.min()) / 1000
        fps_by_video[v[1]] = (len(d) - 1) / span if span > 0 else 30.0
    qa["median_fps"] = float(np.median(list(fps_by_video.values())))

    # per-frame model on every frame with a face and a Tobii label (other participants only)
    train_mask = F.tobii_x.notna().values & F.tobii_y.notna().values
    qa["train_frames"] = int((train_mask & (F.detected.values == 1)).sum())
    print(json.dumps(qa, indent=2), flush=True)
    print("fitting per-frame model ...", flush=True)
    pred = fit_predict(F, train_mask)
    F["px"], F["py"] = pred[:, 0], pred[:, 1]

    lag = lag_check(F, T, pred)
    lag.to_csv(os.path.join(a.out, "e1b_lag_check.csv"), index=False)
    qa["lag_median_ms"] = float(lag.best_lag_ms.median())
    qa["lag_within_200ms_frac"] = float((lag.best_lag_ms.abs() <= 200).mean())
    qa["r_predx_tobiix_at_zero_median"] = float(lag.r_at_zero.median())

    # frame-level accuracy on all labelled frames (comparable with E1)
    fl = F[train_mask]
    frame_rows = []
    for (r, c) in GRIDS:
        ok = pd.Series(zone_of(fl.px, fl.py, r, c) == zone_of(fl.tobii_x, fl.tobii_y, r, c), index=fl.index)
        ps = ok.groupby(fl.participant).mean()
        lo, hi = boot_ci(ps.values, rng)
        su = ps.groupby(ps.index.map(F.groupby("participant").setup.first().to_dict())).mean()
        frame_rows.append({"grid": f"{r}x{c}", "acc": ps.mean(), "ci_lo": lo, "ci_hi": hi,
                           "acc_laptop": su.get("Laptop", np.nan), "acc_pc": su.get("PC", np.nan)})
    frame_acc = pd.DataFrame(frame_rows)

    setup_of = F.groupby("participant").setup.first().to_dict()
    rows, shared, wcount = [], [], []
    for disp in DISP_STD:
        for L in DWELLS_MS:
            W = make_windows(T, L, disp)
            npart = W.participant.nunique()
            wcount.append({"disp_std": disp, "dwell_ms": L, "windows": len(W), "participants": npart,
                           "median_per_participant": float(W.groupby("participant").size().median()) if len(W) else 0})
            print(f"disp {disp} dwell {L} ms: {len(W)} windows from {npart} participants", flush=True)
            if len(W) == 0:
                continue
            r_, s_ = score_windows(F, pred, W, L, fps_by_video, rng, setup_of)
            for x in r_: x.update(disp_std=disp, dwell_ms=L)
            for x in s_: x.update(disp_std=disp, dwell_ms=L)
            rows += r_; shared += s_
    acc, sh, wc = pd.DataFrame(rows), pd.DataFrame(shared), pd.DataFrame(wcount)
    acc.to_csv(os.path.join(a.out, "e1b_dwell_accuracy.csv"), index=False)
    frame_acc.to_csv(os.path.join(a.out, "e1b_frame_accuracy.csv"), index=False)
    sh.to_csv(os.path.join(a.out, "e1b_shared_error.csv"), index=False)
    wc.to_csv(os.path.join(a.out, "e1b_window_counts.csv"), index=False)
    with open(os.path.join(a.out, "e1b_qa.json"), "w") as f:
        json.dump(qa, f, indent=2)

    P = DISP_STD[0]
    L_ = ["# E1b (v3): dwell-level gaze-zone accuracy on EOTT (webcam video, Tobii ground truth)", "",
          f"Clock correction: **{a.sync}**. Webcam-to-Tobii lag estimated from stage-1 out-of-fold predictions, by setup "
          f"(median ms): {qa['clock_lag_median_ms_by_setup']}.", "",
          f"{qa['n_participants']} participants ({qa['setups']}), {qa['n_frames']} frames, "
          f"face detected in {qa['face_detected']:.1%}, median {qa['median_fps']:.1f} fps; "
          f"per-frame model trained on {qa['train_frames']} labelled frames (10-fold, grouped by participant).", "",
          f"**Timing check after correction:** best lag between predicted and Tobii x has median {qa['lag_median_ms']:.0f} ms; "
          f"{qa['lag_within_200ms_frac']:.0%} of participants within ±200 ms.", "",
          "## Windows found", "", "| stability (std) | dwell | windows | participants | median per participant |",
          "|---|---|---|---|---|"]
    for _, x in wc.iterrows():
        L_.append(f"| {x.disp_std} | {int(x.dwell_ms)} ms | {int(x.windows)} | {int(x.participants)} | {x.median_per_participant:.0f} |")
    L_ += ["", "## Single frames (all labelled frames; comparable with E1)", "",
           "| Grid | Accuracy | 95% CI | Laptop | PC |", "|---|---|---|---|---|"]
    for _, x in frame_acc.iterrows():
        L_.append(f"| {x.grid} | {x.acc:.3f} | {x.ci_lo:.3f}–{x.ci_hi:.3f} | {x.acc_laptop:.3f} | {x.acc_pc:.3f} |")
    for L in DWELLS_MS:
        s = acc[(acc.disp_std == P) & (acc.dwell_ms == L)] if len(acc) else acc
        if not len(s):
            continue
        L_ += ["", f"## Dwell {L} ms (primary stability threshold {P})", "",
               "| Grid | single frame | mean | median | vote | answered | mean, Laptop | mean, PC |",
               "|---|---|---|---|---|---|---|---|"]
        for g in [f"{r}x{c}" for r, c in GRIDS]:
            q = s[s.grid == g].set_index("method")
            L_.append(f"| {g} | {q.loc['single','acc']:.3f} | {q.loc['mean','acc']:.3f} "
                      f"({q.loc['mean','ci_lo']:.3f}–{q.loc['mean','ci_hi']:.3f}) | {q.loc['median','acc']:.3f} | "
                      f"{q.loc['vote','acc']:.3f} | {q.loc['mean','answered_frac']:.2f} | "
                      f"{q.loc['mean','acc_laptop']:.3f} | {q.loc['mean','acc_pc']:.3f} |")
    L_ += ["", "## Sensitivity: mean-of-dwell accuracy at other stability thresholds", "",
           "| stability | dwell | 1x2 | 1x3 | 2x2 | 3x3 |", "|---|---|---|---|---|---|"]
    for (d_, L), s in acc[acc.method == "mean"].groupby(["disp_std", "dwell_ms"]) if len(acc) else []:
        g = s.set_index("grid").acc
        L_.append(f"| {d_} | {L} ms | {g['1x2']:.3f} | {g['1x3']:.3f} | {g['2x2']:.3f} | {g['3x3']:.3f} |")
    L_ += ["", "## How much of the error is shared across a dwell", "",
           "ICC near 1: averaging cannot help. Near 0: averaging removes most of the error.", "",
           "| stability | dwell | axis | ICC | RMSE single frame | RMSE dwell mean | frames per window |",
           "|---|---|---|---|---|---|---|"]
    for _, x in sh.iterrows():
        L_.append(f"| {x.disp_std} | {x.dwell_ms} ms | {x.axis} | {x.shared_frac_icc:.2f} | {x.rmse_frame:.3f} | "
                  f"{x.rmse_window_mean:.3f} | {x.frames_per_window_mean:.1f} |")
    L_ += ["", "## QA", "", "```", json.dumps(qa, indent=2), "```"]
    with open(os.path.join(a.out, "E1b_REPORT.md"), "w") as f:
        f.write("\n".join(L_) + "\n")
    print("\n".join(L_))


if __name__ == "__main__":
    main()
