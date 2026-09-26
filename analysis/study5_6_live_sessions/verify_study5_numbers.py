"""Check every number printed in Section 4.5 of the paper against the session logs.

Run:
    python verify_study5_numbers.py --sessions ../../data/sessions/study5_author

Section 4.5 reports several sessions separately, because they differ in ways that make
pooling them wrong: three zones against two, the capture fault present or fixed, and one
session whose paging behaviour is itself a finding. A reader cannot therefore check the
section by running one analysis over the whole folder, and neither can we. This script
names the session and the rule behind each published figure, recomputes it, and exits
non-zero if anything disagrees.

Its companion, verify_paper_numbers.py, does the same for Section 4.6.

Rules used, stated here rather than buried in the code:

  * "all selections" counts every dwell that resolved, including the first of a guarded
    pair. No exclusion is applied.
  * "cue on screen" keeps the selections made while the cued word was displayed, judged by
    the cue's zone being recorded on that selection's own row. Section 4.6 uses a stricter,
    first-frame rule for its exclusion; this one is the rule Section 4.5's two-zone
    sentence states, and it is reported as such.
  * trial duration is the value the interface logged for the trial, less the 800 ms reading
    window that Study 4 does not model - the same definition analyse_study.py uses.
"""
import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

ARM_MS = 800

# The sessions behind Section 4.5, by the substring that identifies the file.
THREE_ZONE = "PILOT_study_20260924-165155"    # 120 trials, three zones
TWO_ZONE = "PILOT3"                           # 96 trials, two zones
CAPTURE_FAULT = "P00_study_20260924-150417"   # 640x480, before the capture fix

# What the paper asserts. Edit here only when the paper changes.
CLAIMED = {
    "three_zone": {"free": (97, 0.443), "calibrated": (103, 0.524)},
    "by_zone": {
        "free":       {0.0: (36, 0.083), 1.0: (38, 0.974), 2.0: (13, 0.231)},
        "calibrated": {0.0: (39, 0.615), 1.0: (41, 0.537), 2.0: (11, 0.727)},
    },
    "capture_fault": {"selections": 37, "centre": 35},
    "two_zone_cue_on_screen": {"free": (53, 0.868), "calibrated": (41, 0.805)},
    "guard_wrong_item": {("scan", "none"): (0.083, 0.250),
                         ("scan", "double"): (0.250, 0.583),
                         ("direct", "either"): (0.417, 0.750)},
    # the paper prints two decimals for the fastest cell and one for the others
    "guard_seconds": {("scan", "none"): (0.37, 0.42),
                      ("scan", "double"): (1.4, 2.1),
                      ("direct", "either"): (0.7, 5.5)},
    "paging": {"page_changes": 92, "direct_trials": 48,
               "direct_selections": 81, "cue_off_screen": 53},
    "exclusion": {"unreachable": 43, "trials": 627},
}

fails = []


def check(label, got, want, tol=0.001):
    ok = (abs(got - want) <= tol) if isinstance(want, float) else (got == want)
    print(f"  {'OK  ' if ok else 'FAIL'} {label}: {got}" + ("" if ok else f"  (paper says {want})"))
    if not ok:
        fails.append(label)


def load(folder, include):
    files = [f for f in sorted(glob.glob(os.path.join(folder, "*_study_*.csv")))
             if include in os.path.basename(f)]
    if not files:
        raise SystemExit(f"no session log in {folder} matching {include!r}")
    d = pd.concat([pd.read_csv(f).assign(
        session=os.path.splitext(os.path.basename(f))[0]) for f in files], ignore_index=True)
    d["condition_guard"] = d.condition_guard.fillna("none")
    if "condition_calib" not in d.columns:
        d["condition_calib"] = "free"
    d["condition_calib"] = d.condition_calib.fillna("free")
    if "cue_zone" not in d.columns:
        d["cue_zone"] = np.nan
    return d


def selections(d):
    ev = d[d.event.isin(["select", "reject"])].copy()
    ev["correct"] = ev.item.astype(str) == ev.cue_item.astype(str)
    return ev


