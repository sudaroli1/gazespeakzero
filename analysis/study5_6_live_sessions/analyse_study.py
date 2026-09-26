"""
Phase 1b analysis — written before data collection, per the protocol.

    python analyse_study.py --sessions ../../data/sessions/study5_author --out results

Reads the session logs, computes the pre-registered measures, tests H1-H3, and compares the
observed wrong-item rates with what the E4 simulator predicts at the accuracy measured here
(H4). Runs on synthetic logs too, so it can be checked before anyone is recruited:

    python analyse_study.py --demo
"""
from __future__ import annotations

import argparse
import glob
import os
import random
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SEED, N_BOOT = 0, 5000
ARM_MS = 800          # the reading window, disarmed by the interface; E4 models selection only
BASE = [("direct", "none"), ("direct", "double"), ("scan", "none"), ("scan", "double")]
CALIBS = ["free", "calibrated"]          # the 2x2x2 design: pattern x guard x calibration
CONDS = [(p, g, c) for c in CALIBS for p, g in BASE]
KEYS = ["session", "participant", "block", "trial"]   # what identifies one trial


def load(folder, include=None):
    """Read the session logs in `folder`.

    `include` is a list of substrings; a log is read if its file name contains any of
    them. The paper reports several of these sessions separately - they differ in the
    number of zones and in whether the capture fault was still present - so a reader
    reproducing one table needs the sessions that table was computed from, not all of
    them. README.md in this folder lists which sessions belong to which table.
    """
    rows = []
    files = sorted(glob.glob(os.path.join(folder, "*_study_*.csv")))
    if include:
        files = [f for f in files if any(k in os.path.basename(f) for k in include)]
        if not files:
            raise SystemExit(f"no session log in {folder} matches {include}")
    for f in files:
        d = pd.read_csv(f)
        d["participant"] = os.path.basename(f).split("_")[0]
        # One person recorded several sessions, and block/trial numbering restarts in
        # each. Keying trials on participant+block+trial alone therefore merges
        # different trials from the same person; the session name keeps them apart.
        d["session"] = os.path.splitext(os.path.basename(f))[0]
        rows.append(d)
    if not rows:
        raise SystemExit(f"no session logs in {folder}")
    d = pd.concat(rows, ignore_index=True)
    d["condition_guard"] = d.condition_guard.fillna("none")
    if "condition_calib" not in d.columns:                 # logs from before the calibration arm
        d["condition_calib"] = "free"
    d["condition_calib"] = d.condition_calib.fillna("free")
    if "site" not in d.columns:            # logs from before the multi-site protocol
        d["site"] = "S?"
    d["site"] = d.site.fillna("S?").astype(str)
    return d


def cluster_ci(values, groups, rng):
    """Bootstrap over participants, not over trials."""
    g = pd.Series(values).groupby(pd.Series(groups))
    means = g.mean()
    keys = means.index.to_numpy()
    if len(keys) < 2:
        return (np.nan, np.nan)
    draws = means.to_numpy()[rng.integers(0, len(keys), (N_BOOT, len(keys)))].mean(1)
    return round(float(np.percentile(draws, 2.5)), 4), round(float(np.percentile(draws, 97.5)), 4)


def reachability(d):
    """Was the cued word on screen when each trial BEGAN?

    Sessions recorded before 25 Sep 2026 carry a bug: the cue was chosen before the engine
    reset its page to 0, so on any trial following one that ended on a later page the cued
    word was picked from the previous page and was never on screen. Those trials cannot be
    completed and score as errors, so they are excluded - but the exclusion is reported
    rather than applied quietly, because it was not pre-registered.

    Judged at the FIRST logged frame of the trial, not the last. At the last frame it is
    circular: a correct selection implies the cue was on screen.
    """
    d = d.copy()
    d["_row"] = np.arange(len(d))
    if "session" not in d.columns:          # synthetic or hand-made frames
        d["session"] = d.get("participant", "S")
    if "cue_zone" not in d.columns:
        d["cue_zone"] = np.nan
    first = (d[d.event != "trial_end"].sort_values("_row")
             .groupby(KEYS).first()[["cue_zone"]])
    first.columns = ["cue_zone_at_start"]
    first = first.reset_index()

    # A log recorded before cue_zone was added has the column missing or empty
    # throughout. That is not evidence that every cue was off screen - it is no
    # evidence either way, and treating it as unreachable would silently discard a
    # whole session. Judge reachability only where the column was actually recorded.
    recorded = (d[d.cue_zone.notna()].groupby("participant").size()
                if "participant" in d.columns else pd.Series(dtype=int))
    has_col = set(recorded[recorded > 0].index)
    first["cue_recorded"] = first.participant.isin(has_col)
    first["reachable"] = np.where(first.cue_recorded,
                                  first.cue_zone_at_start.notna(),
                                  True)          # unknown: keep the trial
    return first


