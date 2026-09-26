"""
E3, step 1: turn the intent bank into the cases the models see, under four conditions.

    python e3_build_cases.py --bank intent_bank.json --e2-items ../study2_scene_vocabulary/results/e2_items.csv --out cases.jsonl

Conditions
----------
clean        the intent's own objects
partial      the first object only
wrong_label  one object replaced by an item E2 actually proposed for that room and the
             labels verified as ABSENT (a real labelling error, not an invented one)
wrong_pick   one object replaced by another item that appeared on the same first screen
             of three in E2 for that room (a plausible gaze mis-selection)

Everything is drawn with a fixed seed, so every model sees exactly the same cases.
Without --e2-items a small built-in fallback pool is used (smoke tests only).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "study2_scene_vocabulary"))
from aac_vocab import canon  # noqa: E402

SEED = 0
FALLBACK_WRONG = {
    "bedroom": ["television set", "sofa", "bathtub", "kettle"],
    "bathroom": ["bed", "sofa", "refrigerator", "book"],
    "kitchen": ["bed", "pillow", "toilet", "sofa"],
    "dining": ["bed", "toilet", "television set", "blanket"],
    "living room": ["toilet", "bed", "stove", "sink"],
}


def pools(e2_items, bank_rooms):
    """(wrong pool, first-screen pool) per room, from E2's own output."""
    wrong, screen = collections.defaultdict(list), collections.defaultdict(list)
    if e2_items and os.path.exists(e2_items):
        import pandas as pd
        d = pd.read_csv(e2_items)
        d = d[d.method.isin(["clip", "qwen_vl", "blip2_qa", "blip2_caption"])]
        for room, g in d.groupby("room"):
            wrong[room] = sorted({canon(x) for x in g[g.status == "wrong"]["item"].astype(str)})
            screen[room] = sorted({canon(x) for x in g[g["rank"] <= 3]["item"].astype(str)})
    for room in bank_rooms:
        if not wrong.get(room):
            wrong[room] = [canon(x) for x in FALLBACK_WRONG.get(room, FALLBACK_WRONG["bedroom"])]
        if not screen.get(room):
            screen[room] = wrong[room]
    return wrong, screen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default=os.path.join(HERE, "intent_bank.json"))
    ap.add_argument("--e2-items", default=None)
    ap.add_argument("--out", default=os.path.join(HERE, "cases.jsonl"))
    a = ap.parse_args()
    bank = json.load(open(a.bank))
    wrong, screen = pools(a.e2_items, {b["room"] for b in bank})
    rng = random.Random(SEED)

    def swap(objs, pool, keep_first):
        """Replace one object (the last, or the only one) with a different item from pool."""
        pool = [p for p in pool if p not in objs]
        if not pool:
            return list(objs), None
        i = len(objs) - 1 if (len(objs) > 1 and keep_first) else rng.randrange(len(objs))
        out = list(objs)
        out[i] = rng.choice(pool)
        return out, i

    n = collections.Counter()
    with open(a.out, "w") as f:
        for b in bank:
            objs = b["objects"]
            cases = {"clean": (objs, None), "partial": (objs[:1], None)}
            cases["wrong_label"] = swap(objs, wrong[b["room"]], keep_first=True)
            cases["wrong_pick"] = swap(objs, screen[b["room"]], keep_first=True)
            for cond, (shown, idx) in cases.items():
                n[cond] += 1
                f.write(json.dumps({"case_id": f"{b['id']}:{cond}", "intent_id": b["id"],
                                    "condition": cond, "room": b["room"], "purpose": b["purpose"],
                                    "objects_true": objs, "objects_shown": shown,
                                    "swapped_index": idx}) + "\n")
    print(f"{sum(n.values())} cases -> {a.out}  {dict(n)}")
    print("pool sizes:", {r: (len(wrong[r]), len(screen[r])) for r in sorted(wrong)})


if __name__ == "__main__":
    main()
