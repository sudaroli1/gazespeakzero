"""Check the numbers printed in Section 4.6 of the paper against the session logs.

Run:
    python code/study/verify_paper_numbers.py --sessions data/sessions/study6_deployment

Every figure in Table 6 and in the surrounding text is recomputed from the raw logs and
compared with what the paper claims. Exits non-zero if anything disagrees.

This exists because a paper's numbers and its data drift apart quietly. A reader should
be able to run one command and find out, and so should we before a revision.
"""
import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

# What Section 4.6 and Table 6 assert. Edit here only when the paper changes.
CLAIMED = {
    "P1": dict(attempted=80, skipped=3, excluded=8, analysed=69,
               per_trial=(66, 69), per_selection=(103, 137),
               unexcluded=(66, 77), gaze_ms=14.7),
    "P2": dict(attempted=80, skipped=0, excluded=15, analysed=65,
               per_trial=(49, 65), per_selection=(73, 116),
               unexcluded=(49, 80), gaze_ms=88.9),
    "pooled": dict(excluded=23, completed=157, analysed=134,
                   per_trial=(115, 134), per_selection=(176, 253),
                   calibrated=0.733, free=0.662,
                   side0=(63, 72), side1=(52, 62)),
}


def load(path):
    d = pd.read_csv(path)
    d["_row"] = np.arange(len(d))
    first = (d[d.event != "trial_end"].sort_values("_row")
             .groupby(["block", "trial"]).first()[["cue_zone"]])
    first.columns = ["cue_at_start"]
    te = d[d.event == "trial_end"].set_index(["block", "trial"]).join(first).reset_index()
    te["correct"] = te.item == te.cue_item
    te["skipped"] = te.detail.eq("skipped")
    te["reachable"] = te.cue_at_start.notna()
    ev = d[d.event.isin(["select", "reject"])].merge(
        te[["block", "trial", "reachable"]], on=["block", "trial"], how="left")
    ev["correct"] = ev.item.astype(str) == ev.cue_item.astype(str)
    frame_ms = pd.to_numeric(d.frame_ms, errors="coerce").dropna()
    return te, ev, frame_ms[frame_ms < 500]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", default="data/sessions/study6_deployment")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.sessions, "*_study_*.csv")))
    if not files:
        raise SystemExit(f"no session logs in {a.sessions}")

    per, fails = {}, []
    all_te, all_ev = [], []
    for f in files:
        who = os.path.basename(f).split("_")[0]
        te, ev, fms = load(f)
        all_te.append(te.assign(who=who)); all_ev.append(ev.assign(who=who))
        done, v = te[~te.skipped], te[~te.skipped & te.reachable]
        evv = ev[ev.reachable.fillna(False)]
        per[who] = dict(attempted=len(te), skipped=int(te.skipped.sum()),
                        excluded=int((~done.reachable).sum()), analysed=len(v),
                        per_trial=(int(v.correct.sum()), len(v)),
                        per_selection=(int(evv.correct.sum()), len(evv)),
                        unexcluded=(int(done.correct.sum()), len(done)),
                        gaze_ms=round(float(fms.median()), 1))

    T, E = pd.concat(all_te), pd.concat(all_ev)
    done, V = T[~T.skipped], T[~T.skipped & T.reachable]
    EV = E[E.reachable.fillna(False)]
    cal = EV.groupby("condition_calib").correct.mean()
    side = V.groupby("cue_at_start").correct.agg(["sum", "size"])
    per["pooled"] = dict(excluded=int((~done.reachable).sum()), completed=len(done),
                         analysed=len(V),
                         per_trial=(int(V.correct.sum()), len(V)),
                         per_selection=(int(EV.correct.sum()), len(EV)),
                         calibrated=round(float(cal.get("calibrated", np.nan)), 3),
                         free=round(float(cal.get("free", np.nan)), 3),
                         side0=(int(side.loc[0.0, "sum"]), int(side.loc[0.0, "size"])),
                         side1=(int(side.loc[1.0, "sum"]), int(side.loc[1.0, "size"])))

    print(f"{'quantity':34}{'in the paper':>18}{'recomputed':>18}")
    print("-" * 70)
    for who, claims in CLAIMED.items():
        if who not in per:
            print(f"  {who}: no matching session found"); fails.append(who); continue
        for k, want in claims.items():
            got = per[who][k]
            ok = got == want
            fails += [] if ok else [f"{who}.{k}"]
            print(f"{who + '.' + k:34}{str(want):>18}{str(got):>18}   {'ok' if ok else '<-- MISMATCH'}")
    print("-" * 70)
    if fails:
        print(f"FAILED: {len(fails)} disagreement(s): {', '.join(fails)}")
        return 1
    print(f"All {sum(len(c) for c in CLAIMED.values())} claimed numbers match the data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