def per_selection_accuracy(d, drop_unreachable=True):
    """A dwell is 'correct' when its zone held the cued item at that moment."""
    dw = d[d.event.isin(["dwell"])].copy()
    # the cue's zone is recorded on the trial's rows; a dwell is correct if the item chosen
    # on that same event row matches the cue (select/reject rows carry the item)
    ev = d[d.event.isin(["select", "reject"])].copy()
    ev["correct"] = (ev.item.astype(str) == ev.cue_item.astype(str))
    if drop_unreachable:
        r = reachability(d)
        keys = KEYS
        ev = ev.merge(r[keys + ["reachable"]], on=keys, how="left")
        dw = dw.merge(r[keys + ["reachable"]], on=keys, how="left")
        ev["reachable"] = ev.reachable.fillna(True)
        dw["reachable"] = dw.reachable.fillna(True)
        ev, dw = ev[ev.reachable], dw[dw.reachable]
    return ev, dw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", default=os.path.join(HERE, "..", "..", "data", "sessions", "study5_author"))
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    ap.add_argument("--include", nargs="+", metavar="SUBSTRING",
                    help="only sessions whose file name contains one of these "
                         "(see README.md for which sessions a given table uses)")
    ap.add_argument("--demo", action="store_true", help="run on synthetic logs, to test the code")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(SEED)

    d = make_demo() if a.demo else load(a.sessions, a.include)

    # Report the exclusion before using it. A reader must be able to see how much of the
    # data this removes and from which sessions, without reading the code.
    reach = reachability(d)
    n_all, n_bad = len(reach), int((~reach.reachable).sum())
    if n_bad:
        print("=" * 72)
        print(f"UNREACHABLE-CUE EXCLUSION: {n_bad} of {n_all} trials "
              f"({100 * n_bad / n_all:.1f}%) had the cued word off screen when the trial")
        print("began, so they could not be completed. Cause: in sessions recorded before")
        print("25 Sep 2026 the cue was chosen before the page reset. These are dropped.")
        print("This exclusion was NOT pre-registered and must be stated in the paper.")
        by_p = reach[~reach.reachable].groupby("participant").size()
        for pid, n in by_p.items():
            tot = int((reach.participant == pid).sum())
            print(f"    {pid}: {n} of {tot} trials ({100 * n / tot:.0f}%)")
        print("=" * 72)
    elif reach.cue_recorded.all():
        print("unreachable-cue exclusion: none - every trial had its cue on screen at the start")
    no_col = sorted(reach.loc[~reach.cue_recorded, "participant"].unique())
    if no_col:
        print(f"NOTE: {', '.join(no_col)} predate the cue_zone column, so reachability "
              "cannot be\n      judged for them. Their trials are KEPT, not excluded - "
              "a missing column is\n      not evidence that the cue was off screen.")

    ev, _ = per_selection_accuracy(d)
    trials = d[d.event == "trial_end"].copy()
    keys = KEYS
    trials = trials.merge(reach[keys + ["reachable"]], on=keys, how="left")
    trials["reachable"] = trials.reachable.fillna(True)
    trials = trials[trials.reachable]
    trials["wrong"] = (trials.item.astype(str) != trials.cue_item.astype(str))
    trials["seconds"] = pd.to_numeric(trials.detail, errors="coerce") / 1000.0
    if trials.seconds.isna().all():                       # the log keeps the duration in frame_ms
        trials["seconds"] = pd.to_numeric(trials.frame_ms, errors="coerce") / 1000.0
    # the reading window is interface overhead, not selection time: take it off before H4
    trials["seconds_raw"] = trials.seconds
    trials["seconds"] = (trials.seconds - ARM_MS / 1000.0).clip(lower=0)

    rows = []
    for pattern, guard, cal in CONDS:
        e = ev[(ev.condition_pattern == pattern) & (ev.condition_guard == guard)
               & (ev.condition_calib == cal)]
        t = trials[(trials.condition_pattern == pattern) & (trials.condition_guard == guard)
                   & (trials.condition_calib == cal)]
        if not len(t):
            continue
        rows.append({
            "pattern": pattern, "guard": guard, "calibration": cal,
            "participants": t.participant.nunique(), "trials": len(t),
            "per_selection_accuracy": round(float(e.correct.mean()), 4) if len(e) else np.nan,
            "per_selection_accuracy_ci": cluster_ci(e.correct.values, e.participant.values, rng) if len(e) else None,
            "wrong_item_rate": round(float(t.wrong.mean()), 4),
            "wrong_item_rate_ci": cluster_ci(t.wrong.values, t.participant.values, rng),
            "seconds_per_trial": round(float(t.seconds.mean()), 2),
            "seconds_per_trial_incl_reading": round(float(t.seconds_raw.mean()), 2),
            "selections_per_trial": round(float(len(e) / max(1, len(t))), 2),
        })
    summ = pd.DataFrame(rows)
    summ.to_csv(os.path.join(a.out, "study_summary.csv"), index=False)

    # per-site reporting: descriptive only. Three participants per site cannot test for a
    # site effect, and the protocol says so; this table exists so the variation is visible.
    if "site" in ev.columns:
        per_site = ev.groupby(["site", "condition_calib"]).correct.agg(["size", "mean"]).round(3)
        per_site.to_csv(os.path.join(a.out, "accuracy_by_site.csv"))
        print("\nper-selection accuracy by site (descriptive; not powered to compare sites):")
        print(per_site.to_string())
        n_sites = ev.site.nunique()
        print(f"  {n_sites} site(s); participants per site:",
              dict(ev.groupby("site").participant.nunique()))


    if "cue_zone" in ev.columns and ev.cue_zone.notna().any():
        pz = ev.dropna(subset=["cue_zone"]).groupby(["condition_calib", "cue_zone"]).correct.agg(
            ["size", "mean"]).round(3)
        pz.to_csv(os.path.join(a.out, "accuracy_by_zone.csv"))
        print("\nper-selection accuracy by the zone the target was in:")
        print(pz.to_string())

    # H1: pooled per-selection accuracy, clustered CI, stated separately for each arm.
    # H1a is the pre-registered claim and applies to the calibration-free arm only.
    def pooled(sub):
        if not len(sub):
            return {"estimate": np.nan, "ci": (np.nan, np.nan), "supported": None}
        ci = cluster_ci(sub.correct.values, sub.participant.values, rng)
        return {"estimate": round(float(sub.correct.mean()), 4), "ci": ci,
                "supported": bool(ci[0] >= 0.75)}

    acc_by_cal = {c: pooled(ev[ev.condition_calib == c]) for c in CALIBS}
    h1 = {"H1a calibration-free accuracy >= 0.75": acc_by_cal["free"],
          "H1b calibrated accuracy >= 0.75": acc_by_cal["calibrated"]}
    acc = acc_by_cal["free"]["estimate"]                    # the headline, calibration-free

    # H5: calibration raises per-selection accuracy (paired over participants)
    pc = ev.groupby(["participant", "condition_calib"]).correct.mean().unstack()
    if set(CALIBS).issubset(pc.columns) and len(pc.dropna()) >= 2:
        dd = (pc["calibrated"] - pc["free"]).dropna().to_numpy()
        b = dd[rng.integers(0, len(dd), (N_BOOT, len(dd)))].mean(1)
        h5 = {"mean": round(float(dd.mean()), 4),
              "ci": (round(float(np.percentile(b, 2.5)), 4),
                     round(float(np.percentile(b, 97.5)), 4)),
              "n_participants": int(len(dd))}
    else:
        h5 = {"mean": np.nan, "ci": (np.nan, np.nan), "n_participants": 0}

    # H2/H3: differences between conditions, bootstrapped over participants
    def rate(pattern, guard, cal="free"):
        t = trials[(trials.condition_pattern == pattern) & (trials.condition_guard == guard)
                   & (trials.condition_calib == cal)]
        return t.groupby("participant").wrong.mean()

    def diff(a_, b_):
        x, y = a_.align(b_, join="inner")
        if len(x) < 2:
            return {"mean": np.nan, "ci": (np.nan, np.nan)}
        dd = (x - y).to_numpy()
        b = dd[rng.integers(0, len(dd), (N_BOOT, len(dd)))].mean(1)
        return {"mean": round(float(dd.mean()), 4),
                "ci": (round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4))}

    h2 = {"direct: guard - none": diff(rate("direct", "double"), rate("direct", "none")),
          "scan: guard - none": diff(rate("scan", "double"), rate("scan", "none"))}
    h3 = {"guarded: scan - direct": diff(rate("scan", "double"), rate("direct", "double")),
          "unguarded: scan - direct": diff(rate("scan", "none"), rate("direct", "none"))}

    # H3 is confounded by layout: in the direct pattern the "next" key occupies the last zone
    # and is never cued, so direct trials only ever use zones 0 and 1 while scanning uses all
    # three. Since the zones are not equally easy, the headline H3 comparison is restricted to
    # the zones both patterns use, and the unrestricted version is reported beside it.
    MATCHED_ZONES = [0.0, 1.0]
    h3_matched = {}
    if "cue_zone" in ev.columns and ev.cue_zone.notna().any():
        evm = ev[ev.cue_zone.isin(MATCHED_ZONES)]
        for guard in ("none", "double"):
            a_ = evm[(evm.condition_pattern == "scan") & (evm.condition_guard == guard)]
            b_ = evm[(evm.condition_pattern == "direct") & (evm.condition_guard == guard)]
            if len(a_) and len(b_):
                h3_matched[f"{guard}: scan - direct (zones 0,1 only)"] = diff(
                    a_.groupby("participant").correct.mean(),
                    b_.groupby("participant").correct.mean())

    # H4: does the E4 simulator predict these rates, run at the accuracy measured here?
    h4 = simulate_at(acc_by_cal, summ)
    h4.to_csv(os.path.join(a.out, "study_vs_simulation.csv"), index=False)

    L = ["# Phase 1b: live selection study", "",
         f"{trials.participant.nunique()} participants, {len(trials)} trials, "
         f"{len(ev)} selections." + ("  **DEMO DATA — not real**" if a.demo else ""), "",
         "## Per condition", "", summ.to_markdown(index=False), "",
         "## Per site (descriptive)", "",
         (per_site.to_markdown() if "site" in ev.columns else "_no site column_"), "",
         "## Pre-registered hypotheses", "",
         f"- **H1a** calibration-free per-selection accuracy {acc_by_cal['free']['estimate']} "
         f"{acc_by_cal['free']['ci']} — "
         f"{'supported' if acc_by_cal['free']['supported'] else 'NOT supported'}",
         f"- **H1b** calibrated per-selection accuracy {acc_by_cal['calibrated']['estimate']} "
         f"{acc_by_cal['calibrated']['ci']} — "
         f"{'supported' if acc_by_cal['calibrated']['supported'] else 'NOT supported'}",
         f"- **H5** calibration gain {h5['mean']} {h5['ci']} "
         f"(n={h5['n_participants']} participants)",
         f"- **H2** guard effect: direct {h2['direct: guard - none']}, scan {h2['scan: guard - none']}",
         f"- **H3** scanning vs direct: guarded {h3['guarded: scan - direct']}, "
         f"unguarded {h3['unguarded: scan - direct']}",
         f"- **H3 (layout-matched, zones 0-1 only — the pre-specified test)** {h3_matched}", "",
         "## H4: observed against the E4 simulator", "", h4.to_markdown(index=False), ""]
    open(os.path.join(a.out, "STUDY_REPORT.md"), "w").write("\n".join(L) + "\n")
    print(summ.to_string(index=False))
    print("\nH1:", h1, "\nH2:", h2, "\nH3:", h3,
          "\nH3 layout-matched:", h3_matched, "\nH5 calibration gain:", h5)
    print("\nwrote", a.out)


