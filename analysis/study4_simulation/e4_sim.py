"""
E4, step 2: simulate one message being selected, under each interface.

    python e4_sim.py --inputs inputs.json --out results [--trials 20000]

A selection shows k zones. The gaze lands on the intended zone with probability a(k) measured
in E1b, otherwise uniformly on one of the other zones; a dwell answers at all with probability
`answered_frac`. The wanted item's position comes from E2: its rank in the scene-grounded list
or in the frequency-ordered fixed vocabulary. If the scene list does not contain it, the user
pages to the end and falls back to the fixed vocabulary, and that cost is charged to the
scene-grounded method.

Three selection patterns:
  direct   pages of (k-1) items plus a "next" zone; the user drives the paging
  halving  the Look to Speak pattern: repeated left/right halving of the list
  scan     the page advances on its own every `scan_seconds`; the user only dwells when the
           wanted item is on screen, so all k zones hold items

Two ways to guard a selection:
  confirm  a yes/no question after the item (a 2-zone selection, so it can also err)
  double   the item is accepted only if the same zone is selected twice in a row

Returns per message: selections, seconds, whether the wrong item was finally spoken.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

SEED = 0
MAX_SELECTIONS = 80          # a message nobody could finish: counted as abandoned


class Interface:
    def __init__(self, name, zones, pattern="direct", guard=None, list_kind="fixed", list_size=None):
        self.name, self.zones, self.pattern, self.guard, self.list_kind = name, zones, pattern, guard, list_kind
        self.list_size = list_size            # override the vocabulary size (a short phrase list)
        self.items_per_page = zones if pattern == "scan" else zones - 1


def _dwell(rng, answered, sel, secs, sel_seconds):
    """One dwell attempt; unanswered dwells cost time and are repeated."""
    while True:
        sel += 1
        secs += sel_seconds
        if rng.random() < answered:
            return sel, secs, True
        if sel > MAX_SELECTIONS:
            return sel, secs, False


def simulate(f, target_rank, fixed_rank, acc, answered, rng, n_vocab, sel_seconds, scan_seconds):
    if f.list_size:                           # a short phrase list: what is not in it cannot be said
        n_vocab = f.list_size
        if (f.list_kind == "fixed" or target_rank >= 999) and fixed_rank > n_vocab:
            return 0, 0.0, False, "unavailable"
    scene = f.list_kind == "scene"
    rank = target_rank if scene else fixed_rank
    scene_len, fell_back, page = 12, False, 0
    sel, secs = 0, 0.0
    k, n_items = f.zones, f.items_per_page
    guard = f.guard

    if f.pattern == "halving":
        steps = int(np.ceil(np.log2(max(2, n_vocab))))
        while sel < MAX_SELECTIONS:
            wrong = False
            for _ in range(steps):
                sel, secs, ok = _dwell(rng, answered, sel, secs, sel_seconds)
                if not ok:
                    return sel, secs, False, True
                if rng.random() > acc[2]:
                    wrong = True
            if guard == "confirm":
                sel, secs, ok = _dwell(rng, answered, sel, secs, sel_seconds)
                says_yes = (rng.random() < acc[2]) == (not wrong)
                if not says_yes:
                    continue                     # rejected, start the halving again
            return sel, secs, wrong, False
        return sel, secs, False, True

    while sel < MAX_SELECTIONS:
        list_len = scene_len if (scene and not fell_back) else n_vocab
        n_pages = max(1, int(np.ceil(list_len / n_items)))
        if scene and not fell_back and rank >= 999:
            # the wanted object is not in the scene list: the user goes through it, then falls back
            if f.pattern == "scan":
                secs += n_pages * scan_seconds
            else:
                for _ in range(n_pages):
                    sel, secs, ok = _dwell(rng, answered, sel, secs, sel_seconds)
                    if not ok:
                        return sel, secs, False, True
            fell_back, rank, page = True, fixed_rank, 0
            continue
        target_page = ((rank - 1) // n_items) % n_pages
        target_slot = (rank - 1) % n_items

        if f.pattern == "scan":
            secs += ((target_page - page) % n_pages) * scan_seconds      # wait for the page to come round
            page = target_page
            correct_zone = target_slot
        else:
            correct_zone = target_slot if page == target_page else n_items   # "next" is the last zone

        sel, secs, ok = _dwell(rng, answered, sel, secs, sel_seconds)
        if not ok:
            return sel, secs, False, True
        landed = correct_zone if rng.random() < acc[k] else int(rng.choice([z for z in range(k) if z != correct_zone]))

        if f.pattern == "direct" and landed == n_items:                  # pressed "next"
            page = (page + 1) % n_pages
            continue

        chosen_right = (page == target_page and landed == target_slot)
        if guard == "double":                                            # repeat the same selection
            sel, secs, ok = _dwell(rng, answered, sel, secs, sel_seconds)
            if not ok:
                return sel, secs, False, True
            again = correct_zone if rng.random() < acc[k] else int(rng.choice([z for z in range(k) if z != correct_zone]))
            if again != landed:
                continue                                                 # disagreement: same page again
        elif guard == "confirm":
            sel, secs, ok = _dwell(rng, answered, sel, secs, sel_seconds)
            if not ok:
                return sel, secs, False, True
            says_yes = (rng.random() < acc[2]) == chosen_right
            if not says_yes:
                continue
        return sel, secs, (not chosen_right), False
    return sel, secs, False, True


def run(f, rows, acc, answered, n_vocab, trials, rng, sel_seconds, scan_seconds):
    idx = rng.integers(0, len(rows), trials)
    S = np.zeros(trials)
    T = np.zeros(trials)
    W = np.zeros(trials)
    A = np.zeros(trials)
    U = np.zeros(trials)                      # the message cannot be said at all with this interface
    for t, i in enumerate(idx):
        r = rows[i]
        s, sec, w, ab = simulate(f, r["rank"], r["fixed_rank"], acc, answered, rng, n_vocab,
                                 sel_seconds, scan_seconds)
        if ab == "unavailable":
            U[t] = 1
            continue
        S[t], T[t], W[t], A[t] = s, sec, w, bool(ab)
    return S, T, W, A, U


def wolpaw_bits(p, n):
    p = min(max(p, 1e-9), 1 - 1e-9)
    return float(np.log2(n) + p * np.log2(p) + (1 - p) * np.log2((1 - p) / max(1, n - 1)))


def _boot(v, rng, n=2000):
    v = np.asarray(v, float)
    m = v[rng.integers(0, len(v), (n, len(v)))].mean(1)
    return [round(float(np.percentile(m, 2.5)), 3), round(float(np.percentile(m, 97.5)), 3)]


def summarise(name, f, S, T, W, A, U=None, rng=None):
    if U is not None and U.sum():             # score only the messages this interface can say
        m = U == 0
        S, T, W, A = S[m], T[m], W[m], A[m]
    cover = float(1 - (U.mean() if U is not None else 0.0))
    ok = (1 - W.mean()) * cover               # a message it cannot say is not a message delivered
    ok_reach = 1 - W.mean()
    return {"interface": name, "list": f.list_kind, "pattern": f.pattern, "zones": f.zones,
            "guard": f.guard or "none",
            "selections_mean": round(float(S.mean()), 2),
            "seconds_mean": round(float(T.mean()), 2),
            "coverage": round(cover, 4),
            "wrong_message_rate": round(float(W.mean()), 4),
            "abandoned_rate": round(float(A.mean()), 4),
            "seconds_per_correct_message": round(float(T.mean() / max(1e-9, ok)), 2),
            "seconds_per_correct_if_sayable": round(float(T.mean() / max(1e-9, ok_reach)), 2),
            "correct_messages_per_minute": round(float(60.0 * ok / max(1e-9, T.mean())), 3),
            "wolpaw_bits_per_selection": round(wolpaw_bits(ok_reach, max(2, f.zones)), 3),
            "wrong_message_rate_ci": _boot(W, rng) if rng is not None else None,
            "seconds_mean_ci": _boot(T, rng) if rng is not None else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default="inputs.json")
    ap.add_argument("--out", default="results")
    ap.add_argument("--trials", type=int, default=20000)
    ap.add_argument("--seconds-per-selection", type=float, default=0.8)
    ap.add_argument("--scan-seconds", type=float, default=3.0)
    ap.add_argument("--scene-method", default="qwen_vl")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    inp = json.load(open(a.inputs))
    acc = {int(k): v for k, v in inp["accuracy_by_zones"].items()}
    answered, n_vocab = inp["answered_frac"], inp["vocabulary_size"]
    d = pd.DataFrame(inp["rank_rows"])
    rng = np.random.default_rng(SEED)
    rows_scene = d[d.method == a.scene_method].to_dict("records")
    rows_fixed = d[d.method == "static"].to_dict("records")

    ifaces = [
        Interface("look_to_speak", 2, "halving", None, "fixed"),
        Interface("look_to_speak_confirm", 2, "halving", "confirm", "fixed"),
        Interface("look_to_speak_16", 2, "halving", None, "fixed", list_size=16),
        Interface("look_to_speak_16_confirm", 2, "halving", "confirm", "fixed", list_size=16),
        Interface("row3_fixed16_double", 3, "direct", "double", "fixed", list_size=16),
        Interface("grid9_fixed", 9, "direct", None, "fixed"),
        Interface("row3_fixed", 3, "direct", None, "fixed"),
        Interface("row3_fixed_double", 3, "direct", "double", "fixed"),
        Interface("row3_scene", 3, "direct", None, "scene"),
        Interface("row3_scene_confirm", 3, "direct", "confirm", "scene"),
        Interface("row3_scene_double", 3, "direct", "double", "scene"),
        Interface("scan3_scene", 3, "scan", None, "scene"),
        Interface("scan3_scene_double", 3, "scan", "double", "scene"),
        Interface("scan3_fixed_double", 3, "scan", "double", "fixed"),
        Interface("scan2_scene_double", 2, "scan", "double", "scene"),
    ]
    out = []
    for f in ifaces:
        rows = rows_scene if f.list_kind == "scene" else rows_fixed
        S, T, W, A, U = run(f, rows, acc, answered, n_vocab, a.trials, rng, a.seconds_per_selection, a.scan_seconds)
        out.append(summarise(f.name, f, S, T, W, A, U, rng))
    res = pd.DataFrame(out).sort_values("seconds_per_correct_message")
    res.to_csv(os.path.join(a.out, "e4_interfaces.csv"), index=False)

    sens, T4 = [], max(2000, a.trials // 5)
    # 1. per-selection accuracy of the 3-zone row
    for p in np.arange(0.60, 0.99, 0.05):
        acc2 = dict(acc)
        acc2[3] = float(p)
        for f in [i for i in ifaces if i.zones == 3]:
            rows = rows_scene if f.list_kind == "scene" else rows_fixed
            S, T, W, A, U = run(f, rows, acc2, answered, n_vocab, T4, rng, a.seconds_per_selection, a.scan_seconds)
            sens.append({"knob": "accuracy_3zones", "value": round(float(p), 2),
                         **summarise(f.name, f, S, T, W, A, U)})
    # 2. how many items per screen, each at its own measured accuracy
    for zones in sorted(acc):
        for pattern, guard in (("direct", None), ("scan", "double")):
            f = Interface(f"{pattern}{zones}_scene{'_double' if guard else ''}", zones, pattern, guard, "scene")
            S, T, W, A, U = run(f, rows_scene, acc, answered, n_vocab, T4, rng, a.seconds_per_selection, a.scan_seconds)
            sens.append({"knob": "zones_per_screen", "value": zones, **summarise(f.name, f, S, T, W, A, U)})
    # 3. how good the scene list has to be
    base = pd.DataFrame(rows_scene)
    for share in np.arange(0.1, 0.99, 0.1):
        rows = base.copy()
        hit = rng.random(len(rows)) < share
        rows["rank"] = np.where(hit, rng.integers(1, 4, len(rows)), rows["rank"].values)
        for f in [i for i in ifaces if i.name in ("row3_scene_double", "scan3_scene_double")]:
            S, T, W, A, U = run(f, rows.to_dict("records"), acc, answered, n_vocab, T4, rng,
                                a.seconds_per_selection, a.scan_seconds)
            sens.append({"knob": "share_in_first_screen", "value": round(float(share), 2),
                         **summarise(f.name, f, S, T, W, A, U)})
    # 4. how fast the scan should advance
    for t in (2.0, 3.0, 4.0, 5.0, 7.0):
        for f in [i for i in ifaces if i.pattern == "scan" and i.zones == 3 and i.list_kind == "scene"]:
            S, T, W, A, U = run(f, rows_scene, acc, answered, n_vocab, T4, rng, a.seconds_per_selection, t)
            sens.append({"knob": "scan_seconds", "value": t, **summarise(f.name, f, S, T, W, A, U)})
    sens = pd.DataFrame(sens)
    sens.to_csv(os.path.join(a.out, "e4_sensitivity.csv"), index=False)

    keep = ["interface", "coverage", "selections_mean", "seconds_mean", "wrong_message_rate",
            "seconds_per_correct_message", "correct_messages_per_minute"]
    L = ["# E4: how long is a message, and how often is it wrong?", "",
         f"{a.trials} simulated messages per interface, seed {SEED}; {a.seconds_per_selection}s per "
         f"selection; scan advances every {a.scan_seconds}s; scene list = {a.scene_method}; "
         f"accuracy per layout from E1b: { dict(sorted(acc.items())) }.", "",
         res[keep].to_markdown(index=False), "",
         "## Sensitivity", "",
         sens[["knob", "value"] + keep].to_markdown(index=False), ""]
    open(os.path.join(a.out, "E4_REPORT.md"), "w").write("\n".join(L) + "\n")
    print(res[keep].to_string(index=False))
    print("\nwrote", a.out)


if __name__ == "__main__":
    main()
