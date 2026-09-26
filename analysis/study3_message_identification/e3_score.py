"""
E3, step 3: score every method.

    python e3_score.py --bank intent_bank.json --cases cases.jsonl \
        --outputs e3_outputs/outputs.jsonl --out e3_results

Ranking methods are scored directly. Generative methods are mapped to the intent bank by
sentence embedding (the generated message is matched against each intent's utterance and its
two paraphrases, best of the three), which is the automatic score; the blinded human sheet
covers the same generations.

Outputs: e3_summary.csv, e3_by_condition.csv, e3_paired_differences.csv, e3_per_case.csv,
e3_generations.csv (for the human check), E3_REPORT.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re

import numpy as np
import pandas as pd

SEED, N_BOOT = 0, 5000
CONDITIONS = ["clean", "partial", "wrong_label", "wrong_pick"]
EMBED_ID = "sentence-transformers/all-MiniLM-L6-v2"


def boot(v, rng):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) < 2:
        return (np.nan, np.nan)
    b = v[rng.integers(0, len(v), (N_BOOT, len(v)))].mean(1)
    return round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)


def paired(a, b, rng):
    d = np.asarray(a, float) - np.asarray(b, float)
    if len(d) < 2:
        return np.nan, (np.nan, np.nan)
    m = d[rng.integers(0, len(d), (N_BOOT, len(d)))].mean(1)
    return round(float(d.mean()), 4), (round(float(np.percentile(m, 2.5)), 4),
                                       round(float(np.percentile(m, 97.5)), 4))


def _tok(s):
    return set(re.findall(r"[a-z]+", str(s).lower())) - {"the", "a", "an", "i", "my", "me", "to",
                                                         "please", "it", "is", "of", "and", "you"}


class Mapper:
    """Generated text -> ranked intent ids. Sentence embeddings, with a token-overlap
    fallback so the smoke tests run without downloading a model."""

    def __init__(self, bank):
        self.bank = bank
        self.texts = [[b["utterance"]] + b["paraphrases"] for b in bank]
        self.model = None
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(EMBED_ID)
            flat = [t for group in self.texts for t in group]
            self.E = self.model.encode(flat, convert_to_tensor=True, normalize_embeddings=True)
            self.owner = [i for i, group in enumerate(self.texts) for _ in group]
            print("mapper: sentence embeddings")
        except Exception as e:                                   # offline / no package
            print(f"mapper: token overlap fallback ({type(e).__name__})")

    def rank(self, text, k=10):
        if self.model is not None:
            import torch
            q = self.model.encode(text, convert_to_tensor=True, normalize_embeddings=True)
            sims = (self.E @ q).cpu().numpy()
            best = {}
            for s, i in zip(sims, self.owner):
                best[i] = max(best.get(i, -9), float(s))
        else:
            t = _tok(text)
            best = {i: max(len(t & _tok(x)) / max(1, len(t | _tok(x))) for x in group)
                    for i, group in enumerate(self.texts)}
        order = sorted(best, key=lambda i: (-best[i], self.bank[i]["id"]))[:k]
        return [self.bank[i]["id"] for i in order]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default="intent_bank.json")
    ap.add_argument("--cases", default="cases.jsonl")
    ap.add_argument("--outputs", default="e3_outputs/outputs.jsonl")
    ap.add_argument("--out", default="e3_results")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(SEED)

    bank = json.load(open(a.bank))
    byid = {b["id"]: b for b in bank}
    cases = {c["case_id"]: c for c in (json.loads(l) for l in open(a.cases))}
    outs = []
    for l in open(a.outputs):
        try:
            outs.append(json.loads(l))
        except json.JSONDecodeError:
            pass
    last = {(o["method"], o["case_id"]): o for o in outs if o["case_id"] in cases}
    methods = sorted({m for m, _ in last})
    common = set.intersection(*[{c for (m, c) in last if m == meth} for meth in methods])
    print("cases per method:", {m: sum(1 for (mm, _) in last if mm == m) for m in methods},
          "| scored (common):", len(common), flush=True)

    mapper = Mapper(bank) if any("text" in o for o in last.values()) else None
    rows, gens = [], []
    for (meth, cid), o in sorted(last.items()):
        if cid not in common:
            continue
        c = cases[cid]
        ranked = o.get("ranked")
        if ranked is None:
            ranked = mapper.rank(o.get("text", ""))
            gens.append({"method": meth, "case_id": cid, "intent_id": c["intent_id"],
                         "condition": c["condition"], "objects_shown": ", ".join(c["objects_shown"]),
                         "generated": o.get("text", ""), "reference": byid[c["intent_id"]]["utterance"],
                         "mapped_to": byid[ranked[0]]["utterance"] if ranked else "",
                         "auto_correct": bool(ranked and ranked[0] == c["intent_id"])})
        gold = c["intent_id"]
        rows.append({"method": meth, "case_id": cid, "intent_id": gold, "condition": c["condition"],
                     "purpose": c["purpose"], "room": c["room"], "seconds": o.get("seconds", np.nan),
                     "n_objects_true": len(c["objects_true"]),
                     # in a noise condition a one-object intent loses its only object: nothing can recover it
                     "recoverable": bool(c["condition"] in ("clean", "partial") or len(c["objects_true"]) > 1),
                     "top1": float(bool(ranked[:1] == [gold])), "top3": float(gold in ranked[:3]),
                     "top5": float(gold in ranked[:5]),
                     "rank": (ranked.index(gold) + 1) if gold in ranked else np.nan})
    per = pd.DataFrame(rows)
    per.to_csv(os.path.join(a.out, "e3_per_case.csv"), index=False)
    if gens:
        pd.DataFrame(gens).to_csv(os.path.join(a.out, "e3_generations.csv"), index=False)

    summ = []
    for meth, d in per.groupby("method"):
        r = {"method": meth, "cases": len(d), "median_seconds": float(np.nanmedian(d.seconds))}
        for k in ("top1", "top3", "top5"):
            r[k] = round(float(d[k].mean()), 4)
            r[k + "_ci"] = boot(d[k].values, rng)
        for cond in CONDITIONS:
            dc = d[d.condition == cond]
            if len(dc):
                r[f"top1_{cond}"] = round(float(dc.top1.mean()), 4)
                r[f"top3_{cond}"] = round(float(dc.top3.mean()), 4)
        for p in ("needs", "information", "social", "etiquette"):
            dp = d[d.purpose == p]
            if len(dp):
                r[f"top3_{p}"] = round(float(dp.top3.mean()), 4)
        summ.append(r)
    summ = pd.DataFrame(summ).sort_values("top3", ascending=False)
    summ.to_csv(os.path.join(a.out, "e3_summary.csv"), index=False)

    by_cond = per.groupby(["method", "condition"]).agg(n=("case_id", "count"), top1=("top1", "mean"),
                                                       top3=("top3", "mean")).reset_index()
    by_cond.to_csv(os.path.join(a.out, "e3_by_condition.csv"), index=False)

    noisy = per[per.condition.isin(["wrong_label", "wrong_pick"])]
    if len(noisy):
        rec = noisy.groupby(["method", "recoverable"]).agg(n=("case_id", "count"), top1=("top1", "mean"),
                                                           top3=("top3", "mean")).reset_index()
        rec.to_csv(os.path.join(a.out, "e3_noise_recoverable.csv"), index=False)
    else:
        rec = pd.DataFrame()

    # paired differences against the retrieval baseline and the template floor, per condition
    diffs = []
    wide = {k: per.pivot_table(index="case_id", columns="method", values=k) for k in ("top1", "top3")}
    base = [b for b in ("embed", "template", "prior") if b in set(per.method)]
    for x in sorted(set(per.method)):
        for y in base:
            if x == y:
                continue
            for k, w in wide.items():
                mean, ci = paired(w[x].values, w[y].values, rng)
                diffs.append({"a": x, "b": y, "metric": k, "a_minus_b": mean,
                              "ci_lo": ci[0], "ci_hi": ci[1], "n": len(w)})
                for cond in CONDITIONS:
                    ids = per[per.condition == cond].case_id.unique()
                    wc = w.loc[w.index.intersection(ids)]
                    mean, ci = paired(wc[x].values, wc[y].values, rng)
                    diffs.append({"a": x, "b": y, "metric": f"{k}_{cond}", "a_minus_b": mean,
                                  "ci_lo": ci[0], "ci_hi": ci[1], "n": len(wc)})
    diffs = pd.DataFrame(diffs, columns=["a", "b", "metric", "a_minus_b", "ci_lo", "ci_hi", "n"])
    diffs.to_csv(os.path.join(a.out, "e3_paired_differences.csv"), index=False)

    L = ["# E3: from selected objects to the intended message", "",
         f"{per.case_id.nunique()} cases ({len(bank)} intents x {len(CONDITIONS)} conditions), "
         f"methods: {', '.join(sorted(set(per.method)))}.", "",
         "## Summary (top-1 = offered first, top-3 = on the first screen of candidate messages)", "",
         summ.to_markdown(index=False), "", "## By condition", "", by_cond.to_markdown(index=False), "",
         "## Paired differences vs the baselines", "",
         diffs[diffs.metric.isin(["top1", "top3"])].to_markdown(index=False), ""]
    open(os.path.join(a.out, "E3_REPORT.md"), "w").write("\n".join(L) + "\n")
    print(summ.to_string(index=False))
    print("\nwrote", a.out)


if __name__ == "__main__":
    main()
