"""
E2, step 3: score every method's ranked items against LVIS ground truth.

    python e2_score.py --set e2_set --outputs e2_outputs/outputs.jsonl --out e2_results

Matching. Each proposed item is mapped to at most one LVIS category by
aac_vocab.Matcher, which uses LVIS names and synonyms plus a fixed alias table
('fridge', 'tv', 'cell phone', ...). The same rules apply to every method. If a
method names the same category twice, only the first is kept.

Ground truth. LVIS is federated: per image, some categories are verified present
(pos), some verified absent (neg), and the rest are unknown. The primary scoring
extends both sets with COCO's exhaustive labels for its 80 classes (pos_x, neg_x;
see e2_build_set.py for the safeguards). LVIS-only figures are a pre-stated
check. Each item is:

    correct        its category is verified present
    wrong          its category is verified absent
    unverifiable   no LVIS category, or not checked in this photo

Lenient: an item also counts as correct if a category in the same small
equivalence group is present (aac_vocab.LENIENT_GROUPS, e.g. table ~
dining_table).

Per image, at K = 3, 6, 12 (items are shown 3 at a time, so K = 3 is one screen):
  precision@K   correct / (correct + wrong) among the top K; NaN if none verifiable
  verifiable@K  (correct + wrong) / K; an empty or short list counts against it
  recall@K      share of AAC-vocabulary objects present in the photo named in the top K
  hit@3         at least one strictly correct item on the first screen
                (hit_lenient@3 is also reported)

Only scenes that every method covered are scored. Means are over scenes, with
95% bootstrap CIs. Differences between methods use a paired bootstrap over the
same resampled scenes. Pooled precision (all items together) is reported as
well. Also writes a blinded audit sheet.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aac_vocab import Matcher  # noqa: E402

KS = [3, 6, 12]
N_BOOT = 5000
SEED = 0
ORDER = ["static", "clip", "blip2_orig", "blip2_caption", "blip2_qa", "qwen_vl"]
PAIRS = [("qwen_vl", "static"), ("qwen_vl", "clip"), ("clip", "static"), ("qwen_vl", "blip2_orig"), ("clip", "blip2_orig"),
         ("blip2_caption", "static"), ("blip2_qa", "static"), ("qwen_vl", "blip2_caption"), ("qwen_vl", "blip2_qa"),
         ("clip", "blip2_caption"), ("clip", "blip2_qa")]


def boot(v, rng):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) < 2:
        return (np.nan, np.nan)
    m = v[rng.integers(0, len(v), (N_BOOT, len(v)))].mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def paired(a, b, rng):
    """mean(a - b) over scenes where both are finite, with a bootstrap CI."""
    ok = np.isfinite(a) & np.isfinite(b)
    d = (a - b)[ok]
    if len(d) < 2:
        return np.nan, (np.nan, np.nan), int(ok.sum())
    m = d[rng.integers(0, len(d), (N_BOOT, len(d)))].mean(1)
    return float(d.mean()), (float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))), int(ok.sum())


def norm_item(s: str) -> str:
    return " ".join("".join(ch for ch in s.lower() if ch.isalnum() or ch == " ").split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="e2_set")
    ap.add_argument("--outputs", default="e2_outputs/outputs.jsonl")
    ap.add_argument("--out", default="e2_results")
    ap.add_argument("--audit-n", type=int, default=50)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(SEED)

    scenes = {r["image_id"]: r for r in (json.loads(l) for l in open(os.path.join(a.set, "set.jsonl")))}
    vocab = json.load(open(os.path.join(a.set, "vocab.json")))
    m = Matcher(vocab["categories"])
    vset = set(vocab["vocab_ids"])

    outs = []
    for l in open(a.outputs):
        try:
            outs.append(json.loads(l))
        except json.JSONDecodeError:
            pass
    # keep the last record per (method, image); score only scenes every method covered
    last = {(o["method"], o["image_id"]): o for o in outs if o["image_id"] in scenes}
    methods = sorted({k[0] for k in last}, key=lambda x: ORDER.index(x) if x in ORDER else 99)
    common = set.intersection(*[{i for (mm, i) in last if mm == meth} for meth in methods])
    cover = {meth: sum(1 for (mm, _) in last if mm == meth) for meth in methods}
    print("scenes per method:", cover, "| scored (common):", len(common), flush=True)

    item_rows, img_rows = [], []
    for (meth, iid), o in sorted(last.items()):
        if iid not in common:
            continue
        s = scenes[iid]
        pos, neg = set(s.get("pos_x", s["pos"])), set(s.get("neg_x", s["neg"]))
        pos_l, neg_l = set(s["pos"]), set(s["neg"])
        rel = pos & vset
        seen, cats = set(), []
        for it in o["items"]:
            c = m.match(it)
            if c is not None and c in seen:
                continue                                    # same category named twice: keep the first
            if c is not None:
                seen.add(c)
            st = "correct" if c in pos else "wrong" if c in neg else "unverifiable"
            stl = "correct" if c in pos_l else "wrong" if c in neg_l else "unverifiable"
            len_ok = st == "correct" or (c is not None and bool(m.group.get(c, set()) & pos))
            cats.append((c, st, len_ok, stl, it))
        for rank, (c, st, len_ok, stl, it) in enumerate(cats, 1):
            item_rows.append({"method": meth, "image_id": iid, "room": s["room"], "rank": rank, "item": it,
                              "category": m.id2name.get(c) if c is not None else None, "status": st,
                              "lenient_correct": bool(len_ok), "status_lvis_only": stl})
        r = {"method": meth, "image_id": iid, "room": s["room"], "seconds": o.get("seconds", np.nan),
             "n_items": len(cats), "n_relevant_present": len(rel)}
        for K in KS:
            top = cats[:K]
            corr = sum(x[1] == "correct" for x in top)
            wrong = sum(x[1] == "wrong" for x in top)
            r[f"correct@{K}"], r[f"wrong@{K}"] = corr, wrong
            r[f"precision@{K}"] = corr / (corr + wrong) if corr + wrong else np.nan
            lc = sum(x[2] for x in top)
            lw = sum(x[1] == "wrong" and not x[2] for x in top)
            r[f"precision_lenient@{K}"] = lc / (lc + lw) if lc + lw else np.nan
            r[f"verifiable@{K}"] = (corr + wrong) / K
            cl, wl = sum(x[3] == "correct" for x in top), sum(x[3] == "wrong" for x in top)
            r[f"precision_lvis_only@{K}"] = cl / (cl + wl) if cl + wl else np.nan
            r[f"verifiable_lvis_only@{K}"] = (cl + wl) / K
            named = {x[0] for x in top if x[0] is not None}
            named_grp = set().union(*[m.group.get(c, {c}) for c in named]) if named else set()
            r[f"recall@{K}"] = len(rel & named) / len(rel) if rel else np.nan
            r[f"recall_lenient@{K}"] = len(rel & named_grp) / len(rel) if rel else np.nan
        r["hit@3"] = float(any(x[1] == "correct" for x in cats[:3]))
        r["hit_lenient@3"] = float(any(x[2] for x in cats[:3]))
        img_rows.append(r)
    items, imgs = pd.DataFrame(item_rows), pd.DataFrame(img_rows)
    items.to_csv(os.path.join(a.out, "e2_items.csv"), index=False)
    imgs.to_csv(os.path.join(a.out, "e2_per_image.csv"), index=False)

    metrics = ([f"{p}@{K}" for K in KS for p in ("precision", "precision_lenient", "verifiable", "recall",
                                                 "recall_lenient", "precision_lvis_only", "verifiable_lvis_only")]
               + ["hit@3", "hit_lenient@3"])
    summ = []
    for meth in methods:
        d = imgs[imgs.method == meth]
        row = {"method": meth, "scenes": len(d), "median_seconds": float(np.nanmedian(d.seconds)),
               "mean_items": float(d.n_items.mean()), "short_lists(<3 items)": int((d.n_items < 3).sum())}
        for k in metrics:
            row[k] = float(np.nanmean(d[k])) if d[k].notna().any() else np.nan
            row[k + "_n"] = int(d[k].notna().sum())
            row[k + "_ci"] = boot(d[k].values, rng)
        for K in KS:
            c_, w_ = d[f"correct@{K}"].sum(), d[f"wrong@{K}"].sum()
            row[f"pooled_precision@{K}"] = c_ / (c_ + w_) if c_ + w_ else np.nan
        summ.append(row)
    summ = pd.DataFrame(summ)
    summ.to_csv(os.path.join(a.out, "e2_summary.csv"), index=False)

    wide = {k: imgs.pivot(index="image_id", columns="method", values=k) for k in ("hit@3", "recall@6", "precision@3")}
    diffs = []
    for x, y in PAIRS:
        if x in methods and y in methods:
            for k, w in wide.items():
                mean, ci, n = paired(w[x].values.astype(float), w[y].values.astype(float), rng)
                diffs.append({"a": x, "b": y, "metric": k, "a_minus_b": mean, "ci_lo": ci[0], "ci_hi": ci[1], "n": n})
    diffs = pd.DataFrame(diffs, columns=["a", "b", "metric", "a_minus_b", "ci_lo", "ci_hi", "n"])
    diffs.to_csv(os.path.join(a.out, "e2_paired_differences.csv"), index=False)
    by_room = imgs.groupby(["method", "room"]).agg(n=("image_id", "count"), precision3=("precision@3", "mean"),
                                                   recall6=("recall@6", "mean"), hit3=("hit@3", "mean")).reset_index()
    by_room.to_csv(os.path.join(a.out, "e2_by_room.csv"), index=False)
    um = items[items.category.isna()].assign(it=lambda z: z["item"].map(norm_item))
    unmatched = um.groupby("method").it.agg(lambda z: ", ".join(f"{k} ({v})" for k, v in z.value_counts().head(15).items())) \
        if len(um) else pd.Series(dtype=str)
    unmatched.to_csv(os.path.join(a.out, "e2_top_unmatched_items.csv"))

    # blinded audit sheet: normalised items, random method codes, item_uid join key
    rs = random.Random(SEED)
    ids = sorted(common)
    rs.shuffle(ids)
    aud = items[items.image_id.isin(ids[: a.audit_n]) & (items["rank"] <= 6)].copy()
    aud["item_norm"] = aud["item"].map(norm_item)
    aud = aud[aud.item_norm != ""]
    codes_list = [f"M{i + 1}" for i in range(len(methods))]
    rs.shuffle(codes_list)
    codes = dict(zip(methods, codes_list))
    uniq = aud.drop_duplicates(["image_id", "item_norm"])[["image_id", "item_norm"]].reset_index(drop=True)
    uniq = uniq.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    uniq["item_uid"] = [f"U{i:04d}" for i in range(len(uniq))]
    uniq["url"] = uniq.image_id.map(lambda i: scenes[i]["url"])
    sheet = uniq.sort_values(["image_id", "item_uid"])[["item_uid", "image_id", "url", "item_norm"]].rename(columns={"item_norm": "item"})
    sheet["is_it_in_the_photo(Y/N)"] = ""
    sheet["would_a_patient_here_plausibly_want_or_mention_it(Y/N)"] = ""
    sheet.to_csv(os.path.join(a.out, "audit_sheet.csv"), index=False)
    key = aud.merge(uniq[["image_id", "item_norm", "item_uid"]], on=["image_id", "item_norm"])
    key["method_code"] = key.method.map(codes)
    os.makedirs(os.path.join(a.out, "audit_key_private"), exist_ok=True)
    key[["item_uid", "image_id", "item", "method_code", "rank"]].to_csv(
        os.path.join(a.out, "audit_key_private", "audit_key_DO_NOT_OPEN_BEFORE_RATING.csv"), index=False)
    json.dump(codes, open(os.path.join(a.out, "audit_key_private", "method_codes.json"), "w"))

    f = lambda v, ci=None: ("n/a" if v is None or not np.isfinite(v) else f"{v:.3f}") + (
        f" ({ci[0]:.3f}–{ci[1]:.3f})" if ci is not None and np.isfinite(ci[0]) else "")
    rooms = imgs.drop_duplicates("image_id").room.value_counts()
    L = ["# E2: how well does each method name the useful objects in an everyday scene?", "",
         f"{len(common)} scenes scored (LVIS v1 val / COCO 2017), all methods on the same scenes; rooms: "
         + ", ".join(f"{k} {v}" for k, v in rooms.items()) + f". Scenes per method before intersecting: {cover}. "
         f"AAC vocabulary: {len(vset)} LVIS categories"
         + (f" ({', '.join(vocab['missing'])} not in this LVIS release)" if vocab["missing"] else "") + ".", "",
         "## First screen (top 3 items)", "",
         "| Method | precision@3 | pooled | lenient | verifiable@3 | recall@3 | hit@3 | hit lenient | median s/scene | lists < 3 items |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for _, x in summ.iterrows():
        L.append(f"| {x.method} | {f(x['precision@3'], x['precision@3_ci'])} (n={x['precision@3_n']}) | {f(x['pooled_precision@3'])} | "
                 f"{f(x['precision_lenient@3'])} | {f(x['verifiable@3'])} | {f(x['recall@3'], x['recall@3_ci'])} | "
                 f"{f(x['hit@3'], x['hit@3_ci'])} | {f(x['hit_lenient@3'])} | {x.median_seconds:.2f} | {x['short_lists(<3 items)']} |")
    L += ["", "LVIS-only check (no COCO extension), precision@3 / verifiable@3: "
          + "; ".join(f"{x.method} {f(x['precision_lvis_only@3'])} / {f(x['verifiable_lvis_only@3'])}" for _, x in summ.iterrows()),
          "", "## Deeper lists", "",
          "| Method | precision@6 | recall@6 | recall lenient@6 | precision@12 | recall@12 | verifiable@12 |",
          "|---|---|---|---|---|---|---|"]
    for _, x in summ.iterrows():
        L.append(f"| {x.method} | {f(x['precision@6'])} | {f(x['recall@6'], x['recall@6_ci'])} | {f(x['recall_lenient@6'])} | "
                 f"{f(x['precision@12'])} | {f(x['recall@12'])} | {f(x['verifiable@12'])} |")
    L += ["", "## Paired differences (same scenes; 95% bootstrap CI)", "", "| A − B | metric | difference | n |", "|---|---|---|---|"]
    for _, x in diffs.iterrows():
        L.append(f"| {x.a} − {x.b} | {x.metric} | {f(x.a_minus_b, (x.ci_lo, x.ci_hi))} | {x.n} |")
    L += ["", "## By room", "", "| Method | Room | n | precision@3 | recall@6 | hit@3 |", "|---|---|---|---|---|---|"]
    for _, x in by_room.iterrows():
        L.append(f"| {x.method} | {x.room} | {x.n} | {f(x.precision3)} | {f(x.recall6)} | {f(x.hit3)} |")
    st = items.groupby("method").status.value_counts(normalize=True).unstack().fillna(0)
    L += ["", "## Item status (all ranks)", "", "```", st.round(3).to_string(), "```", "",
          "## Most frequent items that matched no LVIS category", "", "```", unmatched.to_string(), "```", "",
          "## Examples (first 3 audit scenes)", "", "```"]
    for iid in ids[:3]:
        L.append(f"scene {iid} ({scenes[iid]['room']}), AAC objects present: "
                 + ", ".join(m.id2name[c] for c in sorted(set(scenes[iid].get('pos_x', scenes[iid]['pos'])) & vset)))
        for meth in methods:
            it = items[(items.image_id == iid) & (items.method == meth)].sort_values("rank")
            L.append(f"  {meth:11s}: " + ", ".join(f"{r.item}[{r.status[0]}]" for r in it.head(6).itertuples()))
    L += ["```", "", "Status letters: c = correct, w = wrong (verified absent), u = unverifiable.", "",
          "Audit: rate `audit_sheet.csv` (two Y/N columns). The method key is in `audit_key_private/`: "
          "do not open it, or give it to the rater, before rating is finished."]
    open(os.path.join(a.out, "E2_REPORT.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
