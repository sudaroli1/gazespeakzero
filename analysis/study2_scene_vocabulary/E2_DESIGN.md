# E2 design (fixed 21 Sep 2026, before any E2 output was seen)

**Question (claim C2):** from a photo of an everyday room, how well does each
method propose the objects a person there might select? The methods are judged
the way the interface will use them: items are shown 3 at a time, so the first
screen is the top 3.

## Data
- **Scenes:** 300 photos from **LVIS v1 val**, which are COCO 2017 photos
  labelled with more than 1,200 object categories. They are sampled at 60 per
  room with a fixed seed. A photo qualifies if it contains a room indicator
  (checked in the order bathroom, bedroom, kitchen, living room, dining) and at
  least 3 AAC-vocabulary objects.
- **Ground truth:** LVIS verified-present and verified-absent labels, extended
  with COCO's exhaustive labels for its 80 classes, with two safeguards:
  - COCO *presence* is not trusted for "dining table" (it covers any table),
    "tv" (it includes monitors) or "cup" (it includes mugs and glasses);
  - COCO *absence* is not trusted for small objects COCO often misses (spoon,
    knife, fork, remote, toothbrush, cell phone, scissors, mouse, book, hair
    dryer).

  LVIS-only figures are reported as a check.
- **AAC vocabulary:** 98 names (`aac_vocab.py`) for everyday things a person
  with severe motor impairment might ask for, use or mention. Names missing
  from LVIS v1 (probably comb and pill) are dropped and reported.

## Methods (each proposes up to 12 ranked items)

| Code | What it is | Why it's included |
|---|---|---|
| static | AAC-vocabulary objects ranked by frequency in the *other* scenes; no camera | The best possible pre-written list (Look to Speak style), built with hindsight, so a generous baseline |
| clip | CLIP ViT-L/14 ranks the AAC vocabulary against the photo | The original paper's scene model, used properly |
| blip2_orig | The original paper's Stage 2, verbatim: a BLIP-2 caption split into words | Shows what the original pipeline actually produced |
| qwen_vl | Qwen2.5-VL-3B-Instruct lists up to 12 useful objects, most useful first | A small modern open vision-language model with an open vocabulary |

## Scoring (`e2_score.py`)
- **Matching:** items are matched to LVIS names and synonyms, plus a fixed
  alias table (fridge, tv, cell phone, …) applied the same way to every method.
  A repeated category counts once.
- **Primary metrics:**
  - precision@3, the share of first-screen items that are there;
  - hit@3, whether at least one first-screen item is there;
  - recall@6, the share of AAC objects present that are named in the first two
    screens.
- **Also reported:**
  - verifiable@K;
  - lenient variants, where small equivalence groups count (table ≈ dining
    table);
  - pooled precision;
  - per room.
- **Statistics:** 95% bootstrap CIs over scenes, and paired differences between
  methods on the same scenes. Only scenes covered by every method are scored.
- **Human audit:** a blinded sheet of 50 scenes × top 6 items with the method
  hidden, rated Y/N for "in the photo" and "plausibly wanted". It covers the
  items LVIS cannot verify.

## What would refute C2
If qwen_vl or clip does no better than static on hit@3 and recall@6 (paired CI
including 0), vision adds no value over a good fixed list, and the thesis fails
at this stage. The paper would report that.

## Known limits
- The photos are COCO-style snapshots, not the view from a patient's bed.
- LVIS has no door, window or light category, so items like these are
  unverifiable.
- The vocabulary is ours, and the audit covers that.

## Checks before running
- Smoke tests on the real LVIS 100-image sample (`testdata/`), with oracle,
  anti-oracle and static runs, resume after a half-written line, and a fake
  COCO file.
- A subagent review raised about 20 issues; all the bugs and risks were fixed:
  - a Qwen fp32 fallback that could not fit on a T4 (now bf16);
  - hit@3 using the lenient check;
  - missing aliases;
  - preposition phrases ("glass of water");
  - plurals ("knives");
  - head-noun lenient matching (now explicit groups);
  - duplicate categories counted twice;
  - COCO overrides;
  - denominators;
  - methods covering different scenes;
  - an unpaired bootstrap;
  - timing that included Google Drive reads;
  - blinding leaks in the audit sheet;
  - version pins.
