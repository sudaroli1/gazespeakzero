# E2 findings: scene vocabulary (run 21 Sep 2026, T4 GPU)

Design fixed before the run: `E2_DESIGN.md`. Final results: `results/` (six methods; `set.jsonl` and `vocab.json` included). First run (four methods) (not published: superseded outputs are kept in the working tree and are available on request).

## Set
- 283 LVIS v1 val scenes: 60 each for bathroom, bedroom, kitchen and living room,
  and 43 for dining (only 43 dining scenes qualified).
- 96 of the 98 AAC vocabulary items are in LVIS (comb and pill are not).
- Every method covered all 283 scenes. All figures are paired, on the same
  scenes.

## Headline (primary ground truth: LVIS + COCO extension; 95% bootstrap CIs over scenes)

| Method | precision@3 | hit@3 | recall@6 | verifiable@3 | median s/scene (T4) |
|---|---|---|---|---|---|
| static (best fixed list, with hindsight) | 0.297 [0.27, 0.33] | 0.661 [0.60, 0.72] | 0.249 [0.23, 0.27] | 1.00 | 0 |
| clip (ViT-L/14 over the AAC vocabulary) | 0.897 [0.87, 0.92] | 0.968 [0.95, 0.99] | 0.468 [0.44, 0.50] | 0.61 | 0.07 |
| blip2_orig (original paper, verbatim) | 0.304 [0.25, 0.36] | 0.304 [0.25, 0.36] | 0.000 | 0.33 | 0.13 |
| qwen_vl (Qwen2.5-VL-3B) | 0.970 [0.95, 0.98] | 0.958 [0.93, 0.98] | 0.492 [0.47, 0.52] | 0.70 | 1.90 |

Paired differences (a − b, 95% CI):

| a vs b | hit@3 | recall@6 | precision@3 |
|---|---|---|---|
| qwen_vl vs static | **+0.297** [0.237, 0.360] | **+0.244** [0.211, 0.278] | +0.676 [0.642, 0.710] |
| clip vs static | **+0.307** [0.247, 0.371] | **+0.219** [0.184, 0.254] | +0.603 [0.562, 0.643] |
| qwen_vl vs clip | −0.011 [−0.042, 0.021] | +0.025 [−0.005, 0.053] | **+0.073** [0.047, 0.103] |

## What this means for the claims

1. **Claim C2 is supported: the pre-registered refutation did not happen.**
   Both vision methods beat the best possible fixed list, and the gain holds
   in every room.
   - The first screen of 3 contains at least one object that is really there
     in 96–97% of scenes. For the fixed list the figure is 66%.
   - The first two screens name about half of the AAC-relevant objects
     present. The fixed list names a quarter.
2. **The static list is weakest in bedrooms and living rooms**, where hit@3 is
   0.37 and 0.60. It does best in bathrooms, at 0.87, because bathrooms are
   predictable. This fits the positioning against Look to Speak: a fixed list
   works in predictable rooms and fails where the contents vary.
3. **Qwen vs CLIP: a tie on coverage; Qwen is more precise.** The case for an
   open-vocabulary VLM is therefore not "it finds more". It rests on three
   points:
   - Its first-screen items are wrong less often (+0.07).
   - It is not limited to a hand-made list: it names items outside our
     vocabulary, such as window, rug, door, menu, lotion and ketchup.
   - Its cost is 1.9 s per scene on a T4, against 0.07 s for CLIP. That cost
     is paid once per scene, not per selection, so it is acceptable, but E5
     must measure it on CPU.

   The paper should say this plainly and not claim that the VLM beats CLIP on
   hit rate.
4. **The original BLIP-2 step never worked in this run.** Under transformers
   4.51.3, the decoded output for all 283 scenes was only the echoed question.
   OPT generated nothing, so every scene got the fallback "object, person,
   area". Its 0.30 hit@3 is simply how often a person is in the photo.
   - We must not present this as "BLIP-2 is bad". It shows that the original
     pipeline's output was not what the paper described.
   - For a fair comparison, `blip2_caption` and `blip2_qa` were added (see
     below).

## Caveats that go in the paper
- **Verifiability:**
  - Precision is computed only over items the labels can check. That is 61%
    of CLIP's first-screen items and 70% of Qwen's.
  - Qwen's most common unverifiable items are rug, window, picture, wall and
    door. LVIS has no window or door category.
  - The blinded audit (`audit_sheet.csv`, 50 scenes × top 6) covers these
    items and should be rated before submission.
