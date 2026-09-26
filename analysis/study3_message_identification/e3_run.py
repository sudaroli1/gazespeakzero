"""
E3, step 2: every method proposes messages for every case.

    python e3_run.py --bank intent_bank.json --cases cases.jsonl --out e3_outputs \
        --methods template prior embed lm_rank_qwen1.5b lm_gen_qwen1.5b [--limit 8]

Method output is one JSON line per (method, case):
  ranking methods -> "ranked": the intent ids, best first
  generative      -> "text":   the message the model wrote (mapped to intents when scoring)

Resumable: a (method, case) already in the file is skipped.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import time

MODELS = {                                   # short name -> HF id (all open, non-gated)
    "qwen1.5b": "Qwen/Qwen2.5-1.5B-Instruct",
    "qwen3b": "Qwen/Qwen2.5-3B-Instruct",
    "smol1.7b": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
    "phi3.5": "microsoft/Phi-3.5-mini-instruct",
}
EMBED_ID = "sentence-transformers/all-MiniLM-L6-v2"
SYSTEM = ("You help a person with severe motor impairment who cannot speak. They choose objects "
          "they can see, and you say the sentence they most likely mean, in the first person.")


def user_prompt(case):
    objs = ", ".join(case["objects_shown"])
    return (f"Room: {case['room']}. The person selected, in this order: {objs}.\n"
            "Write the single short sentence they most likely want to say. Reply with the sentence only.")


NEUTRAL_PROMPT = "They want to say: "        # for the PMI calibration of lm_pmi_*


def choice_prompt(case, bank):
    """In-context multiple choice: the model sees every candidate message and picks three."""
    lines = "\n".join(f"{i + 1}. {b['utterance']}" for i, b in enumerate(bank))
    objs = ", ".join(case["objects_shown"])
    return (f"A person who cannot speak is in a {case['room']}. Using an eye-gaze board they selected, "
            f"in this order: {objs}.\n\nWhich of these messages did they most likely mean?\n\n{lines}\n\n"
            "Answer with the three most likely numbers, best first, separated by commas. Numbers only.")


def rank_prompt(case):
    objs = ", ".join(case["objects_shown"])
    return f"A person in a {case['room']} pointed at: {objs}. They want to say: "


def load_cases(path, limit=None):
    rows = [json.loads(l) for l in open(path)]
    if limit:                                  # dry run: spread over the conditions
        by = collections.defaultdict(list)
        for r in rows:
            by[r["condition"]].append(r)
        rows, i = [], 0
        while len(rows) < min(limit, sum(len(v) for v in by.values())):
            for c in list(by):
                if by[c] and len(rows) < limit:
                    rows.append(by[c].pop(0))
            i += 1
    return rows


# ---------------------------------------------------------------- baselines
def run_template(cases, bank, emit):
    for c in cases:
        objs = c["objects_shown"]
        text = "I want " + (" and ".join(objs) if len(objs) < 3 else ", ".join(objs[:-1]) + " and " + objs[-1]) + "."
        emit("template", c, {"text": text}, 0.0)


def run_prior(cases, bank, emit):
    """No vision, no LM: rank intents by how many of the shown objects they contain, ties
    broken by how common the intent's own objects are elsewhere in the bank (leave-one-out)."""
    freq = collections.Counter(o for b in bank for o in b["objects"])
    pop = {b["id"]: sum(freq[o] - 1 for o in b["objects"]) for b in bank}
    for c in cases:
        shown = set(c["objects_shown"])
        t0 = time.time()
        scored = sorted(bank, key=lambda b: (-len(shown & set(b["objects"])), -pop[b["id"]], b["id"]))
        emit("prior", c, {"ranked": [b["id"] for b in scored[:10]]}, time.time() - t0)