def simulate_at(acc_by_cal, summ):
    """Run the E4 simulator at the accuracy measured live in each arm, and compare."""
    sys.path.insert(0, os.path.join(HERE, "..", "study4_simulation"))
    try:
        import json

        from e4_sim import Interface, run
    except Exception as e:                                   # the simulator is optional here
        return pd.DataFrame([{"note": f"E4 simulator not available ({type(e).__name__}: {e})"}])
    inp = json.load(open(os.path.join(HERE, "..", "study4_simulation", "inputs.json")))
    base_a2 = {int(k): v for k, v in inp["accuracy_by_zones"].items()}
    rows_scene = pd.DataFrame(inp["rank_rows"])
    rows_scene = rows_scene[rows_scene.method == "qwen_vl"].to_dict("records")
    rng = np.random.default_rng(SEED)
    out = []
    for pattern, guard, cal in CONDS:
        acc = acc_by_cal.get(cal, {}).get("estimate", np.nan)
        if not (acc == acc):
            continue
        a2 = dict(base_a2)
        a2[3] = float(acc)                                   # the accuracy measured in this arm
        f = Interface(f"{pattern}_{guard}", 3, pattern, None if guard == "none" else "double", "scene")
        S, T, W, A, U = run(f, rows_scene, a2, inp["answered_frac"], inp["vocabulary_size"],
                            5000, rng, 0.8, 3.0)
        obs = summ[(summ.pattern == pattern) & (summ.guard == guard) & (summ.calibration == cal)]
        o = float(obs.wrong_item_rate.iloc[0]) if len(obs) else np.nan
        out.append({"pattern": pattern, "guard": guard, "calibration": cal,
                    "simulated_wrong_rate": round(float(W.mean()), 4),
                    "observed_wrong_rate": o,
                    "difference": round(float(W.mean()) - o, 4) if o == o else np.nan,
                    "within_0.10": bool(abs(float(W.mean()) - o) <= 0.10) if o == o else None})
    return pd.DataFrame(out)