- **LVIS-only check:**
  - With LVIS labels alone, verifiability collapses: the static list's
    verifiable@3 is 0.095. The primary figures therefore rely on the COCO
    extension (with the stated safeguards).
  - Both figures are reported. Where items can be checked, precision stays
    ≥ 0.95 for every method.
- **Unequal vocabularies:** CLIP ranks only our 96-item AAC vocabulary, while
  Qwen is open-vocabulary. This favours CLIP on verifiability, not on
  correctness.
- **Short lists:** Qwen returned fewer than 3 items for 4 of 283 scenes, 2 of
  them from a repetition collapse.
- **Domain gap:** these are COCO snapshots, not the view from a bed. Phase 2
  has to test that view.

## Add-on: fair BLIP-2 baselines (E2b, run 21 Sep; final figures in `results/`)

Two variants, both with the echoed prompt stripped:

- **`blip2_caption`:** the same BLIP-2 OPT-2.7B with no prompt (native
  captioning, 3 beams).
- **`blip2_qa`:** the prompt "Question: What objects are in this room?
  Answer:".

Both answers are cut into noun phrases.

**Parser fix after the run.** The phrase parser was fixed after the run:
- the longest preposition now matches first ("in front of", not "in");
- any "-ing" verb splits a phrase, except for a list of -ing nouns (living
  room, dining table, ceiling fan, washing machine, …).

The raw text was re-parsed and re-scored locally. This changed 40 of 566
lists and moved BLIP-2's figures by at most 1 point, always upward. The
change is generous to the baseline, and nothing else changed. The Colab
as-run tables (not published: superseded outputs are kept in the working tree and are available on request).

**The other four methods reproduce exactly** from the Colab run on the real
`vocab.json`.

| Method | precision@3 | hit@3 | recall@6 | items per scene (mean) | scenes with < 3 items | median s/scene |
|---|---|---|---|---|---|---|
| blip2_caption | 0.992 [0.98, 1.00] | 0.855 [0.81, 0.90] | 0.240 [0.22, 0.27] | 3.0 | 70 | 0.41 |
| blip2_qa | 0.949 [0.93, 0.97] | 0.926 [0.89, 0.95] | 0.312 [0.29, 0.34] | 3.1 | 81 | 0.51 |
| qwen_vl (for reference) | 0.970 | 0.958 | 0.492 | 6.6 | 4 | 1.90 |
| clip (for reference) | 0.897 | 0.968 | 0.468 | 12 | 0 | 0.07 |

Paired differences (95% CI):

| Comparison | Metric | Difference |
|---|---|---|
| qwen_vl − blip2_qa | hit@3 | +0.032 [−0.007, 0.074] (a tie) |
| qwen_vl − blip2_qa | recall@6 | **+0.181** [0.153, 0.209] |
| clip − blip2_qa | hit@3 | +0.042 [0.007, 0.081] |
| clip − blip2_qa | recall@6 | **+0.156** [0.127, 0.186] |
| blip2_caption − static | recall@6 | −0.009 [−0.037, 0.020] (no better than a fixed list) |
| blip2_qa − static | hit@3 | +0.265 [0.198, 0.329] |

### What changes in the story
1. **The original paper's BLIP-2 step failed because of how it was used, not
   because of the model.** Used properly, BLIP-2 gets a correct item onto the
   first screen in 93% of scenes. The paper must say so, instead of letting
   the verbatim run imply "BLIP-2 is useless".
2. **The real limit of a captioner is depth.** A caption or short answer names
   about 3 objects. In 25–29% of scenes it names fewer than 3, so it cannot
   fill even one screen. The interface pages 3 items at a time, so what
   matters after the first screen is the second screen and beyond, and there
   a captioner has nothing left:
   - recall@6 is 0.24–0.31, against 0.47–0.49 for CLIP and Qwen;
   - plain captioning is no better than a fixed list on recall@6.
3. **The C2 comparison changes accordingly.** It is no longer "a VLM against
   a broken BLIP-2". It is "ranked, deep proposals (CLIP over a vocabulary, or
   an instructed VLM) against a caption":
   - the first screen is about equal;
   - the first two screens favour the deep proposers by 16–18 points.
4. **BLIP-2's high precision@3 is partly a consequence of naming few,
   salient objects.** Precision here is conditional on what the method
   names, so it must be read with recall and list length, never alone.

## Human audit (blinded, rated 22–23 Sep; `results/audit/`)

50 scenes, the top 6 items of each method, method names hidden, 1,045 rated
items. Two questions per item: **in the photo?** and, if yes, **would a person
there want or mention it?**

