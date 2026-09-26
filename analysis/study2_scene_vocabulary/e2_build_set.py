"""
E2, step 1: choose the everyday indoor scenes and write their ground truth.

    python e2_build_set.py --lvis lvis_v1_val.json --out e2_set --per-room 60 \
        --coco-ann instances_train2017.json instances_val2017.json --coco-synset coco_to_synset.json

The scenes come from the LVIS v1 validation set (COCO 2017 photos annotated with
more than 1,200 object categories). An image qualifies if:
  * it contains a room indicator (see ROOM_INDICATORS), which also gives its room;
  * at least 3 AAC-vocabulary categories are present in it.
Up to --per-room images are drawn per room with a fixed seed.

Writes set.jsonl (one line per image: id, url, room, positive category ids,
verified-absent category ids) and vocab.json, and downloads the images to
out/images/. Nothing here depends on any method's output.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aac_vocab import AAC_VOCAB, ROOM_INDICATORS, Matcher  # noqa: E402

SEED = 0
# COCO "dining table" covers any table, "tv" includes monitors, "cup" includes mugs and glasses:
# their PRESENCE is not taken as LVIS presence (their absence still is).
COCO_NO_POSITIVE = {"dining table", "tv", "cup"}
# Small objects COCO often leaves unlabelled: their ABSENCE is not trusted.
COCO_NO_NEGATIVE = {"spoon", "knife", "fork", "remote", "toothbrush", "cell phone", "scissors", "mouse",
                    "book", "hair drier"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lvis", required=True)
    ap.add_argument("--out", default="e2_set")
    ap.add_argument("--per-room", type=int, default=60)
    ap.add_argument("--min-aac", type=int, default=3)
    ap.add_argument("--no-download", action="store_true")
    ap.add_argument("--coco-ann", nargs="*", default=[],
                    help="COCO 2017 instances_*.json. COCO labels its 80 classes exhaustively, so a COCO class "
                         "absent from a photo is verified absent; mapped to LVIS via coco_to_synset.json")
    ap.add_argument("--coco-synset", default=None, help="coco_to_synset.json from the lvis-api repository")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "images"), exist_ok=True)

    d = json.load(open(a.lvis))
    m = Matcher(d["categories"])
    vocab_ids, missing = m.resolve_vocab(AAC_VOCAB)
    print(f"AAC vocabulary: {len(vocab_ids)} of {len(AAC_VOCAB)} names found in this LVIS release")
    if missing:
        print("  not in LVIS (dropped):", ", ".join(missing))
    room_ids = []
    for room, names in ROOM_INDICATORS:
        ids, miss = m.resolve_vocab(names)
        room_ids.append((room, set(ids)))
        if miss:
            print(f"  room indicator names not in LVIS for {room}: {miss}")

    pos = collections.defaultdict(set)
    for ann in d["annotations"]:
        pos[ann["image_id"]].add(ann["category_id"])
    del d["annotations"]                         # free memory before the COCO files are read
    import gc; gc.collect()
    vset = set(vocab_ids)
    by_room = collections.defaultdict(list)
    for img in d["images"]:
        p = pos.get(img["id"], set())
        room = next((r for r, ids in room_ids if p & ids), None)
        if room is None or len(p & vset) < a.min_aac:
            continue
        by_room[room].append(img)
    rng = random.Random(SEED)
    chosen = []
    for room, _ in ROOM_INDICATORS:
        imgs = sorted(by_room[room], key=lambda i: i["id"])
        rng.shuffle(imgs)
        chosen += [(room, i) for i in imgs[: a.per_room]]
        print(f"  {room}: {len(by_room[room])} eligible, {min(len(imgs), a.per_room)} chosen")

    # COCO exhaustive labels -> extra verified-present / verified-absent LVIS categories
    coco_pos, coco_known = {}, set()
    coco_map, coco_neg_ok, coco_pos_ok = {}, set(), set()
    coco_n_ann = collections.Counter()
    if a.coco_ann and a.coco_synset:
        syn = json.load(open(a.coco_synset))
        lvis_by_synset = {c.get("synset"): c["id"] for c in d["categories"] if c.get("synset")}
        want = {img["id"] for _, img in chosen}
        for path in a.coco_ann:
            cj = json.load(open(path))
            cname = {c["id"]: c["name"] for c in cj["categories"]}
            for c in cj["categories"]:
                lid = lvis_by_synset.get(syn.get(c["name"], {}).get("synset"))
                if lid is not None:
                    coco_map[c["id"]] = lid
                    if c["name"] not in COCO_NO_NEGATIVE:
                        coco_neg_ok.add(lid)
                    if c["name"] not in COCO_NO_POSITIVE:
                        coco_pos_ok.add(lid)
            for im in cj["images"]:
                if im["id"] in want:
                    coco_known.add(im["id"])
                    coco_pos.setdefault(im["id"], set())
            for an in cj["annotations"]:
                if an["image_id"] in want:
                    coco_n_ann[an["image_id"]] += 1
                    if an["category_id"] in coco_map:
                        coco_pos[an["image_id"]].add(coco_map[an["category_id"]])
            del cj
        coco_known = {i for i in coco_known if coco_n_ann[i] > 0}   # trust absences only for labelled images
        print(f"COCO: {len(coco_map)} of 80 classes map to LVIS; {len(coco_known)} of {len(want)} scenes found "
              f"in COCO files with at least one label")
        print("  COCO -> LVIS:", ", ".join(sorted(f"{cname_} -> {d_}" for cname_, d_ in
              ((n, next((c['name'] for c in d['categories'] if c['id'] == coco_map[i]), '?'))
               for i, n in cname.items() if i in coco_map)))[:2000])

    rows = []
    for room, img in chosen:
        url = img.get("coco_url") or f"http://images.cocodataset.org/val2017/{img['id']:012d}.jpg"
        rows.append({"image_id": img["id"], "url": url, "room": room, "width": img.get("width"),
                     "height": img.get("height"), "pos": sorted(pos[img["id"]]),
                     "neg": sorted(img.get("neg_category_ids", [])),
                     # extended with COCO exhaustive labels (primary for scoring)
                     "pos_x": sorted(pos[img["id"]] | ((coco_pos.get(img["id"], set()) & coco_pos_ok)
                                                       - set(img.get("neg_category_ids", [])))),
                     "neg_x": sorted((set(img.get("neg_category_ids", [])) |
                                      ((coco_neg_ok - coco_pos.get(img["id"], set())) if img["id"] in coco_known else set()))
                                     - pos[img["id"]] - coco_pos.get(img["id"], set())),
                     "not_exhaustive": sorted(img.get("not_exhaustive_category_ids", []))})
    with open(os.path.join(a.out, "set.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    json.dump({"vocab_ids": vocab_ids, "vocab_names": [m.id2name[i] for i in vocab_ids],
               "missing": missing, "categories": d["categories"]},
              open(os.path.join(a.out, "vocab.json"), "w"))
    print(f"{len(rows)} scenes written")

    if a.no_download:
        return
    import requests
    ok = 0
    for r in rows:
        dst = os.path.join(a.out, "images", f"{r['image_id']}.jpg")
        if os.path.exists(dst) and os.path.getsize(dst) > 1000:
            ok += 1
            continue
        for attempt in range(3):
            try:
                resp = requests.get(r["url"], timeout=30)
                resp.raise_for_status()
                open(dst, "wb").write(resp.content)
                ok += 1
                break
            except Exception as e:
                if attempt == 2:
                    print(f"  download failed {r['image_id']}: {e}")
                time.sleep(2)
    print(f"images downloaded: {ok}/{len(rows)}")


if __name__ == "__main__":
    main()