def make_demo(n_participants=12, trials=10):
    """Synthetic logs with a known accuracy, so the analysis code can be checked before anyone
    is recruited. The generator is deliberately crude (it does not reproduce the interface's
    re-show behaviour), so its condition differences mean nothing: only the plumbing is being
    tested here, not the hypotheses."""
    rng = random.Random(SEED)
    items = ["water", "blanket", "toilet", "tv", "light", "phone", "book", "food"]
    rows = []
    for p in range(n_participants):
        pid = f"P{p + 1:02d}"
        site = f"S{p // 3 + 1}"            # four sites, three participants each
        base_acc = rng.gauss(0.72, 0.06)
        for pattern, guard, cal in CONDS:
            acc = base_acc + (0.10 if cal == "calibrated" else 0.0)
            for tr in range(1, trials + 1):
                cue = rng.choice(items)
                sels, t = 0, 0.0
                while True:
                    right = rng.random() < acc
                    chosen = cue if right else rng.choice([i for i in items if i != cue])
                    sels += 1
                    t += 800
                    rows.append({"t_ms": t, "block": 0, "condition_pattern": pattern,
                                 "condition_guard": guard, "condition_calib": cal,
                                 "trial": tr, "cue_item": cue,
                                 "event": "select" if guard == "none" else "reject",
                                 "zone": 0, "item": chosen, "page": 0, "detail": "", "frame_ms": 30,
                                 "px": 0.5, "py": 0.5, "participant": pid, "session": pid, "site": site})
                    if guard == "none":
                        break
                    again = chosen if rng.random() < acc else rng.choice(items)
                    sels += 1
                    t += 800
                    rows.append({"t_ms": t, "block": 0, "condition_pattern": pattern,
                                 "condition_guard": guard, "condition_calib": cal,
                                 "trial": tr, "cue_item": cue,
                                 "event": "select" if again == chosen else "reject", "zone": 0,
                                 "item": chosen if again == chosen else "", "page": 0,
                                 "detail": "double", "frame_ms": 30, "px": 0.5, "py": 0.5,
                                 "participant": pid, "session": pid, "site": site})
                    if again == chosen:
                        break
                rows.append({"t_ms": t, "block": 0, "condition_pattern": pattern,
                             "condition_guard": guard, "condition_calib": cal,
                             "trial": tr, "cue_item": cue, "event": "trial_end", "zone": "", "item": chosen, "page": "",
                             "detail": "", "frame_ms": t, "px": "", "py": "", "participant": pid, "session": pid, "site": site})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()