def run_embed(cases, bank, emit, device):
    from sentence_transformers import SentenceTransformer, util
    m = SentenceTransformer(EMBED_ID, device=device)
    texts = [b["utterance"] for b in bank]
    E = m.encode(texts, convert_to_tensor=True, normalize_embeddings=True)
    for c in cases:
        t0 = time.time()
        q = m.encode(f"in the {c['room']}: " + ", ".join(c["objects_shown"]),
                     convert_to_tensor=True, normalize_embeddings=True)
        sims = util.cos_sim(q, E)[0].cpu().numpy()
        order = sims.argsort()[::-1][:10]
        emit("embed", c, {"ranked": [bank[i]["id"] for i in order]}, time.time() - t0)
    del m


def _free():
    import gc
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass


# ---------------------------------------------------------------- language models
def load_lm(short, device):
    """Built-in implementations only: a model's own downloaded code goes stale against
    newer transformers (Phi-3.5's did, in the cache API)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    mid = MODELS[short]
    tok = AutoTokenizer.from_pretrained(mid)
    dt = torch.float16 if device == "cuda" else torch.float32
    try:
        model = AutoModelForCausalLM.from_pretrained(mid, dtype=dt)      # transformers >= 4.56
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(mid, torch_dtype=dt)
    model = model.to(device).eval()
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    return tok, model


def score_candidates(tok, model, device, prompt, cands, batch=20):
    """Mean token log-likelihood of each candidate continuation, given the prompt."""
    import torch
    p_ids = tok(prompt, return_tensors="pt").input_ids[0]
    scores = []
    for i in range(0, len(cands), batch):
        seqs = [torch.cat([p_ids, tok(x, return_tensors="pt", add_special_tokens=False).input_ids[0]])
                for x in cands[i:i + batch]]
        n = max(len(s) for s in seqs)
        inp = torch.full((len(seqs), n), tok.pad_token_id)
        att = torch.zeros((len(seqs), n), dtype=torch.long)
        for j, s in enumerate(seqs):
            inp[j, :len(s)], att[j, :len(s)] = s, 1
        inp, att = inp.to(device), att.to(device)
        with torch.no_grad():
            logits = model(input_ids=inp, attention_mask=att, use_cache=False).logits.float().log_softmax(-1)
        for j, s in enumerate(seqs):
            lp = logits[j, torch.arange(len(p_ids) - 1, len(s) - 1), s[len(p_ids):].to(device)]
            scores.append(float(lp.mean()))
    return scores


def run_lm_rank(cases, bank, emit, device, short, pmi=False):
    """Rank the candidate messages by log-likelihood given the objects.

    pmi=True subtracts each candidate's likelihood under a neutral prompt (Holtzman et al.
    2021): without it, ranking rewards sentences the model likes anyway ("surface form
    competition") rather than sentences that fit the objects."""
    import torch
    tok, model = load_lm(short, device)
    cands = [b["utterance"] for b in bank]
    ids = [b["id"] for b in bank]
    name = f"lm_{'pmi' if pmi else 'rank'}_{short}"
    base = score_candidates(tok, model, device, NEUTRAL_PROMPT, cands) if pmi else None
    for c in cases:
        t0 = time.time()
        sc = score_candidates(tok, model, device, rank_prompt(c), cands)
        if pmi:
            sc = [a - b for a, b in zip(sc, base)]
        if device == "cuda":
            torch.cuda.synchronize()
        order = sorted(range(len(cands)), key=lambda i: -sc[i])[:10]
        emit(name, c, {"ranked": [ids[i] for i in order]}, time.time() - t0)
    del model
    _free()


def run_lm_choice(cases, bank, emit, device, short):
    """In-context multiple choice: the model sees all candidates and answers with three numbers."""
    import re as _re

    import torch
    tok, model = load_lm(short, device)
    ids = [b["id"] for b in bank]
    empty = 0
    for i, c in enumerate(cases):
        msgs = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": choice_prompt(c, bank)}]
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        x = tok(text, return_tensors="pt").to(device)
        t0 = time.time()
        with torch.no_grad():
            out = model.generate(**x, max_new_tokens=16, do_sample=False, pad_token_id=tok.pad_token_id)
        if device == "cuda":
            torch.cuda.synchronize()
        raw = tok.decode(out[0, x["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        picks, seen = [], set()
        for m in _re.findall(r"\d+", raw):
            k = int(m) - 1
            if 0 <= k < len(ids) and k not in seen:
                seen.add(k)
                picks.append(ids[k])
        empty += not picks
        if i < 3:
            print(f"  {short} choice: {c['objects_shown']} -> {raw!r} -> {picks[:3]}", flush=True)
        emit(f"lm_choice_{short}", c, {"ranked": picks[:10], "raw": raw}, time.time() - t0)
    print(f"  {short}: {empty} of {len(cases)} answers had no usable number", flush=True)
    del model
    _free()


def run_lm_gen(cases, bank, emit, device, short):
    import torch
    tok, model = load_lm(short, device)
    for i, c in enumerate(cases):
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_prompt(c)}]
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        x = tok(text, return_tensors="pt").to(device)
        t0 = time.time()
        with torch.no_grad():
            out = model.generate(**x, max_new_tokens=32, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
        if device == "cuda":
            torch.cuda.synchronize()
        gen = tok.decode(out[0, x["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        gen = gen.split("\n")[0].strip().strip('"')
        if i < 3:
            print(f"  {short} gen: {c['case_id']} {c['objects_shown']} -> {gen!r}", flush=True)
        emit(f"lm_gen_{short}", c, {"text": gen}, time.time() - t0)
    del model
    _free()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default="intent_bank.json")
    ap.add_argument("--cases", default="cases.jsonl")
    ap.add_argument("--out", default="e3_outputs")
    ap.add_argument("--methods", nargs="+", default=["template", "prior", "embed"])
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bank = json.load(open(a.bank))
    cases = load_cases(a.cases, a.limit)
    path = os.path.join(a.out, "outputs.dry.jsonl" if a.limit else "outputs.jsonl")

    done = set()
    if os.path.exists(path):                     # drop a half-written last line
        good = []
        for l in open(path):
            try:
                o = json.loads(l)
                done.add((o["method"], o["case_id"]))
                good.append(l if l.endswith("\n") else l + "\n")
            except json.JSONDecodeError:
                pass
        open(path, "w").writelines(good)
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        device = "cpu"
    print(f"{len(cases)} cases | {len(bank)} intents | device {device} | methods {a.methods}", flush=True)

    f = open(path, "a")
    n = collections.Counter()

    def emit(method, case, payload, secs):
        f.write(json.dumps({"method": method, "case_id": case["case_id"], "intent_id": case["intent_id"],
                            "condition": case["condition"], "seconds": round(secs, 4), **payload}) + "\n")
        f.flush()
        n[method] += 1
        if n[method] % 50 == 0:
            print(f"  {method}: {n[method]} cases", flush=True)

    for m in a.methods:
        todo = [c for c in cases if (m, c["case_id"]) not in done]
        if not todo:
            print(f"{m}: already done")
            continue
        print(f"{m}: {len(todo)} cases ...", flush=True)
        t0 = time.time()
        try:
            if m == "template":
                run_template(todo, bank, emit)
            elif m == "prior":
                run_prior(todo, bank, emit)
            elif m == "embed":
                run_embed(todo, bank, emit, device)
            elif m.startswith("lm_rank_"):
                run_lm_rank(todo, bank, emit, device, m[len("lm_rank_"):])
            elif m.startswith("lm_pmi_"):
                run_lm_rank(todo, bank, emit, device, m[len("lm_pmi_"):], pmi=True)
            elif m.startswith("lm_choice_"):
                run_lm_choice(todo, bank, emit, device, m[len("lm_choice_"):])
            elif m.startswith("lm_gen_"):
                run_lm_gen(todo, bank, emit, device, m[len("lm_gen_"):])
            else:
                raise SystemExit(f"unknown method {m}")
        except Exception as e:                      # keep going: the rest of the run is still useful
            import traceback
            traceback.print_exc()
            print(f"!! {m} FAILED ({type(e).__name__}: {e}); continuing with the other methods", flush=True)
            _free()
            continue
        print(f"{m}: done in {time.time() - t0:.0f} s", flush=True)
    f.close()


if __name__ == "__main__":
    main()
