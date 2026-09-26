"""
E4, step 1: turn E1b and E2 into the numbers the simulator uses.

    python e4_build_inputs.py --e1b ../study1b_dwell_and_ablation/results/setup --e2 ../study2_scene_vocabulary/results --out inputs.json

Writes:
  accuracy per layout (2, 3, 4, 9 zones)   <- E1b dwell accuracy, 0.5 s, single frame
  answered_frac                            <- E1b
  rank curves: for each method, the rank at which the wanted object is offered
               (999 = never), one row per (scene, present AAC object)
  fixed_rank:  the same objects' position in the frequency-ordered 96-item vocabulary
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "study2_scene_vocabulary"))
from aac_vocab import canon  # noqa: E402

GRID_ZONES = {"1x2": 2, "1x3": 3, "2x2": 4, "3x3": 9}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--e1b", default=os.path.join(HERE, "..", "study1b_dwell_and_ablation", "results", "setup"))
    ap.add_argument("--e2", default=os.path.join(HERE, "..", "study2_scene_vocabulary", "results"))
    ap.add_argument("--dwell", type=int, default=500)
    ap.add_argument("--out", default=os.path.join(HERE, "inputs.json"))
    a = ap.parse_args()

    dw = pd.read_csv(os.path.join(a.e1b, "e1b_dwell_accuracy.csv"))
    dw = dw[(dw.dwell_ms == a.dwell) & (dw.method == "single")]
    acc, ci = {}, {}
    for grid, z in GRID_ZONES.items():
        r = dw[dw.grid == grid]
        if len(r):
            r = r.iloc[0]
            acc[str(z)] = float(r.acc)
            ci[str(z)] = [float(r.ci_lo), float(r.ci_hi)]
    answered = float(dw.answered_frac.iloc[0])

    scenes = {}
    for line in open(os.path.join(a.e2, "set.jsonl")):
        r = json.loads(line)
        scenes[r["image_id"]] = r
    voc = json.load(open(os.path.join(a.e2, "vocab.json")))
    id2name = dict(zip(voc["vocab_ids"], voc["vocab_names"]))
    vocab_ids = set(voc["vocab_ids"])

    # the best fixed list: the AAC vocabulary ordered by how often each item occurs in the set
    freq = collections.Counter()
    for s in scenes.values():
        freq.update(set(s.get("pos_x", s["pos"])) & vocab_ids)
    fixed_order = [canon(id2name[i]) for i, _ in freq.most_common()]
    fixed_order += [canon(n) for n in voc["vocab_names"] if canon(n) not in set(fixed_order)]
    fixed_pos = {n: i + 1 for i, n in enumerate(fixed_order)}

    items = pd.read_csv(os.path.join(a.e2, "e2_items.csv"))
    rows = []
    for meth, g in items.groupby("method"):
        for iid, gi in g.groupby("image_id"):
            present = {canon(id2name[i]) for i in set(scenes[iid].get("pos_x", scenes[iid]["pos"])) & vocab_ids}
            if not present:
                continue
            named = {}
            for _, r in gi.sort_values("rank").iterrows():
                c = r["category"]
                if isinstance(c, str):
                    named.setdefault(canon(c), int(r["rank"]))
            for obj in sorted(present):
                rows.append({"method": meth, "image_id": int(iid), "obj": obj,
                             "rank": named.get(obj, 999), "fixed_rank": fixed_pos.get(obj, len(fixed_pos) + 1)})
    d = pd.DataFrame(rows)
    out = {
        "accuracy_by_zones": acc, "accuracy_ci": ci, "answered_frac": answered,
        "dwell_ms": a.dwell, "vocabulary_size": len(fixed_order),
        "scene_seconds": {"qwen_vl": 1.902, "clip": 0.069},        # E2 medians, T4
        "rank_rows": d.to_dict("records"),
    }
    json.dump(out, open(a.out, "w"))
    print("accuracy by zones:", {k: round(v, 3) for k, v in acc.items()}, "| answered", round(answered, 3))
    print("vocabulary:", len(fixed_order), "| (scene, object) pairs:", len(d))
    print(d.groupby("method")["rank"].apply(
        lambda r: pd.Series({f"top{k}": round((r <= k).mean(), 3) for k in (3, 6, 12)})).unstack().to_string())
    print("wanted object in the fixed list's first screen (top 3):",
          round((d[d.method == "static"].fixed_rank <= 3).mean(), 3))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
