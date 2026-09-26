"""
E2, step 4: score the human audit and compare it with the automatic (LVIS+COCO) labels.

    python e2_audit_score.py --rated results/audit_rater1.xlsx [results/audit_rater2.xlsx] \
        --key results/audit_key_private/audit_key_DO_NOT_OPEN_BEFORE_RATING.csv \
        --codes results/audit_key_private/method_codes.json \
        --items results/e2_items.csv --out results/audit

The FIRST file given is the one scored. Any further file is compared against it:
with --review the comparison is reported as a review (which answers a second person
changed), not as independent inter-rater agreement.

Outputs
-------
audit_summary.csv       per method: human precision@K, useful@K, hit@3, useful-hit@3, with
                        bootstrap CIs over the audited scenes
audit_vs_labels.csv     where the automatic labels have a verdict: agreement, and the
                        automatic status of the items they could not check
audit_rater_agreement.csv   raw agreement and Cohen's kappa per column (only with 2+ files)
audit_generic_terms.csv sensitivity: the same table with non-pointable generic names
                        (area, object, room names) removed from every method's list
AUDIT_REPORT.md
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

SEED, N_BOOT, KS = 0, 5000, (3, 6)
ORDER = ["static", "clip", "blip2_orig", "blip2_caption", "blip2_qa", "qwen_vl"]
GENERIC = {"area", "object", "room", "bathroom", "bedroom", "kitchen", "living room", "dining room",
           "restaurant", "furniture", "group of people", "hotel room", "sitting room", "scene", "space"}
COLS = ["scene", "photo", "item", "D", "E", "notes", "item_uid", "image_id"]


def read_rated(path):
    d = pd.read_excel(path, sheet_name="Rating")
    d.columns = COLS
    for c in ("D", "E"):
        d[c] = d[c].astype("string").str.strip().str.upper().replace({"": pd.NA})
    return d[["item_uid", "image_id", "item", "D", "E"]]


def boot(v, rng):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) < 2:
        return (np.nan, np.nan)
    b = v[rng.integers(0, len(v), (N_BOOT, len(v)))].mean(1)
    return round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)


def kappa(x, y):
    x, y = np.asarray(x), np.asarray(y)
    ok = pd.notna(x) & pd.notna(y)
    x, y = x[ok], y[ok]
    if len(x) == 0:
        return np.nan, np.nan, 0
    po = float((x == y).mean())
    labels = sorted(set(x) | set(y))
    pe = sum((x == l).mean() * (y == l).mean() for l in labels)
    k = (po - pe) / (1 - pe) if pe < 1 else np.nan
    return round(po, 4), (round(float(k), 4) if k == k else np.nan), int(len(x))


def per_method_table(rated, key, rng, drop_generic=False):
    """rated: item_uid -> D,E. key: item_uid, method, rank (rank is per method and scene)."""
    d = key.merge(rated[["item_uid", "D", "E"]], on="item_uid", how="left")
    d["in_photo"] = (d.D == "Y")
    d["useful"] = d.in_photo & (d.E == "Y")
    if drop_generic:
        d = d[~d.item.str.lower().isin(GENERIC)].copy()
        d["rank"] = d.groupby(["method", "image_id"])["rank"].rank(method="first").astype(int)
    rows = []
    for meth in [m for m in ORDER if m in set(d.method)]:
        dm = d[d.method == meth]
        r = {"method": meth, "scenes": dm.image_id.nunique(), "items_rated": len(dm)}
        for K in KS:
            top = dm[dm["rank"] <= K]
            g = top.groupby("image_id")
            prec = (g.in_photo.sum() / K)          # denominator K: a short list is penalised
            use = (g.useful.sum() / K)
            r[f"human_precision@{K}"] = round(float(prec.mean()), 4)
            r[f"human_precision@{K}_ci"] = boot(prec.values, rng)
            r[f"useful@{K}"] = round(float(use.mean()), 4)
            r[f"useful@{K}_ci"] = boot(use.values, rng)
            if K == 3:
                hit = g.in_photo.any().astype(float)
                uhit = g.useful.any().astype(float)
                r["human_hit@3"] = round(float(hit.mean()), 4)
                r["human_hit@3_ci"] = boot(hit.values, rng)
                r["useful_hit@3"] = round(float(uhit.mean()), 4)
                r["useful_hit@3_ci"] = boot(uhit.values, rng)
        rows.append(r)
    return pd.DataFrame(rows), d


PAIRS = [("qwen_vl", "clip"), ("qwen_vl", "static"), ("clip", "static"), ("qwen_vl", "blip2_qa"),
         ("clip", "blip2_qa"), ("blip2_qa", "static"), ("qwen_vl", "blip2_orig")]


def paired_table(joined, rng):
    """Paired differences between methods on the audited scenes."""
    per = {}
    for meth, dm in joined.groupby("method"):
        g3, g6 = dm[dm["rank"] <= 3].groupby("image_id"), dm[dm["rank"] <= 6].groupby("image_id")
        per[meth] = pd.DataFrame({"human_precision@3": g3.in_photo.sum() / 3,
                                  "useful@3": g3.useful.sum() / 3,
                                  "human_hit@3": g3.in_photo.any().astype(float),
                                  "useful_hit@3": g3.useful.any().astype(float),
                                  "human_precision@6": g6.in_photo.sum() / 6,
                                  "useful@6": g6.useful.sum() / 6})
    rows = []
    for x, y in PAIRS:
        if x not in per or y not in per:
            continue
        for k in per[x].columns:
            u, v = per[x][k].align(per[y][k], join="inner")
            d = (u - v).values.astype(float)
            b = d[rng.integers(0, len(d), (N_BOOT, len(d)))].mean(1)
            rows.append({"a": x, "b": y, "metric": k, "a_minus_b": round(float(d.mean()), 4),
                         "ci_lo": round(float(np.percentile(b, 2.5)), 4),
                         "ci_hi": round(float(np.percentile(b, 97.5)), 4), "n_scenes": len(d)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rated", nargs="+", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--codes", required=True)
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", default="results/audit")
    ap.add_argument("--review", action="store_true",
                    help="the extra file(s) are a second pass over the same answers, not an "
                         "independent rating: report changes, and do not report kappa as reliability")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(SEED)

    raters = [read_rated(p) for p in a.rated]
    primary = raters[0]
    key = pd.read_csv(a.key)
    codes = {v: k for k, v in json.load(open(a.codes)).items()}
    key["method"] = key.method_code.map(codes)
    assert key.method.notna().all(), "unknown method code in the key"

    summ, joined = per_method_table(primary, key, rng)
    summ.to_csv(os.path.join(a.out, "audit_summary.csv"), index=False)
    gen, _ = per_method_table(primary, key, rng, drop_generic=True)
    gen.to_csv(os.path.join(a.out, "audit_generic_terms.csv"), index=False)

    diffs = paired_table(joined, rng)
    diffs.to_csv(os.path.join(a.out, "audit_paired_differences.csv"), index=False)

    # agreement with the automatic labels
    it = pd.read_csv(a.items)
    it["k"] = it.image_id.astype(str) + "|" + it.method + "|" + it["item"].str.lower()
    joined["k"] = joined.image_id.astype(str) + "|" + joined.method + "|" + joined["item"].str.lower()
    j = joined.merge(it[["k", "status"]].drop_duplicates("k"), on="k", how="left")
    rows = []
    for meth in [m for m in ORDER if m in set(j.method)]:
        dm = j[j.method == meth]
        ver = dm[dm.status.isin(["correct", "wrong"])]
        agree = (ver.in_photo == (ver.status == "correct"))
        unv = dm[dm.status == "unverifiable"]
        rows.append({"method": meth, "items": len(dm),
                     "label_verdict": len(ver), "agreement_with_labels": round(float(agree.mean()), 4) if len(ver) else np.nan,
                     "label_correct_human_N": int(((ver.status == "correct") & ~ver.in_photo).sum()),
                     "label_wrong_human_Y": int(((ver.status == "wrong") & ver.in_photo).sum()),
                     "unverifiable_items": len(unv),
                     "unverifiable_in_photo": round(float(unv.in_photo.mean()), 4) if len(unv) else np.nan,
                     "unverifiable_useful": round(float(unv.useful.mean()), 4) if len(unv) else np.nan})
    vs = pd.DataFrame(rows)
    vs.to_csv(os.path.join(a.out, "audit_vs_labels.csv"), index=False)

    # review or independent agreement
    ag = []
    if len(raters) > 1 and a.review:
        other = raters[1]
        m = primary.merge(other, on="item_uid", suffixes=("_p", "_o"))
        m = m.merge(key[["item_uid", "method"]], on="item_uid", how="left")
        rows = []
        for meth, g in list(m.groupby("method")) + [("ALL", m)]:
            inphoto = (g.D_p != g.D_o).sum()
            both_y = g[(g.D_p == "Y") & (g.D_o == "Y")]
            rows.append({"method": meth, "items": len(g), "in_photo_changed": int(inphoto),
                         "in_photo_changed_pct": round(100 * inphoto / max(1, len(g)), 2),
                         "useful_compared": len(both_y),
                         "useful_changed": int((both_y.E_p != both_y.E_o).sum())})
        pd.DataFrame(rows).to_csv(os.path.join(a.out, "audit_review_changes.csv"), index=False)
        ag = rows
    elif len(raters) > 1:
        for i, other in enumerate(raters[1:], start=2):
            m = primary.merge(other, on="item_uid", suffixes=("_1", f"_{i}"))
            for col in ("D", "E"):
                po, k, n = kappa(m[f"{col}_1"], m[f"{col}_{i}"])
                ag.append({"pair": f"1 vs {i}", "column": col, "n": n, "raw_agreement": po, "cohens_kappa": k})
        pd.DataFrame(ag).to_csv(os.path.join(a.out, "audit_rater_agreement.csv"), index=False)

    L = ["# E2 human audit (blinded)", "",
         f"Rater file(s): {', '.join(os.path.basename(p) for p in a.rated)}. "
         f"Primary rater: {os.path.basename(a.rated[0])}. "
         f"{primary.item_uid.nunique()} items over {key.image_id.nunique()} scenes.", "",
         "## Per method (human judgement, top items of each method)", "",
         summ.to_markdown(index=False), "",
         "- `human_precision@K`: share of the first K items that the rater could point to in the photo.",
         "- `useful@K`: share of the first K items that are both in the photo and something a person there might want or mention.",
         "- `human_hit@3` / `useful_hit@3`: at least one such item on the first screen.", "",
         "## Paired differences on the audited scenes", "",
         diffs.to_markdown(index=False), "",
         "## Sensitivity: generic names removed (area, object, room names)", "",
         gen.to_markdown(index=False), "",
         "## Human judgement vs the automatic LVIS+COCO labels", "",
         vs.to_markdown(index=False), ""]
    if ag:
        title = ("## Second-pass review (a second person went over the same answers; this is NOT "
                 "independent inter-rater agreement)" if a.review else "## Rater agreement")
        L += [title, "", pd.DataFrame(ag).to_markdown(index=False), ""]
    open(os.path.join(a.out, "AUDIT_REPORT.md"), "w").write("\n".join(L) + "\n")
    print(summ.to_string(index=False))
    print("\nwrote", a.out)


if __name__ == "__main__":
    main()
