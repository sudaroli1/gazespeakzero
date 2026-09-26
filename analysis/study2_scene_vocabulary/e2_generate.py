"""
E2, step 2: each method proposes a ranked list of up to 12 items for every scene.

    python e2_generate.py --set e2_set --out e2_outputs --methods static clip blip2_orig qwen_vl [--limit 5]

Methods
-------
static      No vision. The AAC-vocabulary items ranked by how often they occur
            in the OTHER scenes of the set (leave-one-out), using the same ground truth
            as the scoring. This is the best
            possible fixed, pre-written list, as Look to Speak would use, built
            with hindsight, so it is a generous baseline.
clip        CLIP ViT-L/14 (the original paper's scene model), used as it
            should be used: ranks every AAC-vocabulary item by image-text
            similarity to "a photo of a {item}." Closed vocabulary.
blip2_orig  The original GazeSpeakZero Stage 2, verbatim: BLIP-2 (OPT-2.7B)
            answers "What are the objects and areas visible in this scene?",
            the decoded text is split into words, stopwords and words of two
            letters or fewer are removed, and the first 12 unique words are kept.
blip2_caption  Fair BLIP-2 baseline 1: the same model with no text prompt, i.e. its
            native captioning mode (beam search, 3 beams). The caption is cut into
            noun phrases at commas, "and" and spatial words ("a kitchen with a
            stove and a sink" -> kitchen, stove, sink).
blip2_qa    Fair BLIP-2 baseline 2: the prompt format BLIP-2 was trained on,
            "Question: What objects are in this room? Answer:", same phrase parsing.
            Both variants strip the echoed prompt from the decoded text (under
            transformers 4.51 the decoded output starts with the prompt; in E2
            the verbatim original step returned only the echo for all 283 scenes).
qwen_vl     Qwen2.5-VL-3B-Instruct, a small open vision-language model, asked
            for a ranked comma-separated list (prompt below). Open vocabulary.

Output: one JSON line per (method, image) with the ranked items and the seconds
the method took for that image (GPU time where a GPU is used). Resumable: a
(method, image) pair already in the output file is skipped.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aac_vocab import canon  # noqa: E402

K_MAX = 12
QWEN_PROMPT = ("List the objects in this scene that a person here might ask for, use or talk about. "
               "Reply with only a comma-separated list of up to 12 short object names, most useful first.")
BLIP_PROMPT = "What are the objects and areas visible in this scene?"          # original, verbatim
BLIP_STOPWORDS = {                                                               # original, verbatim
    "a", "an", "the", "is", "are", "and", "of", "in", "on", "with", "this",
    "that", "to", "for", "at", "it", "its", "there", "scene", "image",
    "visible", "objects", "areas", "what",
}


BLIP_QA_PROMPT = "Question: What objects are in this room? Answer:"
_ING_NOUNS = ("ceiling|painting|paintings|clothing|building|buildings|ring|rings|string|wing|wings|bedding|"
              "icing|frosting|pudding|dressing|railing|lighting|seating|flooring|awning|earring|earrings|"
              "stuffing|wedding|spring|swing|king|thing|things|something|nothing|everything|ironing board|"
              "sling|filling|topping|toppings|siding|molding|moulding|outing|living|dining|sewing|washing|baking|cutting|"
              "shopping|rolling|frying|sleeping|running|walking|hearing|reading|drinking|changing|sitting room|"
              "dressing table|mixing|serving|measuring|boxing|parking|ping")
# split at punctuation, conjunctions, prepositions (longest first) and any "-ing" verb that is not a noun above
_SPLIT = re.compile(r"[,;.:!?\n]|\b(?:in front of|on top of|next to|there is|there are|and|with|on|in|at|near|"
                    r"beside|under|behind|by|including|is|are|has|have|their|his|her|its)\b"
                    r"|\b(?!(?:" + _ING_NOUNS + r")\b)[a-z]+ing\b")
_LEAD = re.compile(r"^(?:a|an|the|some|two|three|four|five|several|many|other|various|small|large|"
                   r"big|white|black|red|blue|green|wooden|old|\d+)\s+")


def phrase_items(text: str) -> list[str]:
    """Noun phrases from a BLIP-2 caption or answer, in order, without repeats."""
    items = []
    for ph in _SPLIT.split(text.lower()):
        ph = re.sub(r"[^a-z\s-]", " ", ph or "").strip()
        prev = None
        while ph and ph != prev:                  # strip leading articles / numbers / colours
            prev, ph = ph, _LEAD.sub("", ph).strip()
        if ph and len(ph) >= 2 and len(ph.split()) <= 4 and ph not in items and ph not in BLIP_STOPWORDS:
            items.append(ph)
    return items[:K_MAX]


def strip_prompt(decoded: str, prompt: str) -> str:
    d = decoded.strip()
    return d[len(prompt):].strip() if prompt and d.lower().startswith(prompt.lower()) else d


def load_set(d):
    rows = [json.loads(l) for l in open(os.path.join(d, "set.jsonl"))]
    vocab = json.load(open(os.path.join(d, "vocab.json")))
    rows = [r for r in rows if os.path.exists(os.path.join(d, "images", f"{r['image_id']}.jpg"))]
    return rows, vocab


def parse_list(text: str) -> list[str]:
    text = text.replace("\n", ",").replace(";", ",")
    items = []
    for t in text.split(","):
        t = re.sub(r"^\s*(\d+[\.\)]|[-*•])\s*", "", t).strip().strip(".").strip()
        if t and len(t) <= 40 and t.lower() not in [i.lower() for i in items]:
            items.append(t)
    return items[:K_MAX]


def run_static(rows, vocab, emit):
    vids = vocab["vocab_ids"]
    names = {i: canon(n) for i, n in zip(vids, vocab["vocab_names"])}
    count = collections.Counter()
    for r in rows:
        count.update(set(r.get("pos_x", r["pos"])) & set(vids))
    for r in rows:
        own = set(r.get("pos_x", r["pos"])) & set(vids)
        loo = {i: count[i] - (1 if i in own else 0) for i in vids}      # leave this image out
        ranked = sorted(vids, key=lambda i: (-loo[i], names[i]))[:K_MAX]
        emit("static", r, [names[i] for i in ranked], 0.0)


def run_clip(rows, d, vocab, emit, device):
    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor
    model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14").to(device).eval()
    proc = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")
    names = [canon(n) for n in vocab["vocab_names"]]
    with torch.no_grad():
        t = proc(text=[f"a photo of a {n}." for n in names], return_tensors="pt", padding=True).to(device)
        tf = model.get_text_features(**t)
        tf = tf / tf.norm(dim=-1, keepdim=True)
        for r in rows:
            img = Image.open(os.path.join(d, "images", f"{r['image_id']}.jpg")).convert("RGB")
            t0 = time.time()
            x = proc(images=img, return_tensors="pt").to(device)
            f = model.get_image_features(**x)
            f = f / f.norm(dim=-1, keepdim=True)
            sims = (f @ tf.T)[0].float().cpu().numpy()
            order = sims.argsort()[::-1][:K_MAX]
            if device == "cuda":
                torch.cuda.synchronize()
            emit("clip", r, [names[i] for i in order], time.time() - t0)
    del model
    _free()


def run_blip2(rows, d, emit, device):
    import torch
    from PIL import Image
    from transformers import Blip2ForConditionalGeneration, Blip2Processor
    dtype = torch.float16 if device == "cuda" else torch.float32
    proc = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
    model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-opt-2.7b", torch_dtype=dtype).to(device).eval()
    for r in rows:
        img = Image.open(os.path.join(d, "images", f"{r['image_id']}.jpg")).convert("RGB")
        t0 = time.time()
        x = proc(images=img, text=BLIP_PROMPT, return_tensors="pt").to(device, dtype)
        with torch.no_grad():
            out = model.generate(**x, max_new_tokens=40)
        caption = proc.batch_decode(out, skip_special_tokens=True)[0]
        toks = [t for t in re.findall(r"[a-zA-Z]+", caption.lower()) if t not in BLIP_STOPWORDS and len(t) > 2]
        labels = list(dict.fromkeys(toks))[:K_MAX] or ["object", "person", "area"]   # original fallback
        emit("blip2_orig", r, labels, time.time() - t0, raw=caption)
    del model
    _free()


def run_blip2_fair(rows, d, emit, device, variant):
    import torch
    from PIL import Image
    from transformers import Blip2ForConditionalGeneration, Blip2Processor
    dtype = torch.float16 if device == "cuda" else torch.float32
    proc = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
    model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-opt-2.7b", torch_dtype=dtype).to(device).eval()
    prompt = BLIP_QA_PROMPT if variant == "blip2_qa" else None
    empty = 0
    for i, r in enumerate(rows):
        img = Image.open(os.path.join(d, "images", f"{r['image_id']}.jpg")).convert("RGB")
        t0 = time.time()
        x = (proc(images=img, text=prompt, return_tensors="pt") if prompt else proc(images=img, return_tensors="pt"))
        x = x.to(device, dtype)
        with torch.no_grad():
            out = model.generate(**x, max_new_tokens=40, num_beams=3, repetition_penalty=1.3)
        if device == "cuda":
            torch.cuda.synchronize()
        raw = strip_prompt(proc.batch_decode(out, skip_special_tokens=True)[0], prompt or "")
        items = phrase_items(raw)
        empty += not items
        if i < 3:
            print(f"  {variant} raw: {raw!r} -> {items}", flush=True)
        emit(variant, r, items, time.time() - t0, raw=raw)
    print(f"  {variant}: {empty} of {len(rows)} scenes gave no items", flush=True)
    del model
    _free()


def run_qwen(rows, d, emit, device):
    import torch
    from PIL import Image
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
    mid = "Qwen/Qwen2.5-VL-3B-Instruct"
    proc = AutoProcessor.from_pretrained(mid, min_pixels=256 * 28 * 28, max_pixels=640 * 28 * 28)

    def load(dtype):
        return Qwen2_5_VLForConditionalGeneration.from_pretrained(mid, torch_dtype=dtype, attn_implementation="sdpa").to(device).eval()

    def ask(model, img):
        msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": QWEN_PROMPT}]}]
        text = proc.apply_chat_template(msgs, add_generation_prompt=True)
        x = proc(text=[text], images=[img], return_tensors="pt").to(device)
        with torch.no_grad():
            out = model.generate(**x, max_new_tokens=80, do_sample=False)
        return proc.batch_decode(out[:, x["input_ids"].shape[1]:], skip_special_tokens=True)[0]

    # Qwen2.5-VL can overflow in fp16. Probe 3 scenes; if fewer than 2 give a usable list,
    # reload in bf16 (emulated on a T4: slower, but it fits; fp32 would not fit in 15 GB).
    dtype = torch.float16 if device == "cuda" else torch.float32
    model = load(dtype)
    probes = [Image.open(os.path.join(d, "images", f"{r['image_id']}.jpg")).convert("RGB") for r in rows[:3]]
    answers = [ask(model, im) for im in probes]
    good = sum(len(parse_list(x)) >= 2 for x in answers)
    if dtype == torch.float16 and good < min(2, len(probes)):
        print(f"  qwen fp16 answers unusable ({answers[0][:60]!r}); reloading in bfloat16", flush=True)
        del model
        _free()
        dtype = torch.bfloat16
        model = load(dtype)
        answers = [ask(model, im) for im in probes]
    print(f"  qwen dtype {dtype}; first answer: {answers[0][:120]!r}", flush=True)
    short = 0
    for r in rows:
        img = Image.open(os.path.join(d, "images", f"{r['image_id']}.jpg")).convert("RGB")
        t0 = time.time()
        raw = ask(model, img)
        if device == "cuda":
            torch.cuda.synchronize()
        items = parse_list(raw)
        short += len(items) < 2
        emit("qwen_vl", r, items, time.time() - t0, raw=raw)
    print(f"  qwen: {short} of {len(rows)} scenes gave fewer than 2 items", flush=True)
    del model
    _free()


def _free():
    import gc
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="e2_set")
    ap.add_argument("--out", default="e2_outputs")
    ap.add_argument("--methods", nargs="+", default=["static", "clip", "blip2_orig", "qwen_vl"])
    ap.add_argument("--limit", type=int, default=None, help="dry run: first N scenes only")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows, vocab = load_set(a.set)
    if a.limit:                                  # dry run: spread the scenes over the rooms
        by = collections.defaultdict(list)
        for r in rows:
            by[r["room"]].append(r)
        picked = []
        while len(picked) < min(a.limit, len(rows)):
            for room in list(by):
                if by[room] and len(picked) < a.limit:
                    picked.append(by[room].pop(0))
        rows = picked
    path = os.path.join(a.out, "outputs.dry.jsonl" if a.limit else "outputs.jsonl")
    done = set()
    if os.path.exists(path):                    # drop a half-written last line left by a disconnect
        good = []
        for l in open(path):
            try:
                o = json.loads(l)
                done.add((o["method"], o["image_id"]))
                good.append(l if l.endswith("\n") else l + "\n")
            except json.JSONDecodeError:
                pass
        with open(path, "w") as g:
            g.writelines(good)
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        device = "cpu"
    print(f"{len(rows)} scenes | device {device} | methods {a.methods}", flush=True)
    f = open(path, "a")
    n = collections.Counter()

    def emit(method, r, items, secs, raw=None):
        f.write(json.dumps({"method": method, "image_id": r["image_id"], "items": items[:K_MAX],
                            "seconds": round(secs, 4), "raw": raw}) + "\n")
        f.flush()
        n[method] += 1
        if n[method] % 50 == 0:
            print(f"  {method}: {n[method]} scenes", flush=True)

    for m in a.methods:
        todo = [r for r in rows if (m, r["image_id"]) not in done]
        if not todo:
            print(f"{m}: already done")
            continue
        print(f"{m}: {len(todo)} scenes ...", flush=True)
        t0 = time.time()
        if m == "static":
            run_static(rows, vocab, lambda mm, r, it, s, raw=None: emit(mm, r, it, s, raw)
                       if (mm, r["image_id"]) not in done else None)
        elif m == "clip":
            run_clip(todo, a.set, vocab, emit, device)
        elif m == "blip2_orig":
            run_blip2(todo, a.set, emit, device)
        elif m in ("blip2_caption", "blip2_qa"):
            run_blip2_fair(todo, a.set, emit, device, m)
        elif m == "qwen_vl":
            run_qwen(todo, a.set, emit, device)
        else:
            raise SystemExit(f"unknown method {m}")
        print(f"{m}: done in {time.time() - t0:.0f} s", flush=True)
    f.close()


if __name__ == "__main__":
    main()