def durations(d):
    """The logged trial duration, less the reading window. As in analyse_study.py."""
    t = d[d.event == "trial_end"].copy()
    t["seconds"] = pd.to_numeric(t.detail, errors="coerce") / 1000.0
    if t.seconds.isna().all():
        t["seconds"] = pd.to_numeric(t.frame_ms, errors="coerce") / 1000.0
    t["seconds"] = (t.seconds - ARM_MS / 1000.0).clip(lower=0)
    t["wrong"] = t.item.astype(str) != t.cue_item.astype(str)
    return t



# ---------------------------------------------------------------------------
# Section 4.5.3, the calibration mapping. The paper states that on one session a
# monotone (isotonic) fit raised held-out three-zone accuracy from 0.675 to 0.762
# and the right-hand zone from 0.72 to 1.00, while the left-hand zone did not
# improve (0.56 to 0.53). Those figures are recomputed here from the calibration
# frames, fitting on the first calibration pass and testing on the second, so the
# claim is checkable rather than asserted.

CALIB = dict(session="P04", affine=0.675, isotonic=0.762,
             right_affine=0.72, right_isotonic=1.00,
             left_affine=0.56, left_isotonic=0.53)


def zone_of(x, zones=3):
    return np.clip((np.clip(x, 0, 1) * zones).astype(int), 0, zones - 1)


