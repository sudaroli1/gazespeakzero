# Study 2 — what should the screen offer? (Sec. 4.2)

**Question.** A gaze interface can offer only a handful of words at a time. Should they come
from a fixed AAC list, or from what the camera can see in the room?

**Answer.** Grounding in the scene beats the best fixed list on every paired measure. The
design document `E2_DESIGN.md` was fixed before the run and names what would have refuted
that.

**A second finding matters more than the first:** presence and usefulness diverge. A word can
be verifiably in the image and still be no use to someone trying to say something, which is
why the human audit exists and why `verifiable@3` is reported next to `precision@3`.

## What you need

283 LVIS v1 validation scenes (60 each for bathroom, bedroom, kitchen and living room, 43 for
dining — only 43 qualified), from LVIS and COCO. We cannot redistribute the images or the
annotation files. `results/set.jsonl` records exactly which images were used, so the scoring
stage below can be re-run without re-selecting them.

The generation stage used a T4 GPU on Colab. The notebooks are here; so are their outputs.

## Order of operations

```
python e2_build_set.py   --lvis <lvis_val.json> --out set.jsonl     # which scenes
python e2_generate.py    --set set.jsonl --out outputs.jsonl        # GPU: six methods
python e2_score.py       --set set.jsonl --outputs outputs.jsonl --out results
python build_audit_workbook.py                                     # the blinded human audit
python e2_audit_score.py --rated results/audit_rater*.xlsx \
       --key <key> --codes <codes> --items results/e2_items.csv --out results/audit
```

`results/outputs.jsonl` is the generation stage's output as it was produced, so
`e2_score.py` can be re-run and checked without a GPU.

`E2_scene_vocab_colab.ipynb` and `E2b_blip2_fair_colab.ipynb` are the notebooks that ran;
`build_notebook_e2.py` and `build_notebook_e2b.py` regenerate them from these files.
`aac_vocab.py` is the fixed AAC list the scene methods are compared against, and Study 3
imports it from here rather than keeping a second copy.

## The audit, and what is not here

The audit was blinded: raters saw method outputs under codes, with the mapping withheld until
after rating. **The answer key and the code mapping are not in this repository** — publishing
them would make the blinding unrepeatable for anyone who wants to rate the same sheet. The
rated workbooks, the scoring script and every number derived from them are here.
`audit_review_changes.csv` records what changed when a rater revised a judgement.

## Results in this folder

| File | What it is |
|---|---|
| `results/e2_summary.csv` | the headline table: six methods, four measures |
| `results/e2_per_image.csv` | per-scene scores, the unit the intervals bootstrap over |
| `results/e2_paired_differences.csv` | paired differences against the fixed list |
| `results/e2_by_room.csv` | the same by room type |
| `results/e2_items.csv` | every proposed item, with its verification status |
| `results/e2_top_unmatched_items.csv` | the useful words no ground truth contains — the divergence above |
| `results/audit/` | the human audit: agreement, summary, and audit vs automatic labels |
| `results/vocab.json`, `set.jsonl` | the vocabulary and the exact scene set |
| `results/E2_REPORT.md`, `audit/AUDIT_REPORT.md` | each run's own report |

Study 3 and Study 4 both take parameters from `results/`.