**Who judged, and how — state this plainly in the paper.** One rater (an author)
judged all 1,045 items. A second person then went over the same answers and
corrected the ones they disagreed with, so the labels below are **adjudicated by
two people, not two independent ratings**. The second pass changed the
in-photo answer for 14 of 1,323 method-item pairs (1.1%) and the usefulness
answer for 23 of 660 (3.5%), spread across methods (1.1–2.1% of each vision
method's items, none of the fixed list's), and moved no method's figures by
more than 0.02.

No inter-rater kappa is reported, because the second pass saw the first
answers. A blank 15-scene workbook (`results/audit_rater_independent.xlsx`)
is ready if a reviewer asks for a truly independent rating.

| Method | in photo @3 | useful @3 | useful hit@3 | in photo @6 | useful @6 |
|---|---|---|---|---|---|
| static | 0.253 [0.19, 0.32] | 0.133 [0.09, 0.19] | 0.38 [0.26, 0.52] | 0.200 | 0.087 |
| clip | 0.593 [0.52, 0.67] | 0.287 [0.20, 0.37] | 0.54 [0.40, 0.68] | 0.477 | 0.243 |
| blip2_orig | 0.100 [0.06, 0.14] | 0.007 [0.00, 0.02] | 0.02 [0.00, 0.06] | 0.050 | 0.003 |
| blip2_caption | 0.773 [0.71, 0.84] | 0.247 [0.17, 0.33] | 0.50 [0.36, 0.64] | 0.417 | 0.137 |
| blip2_qa | 0.680 [0.60, 0.75] | 0.280 [0.21, 0.36] | 0.58 [0.44, 0.72] | 0.383 | 0.150 |
| **qwen_vl** | **0.780 [0.69, 0.85]** | **0.387 [0.29, 0.49]** | **0.64 [0.50, 0.76]** | **0.680** | **0.353** |

Here precision is out of K, so a short list is penalised, and every item
counts — including the ones the labels could not check.

### What the audit adds

1. **Qwen's unchecked items are mostly real; CLIP's are mostly not.** Of the
   items the labels could not verify, the rater found in the photo:
   - qwen_vl 68%, blip2_qa 71%, blip2_caption 76%;
   - **clip only 32%**;
   - static 10%.

   This is the answer to "are the unverifiable items hallucinations?" — for
   the VLM they are largely genuine objects that LVIS has no category for
   (window, rug, door); for CLIP they are largely wrong guesses, because CLIP
   must rank a fixed vocabulary whether or not the objects are there.
2. **The automatic comparison understated the gap between Qwen and CLIP.**
   Judged by a human over all items, Qwen leads CLIP on the first screen by
   **+0.19 [0.07, 0.29]** (in photo @3), on the first two screens by
   **+0.20 [0.13, 0.27]**, and on useful@6 by **+0.11 [0.04, 0.18]**. The automatic figures had them nearly tied.
3. **Usefulness separates the methods further than presence does.** Only 39%
   of Qwen's first-screen items are both present and worth offering, against
   29% for CLIP, 28% for blip2_qa and 13% for the fixed list. Paired: Qwen over
   the fixed list **+0.25 [0.16, 0.35]** on useful@3 and **+0.26 [0.10, 0.40]**
   on useful hit@3. Qwen over CLIP is **+0.10 [−0.02, 0.22]**, so on usefulness
   at the first screen the two are not separated.
   - The remaining 60% is the design problem for E3/E4: about half of what
     any method offers is background a patient would not name. Re-ranking by
     usefulness, not only by presence, is the obvious next lever.
4. **The automatic labels are decent but not perfect.** Human and label agree
   on 81–93% of the items the labels could judge. Most disagreements are
   items the labels call present and the raters could not see (29 for Qwen, 24
   for CLIP), i.e. label noise or objects too small to point at, not method
   errors.
5. **Generic names change nothing.** Removing area, object and room names from
   every list leaves the ranking unchanged.

### Audit files
`results/audit_rater1.xlsx` (first pass) and `results/audit_rater2.xlsx`
(second pass, the labels used). Scored by `e2_audit_score.py --review`; the
per-method change counts are in `results/audit/audit_review_changes.csv`.
The blinded sheet the workbooks were built from is `results/audit_sheet.csv` (1,045 rows: 50 scenes, the top 6 items of
each of the 6 methods, with duplicates merged). The codes differ from v1 and
from the Colab v2 sheet, so use this file only.