def check_calibration(sessions):
    """Raw / affine / isotonic three-zone accuracy, held out on the second pass."""
    print(f"\nSection 4.5.3, the calibration mapping - session {CALIB['session']}")
    try:
        from sklearn.isotonic import IsotonicRegression
    except ImportError:
        print("  SKIP scikit-learn is not installed, so this block cannot run")
        return
    path = os.path.join(sessions, f"calib_frames_{CALIB['session']}.csv")
    if not os.path.exists(path):
        print(f"  SKIP {os.path.basename(path)} is not in this copy of the data")
        return

    d = pd.read_csv(path)
    passes = sorted(d["pass"].unique())
    fit, test = d[d["pass"] == passes[0]], d[d["pass"] == passes[1]]
    target = zone_of(test.target_x.to_numpy())

    # An affine correction fitted prediction-on-target and then inverted. Fitted the
    # other way round it is attenuated by the noise in the predictor (regression
    # dilution) and corrects almost nothing; Sec. 4.5.3 reports that mistake too.
    slope, intercept = np.polyfit(fit.target_x, fit.px_raw, 1)
    affine = zone_of((test.px_raw.to_numpy() - intercept) / slope)
    iso = IsotonicRegression(out_of_bounds="clip").fit(fit.px_raw, fit.target_x)
    isotonic = zone_of(iso.predict(test.px_raw))

    def acc(pred, zone=None):
        keep = slice(None) if zone is None else (target == zone)
        return round(float((pred[keep] == target[keep]).mean()), 3)

    print(f"  fitted on pass {passes[0]} ({len(fit)} frames), "
          f"tested on pass {passes[1]} ({len(test)} frames)")
    check("affine, overall", acc(affine), CALIB["affine"])
    check("isotonic, overall", acc(isotonic), CALIB["isotonic"])
    check("affine, right-hand zone", acc(affine, 2), CALIB["right_affine"], tol=0.006)
    check("isotonic, right-hand zone", acc(isotonic, 2), CALIB["right_isotonic"])
    check("affine, left-hand zone", acc(affine, 0), CALIB["left_affine"], tol=0.006)
    check("isotonic, left-hand zone", acc(isotonic, 0), CALIB["left_isotonic"], tol=0.006)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "sessions", "study5_author"))
    a = ap.parse_args()

    print(f"\nSection 4.5, three zones - session {THREE_ZONE}, all selections")
    ev = selections(load(a.sessions, THREE_ZONE))
    for calib, (n, acc) in CLAIMED["three_zone"].items():
        sub = ev[ev.condition_calib == calib]
        check(f"{calib} selections", len(sub), n)
        check(f"{calib} per-selection accuracy", round(float(sub.correct.mean()), 3), acc)

    print("\nSection 4.5, the same session broken down by the zone the target was in")
    for calib, per_zone in CLAIMED["by_zone"].items():
        sub = ev[(ev.condition_calib == calib) & ev.cue_zone.notna()]
        for zone, (n, acc) in per_zone.items():
            z = sub[sub.cue_zone == zone]
            check(f"{calib}, zone {int(zone)}, n", len(z), n)
            check(f"{calib}, zone {int(zone)}, accuracy", round(float(z.correct.mean()), 3), acc)

    print(f"\nSection 4.5, the capture fault - session {CAPTURE_FAULT}")
    f = selections(load(a.sessions, CAPTURE_FAULT))
    zones = pd.to_numeric(f.zone, errors="coerce")
    check("selections in that session", len(f), CLAIMED["capture_fault"]["selections"])
    check("of them in the centre zone", int((zones == 1).sum()), CLAIMED["capture_fault"]["centre"])

    print(f"\nSection 4.5, two zones - session {TWO_ZONE}, selections made with the cue on screen")
    d3 = load(a.sessions, TWO_ZONE)
    on = selections(d3)
    on = on[on.cue_zone.notna()]
    for calib, (n, acc) in CLAIMED["two_zone_cue_on_screen"].items():
        sub = on[on.condition_calib == calib]
        check(f"{calib} selections", len(sub), n)
        check(f"{calib} per-selection accuracy", round(float(sub.correct.mean()), 3), acc)

    print(f"\nSection 4.5, Table 'Trial outcomes at two zones' - session {TWO_ZONE}, by block")
    t = durations(d3)
    for measure, claimed in (("wrong", CLAIMED["guard_wrong_item"]),
                             ("seconds", CLAIMED["guard_seconds"])):
        by_block = t.groupby(["condition_pattern", "condition_guard", "block"])[measure].mean()
        for (pattern, guard), (lo, hi) in claimed.items():
            m = (by_block.xs(pattern, level=0) if guard == "either"
                 else by_block.xs((pattern, guard), level=(0, 1)))
            name = f"{pattern}, {guard} guard, {'wrong-item rate' if measure == 'wrong' else 's/trial'}"
            dp = 3 if measure == "wrong" else 2
            tol = 0.001 if measure == "wrong" else 0.05
            check(f"{name} low", round(float(m.min()), dp), lo, tol=tol)
            check(f"{name} high", round(float(m.max()), dp), hi, tol=tol)

    print(f"\nSection 4.5, the paging pathology - session {TWO_ZONE}, direct condition")
    p = CLAIMED["paging"]
    direct = d3[d3.condition_pattern == "direct"]
    check("page changes", int((direct.event == "page").sum()), p["page_changes"])
    check("trials in that condition", int((direct.event == "trial_end").sum()), p["direct_trials"])
    dsel = selections(direct)
    check("selections in that condition", len(dsel), p["direct_selections"])
    check("of them with the cued word off screen", int(dsel.cue_zone.isna().sum()),
          p["cue_off_screen"])

    print("\nThe unreachable-cue exclusion, over every session in the folder")
    files = sorted(glob.glob(os.path.join(a.sessions, "*_study_*.csv")))
    n_trials = n_bad = 0
    for path in files:
        d = pd.read_csv(path)
        if "cue_zone" not in d.columns:
            n_trials += int((d.event == "trial_end").sum())
            continue                       # recorded before the column existed: kept, not judged
        d["_row"] = np.arange(len(d))
        first = (d[d.event != "trial_end"].sort_values("_row")
                 .groupby(["block", "trial"]).first()[["cue_zone"]])
        n_trials += int((d.event == "trial_end").sum())
        n_bad += int(first.cue_zone.isna().sum())
    check("trials excluded, cue off screen at the start", n_bad, CLAIMED["exclusion"]["unreachable"])
    check("cued trials in the folder", n_trials, CLAIMED["exclusion"]["trials"])

    check_calibration(a.sessions)

    print()
    if fails:
        print(f"{len(fails)} of the paper's numbers do not match the logs:")
        for f_ in fails:
            print("   ", f_)
        sys.exit(1)
    print("Every number in Section 4.5 matches the session logs.")


if __name__ == "__main__":
    main()
