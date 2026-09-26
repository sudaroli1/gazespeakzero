# Study 3 — does a language model recover the message? (Sec. 4.3)

**Question.** The person has selected two or three objects. Something must turn that into the
sentence they meant. Does a small language model do it better than a plain lookup?

**Answer. No** — and this is a **pre-registered refutation**. `E3_DESIGN.md` was fixed before
the run and stated that if a plain overlap count over the intent bank matched or beat the
language models, the language stage would be dropped. It did: 0.538 top-1 against 0.471 for
the best generative model, on the same 240 cases. Four models used three ways (generation,
likelihood ranking, embedding retrieval) all fall below it.

The identification is carried by the selected objects, not by the language. That result
removed a component from the system rather than adding one.

## Order of operations

```
python build_intent_bank.py                                        # 60 intents, from the Study 2 vocabulary
python e3_build_cases.py --bank intent_bank.json \
       --e2-items ../study2_scene_vocabulary/results/e2_items.csv --out cases.jsonl
python e3_run.py   --bank intent_bank.json --cases cases.jsonl --out outputs.jsonl   # GPU
python e3_score.py --bank intent_bank.json --cases cases.jsonl \
       --outputs outputs.jsonl --out results
python build_message_workbook.py <src> <out>                        # the blinded human check
```

60 intents x 4 noise conditions = 240 cases; every method sees the same cases.
`results/outputs.jsonl` is the generation stage as it ran, so the scoring can be repeated
without a GPU. `E3_intent_colab.ipynb` and `E3b_fair_lm_colab.ipynb` are the notebooks that
ran; `build_notebook_e3.py` and `build_notebook_e3b.py` regenerate them, inlining
`aac_vocab.py` from Study 2 so there is one copy of the vocabulary and not two.

`intent_bank.json` appears both here and in `results/` — the second is the copy the scored run
used, kept with its outputs.

## What is not here

As in Study 2, the **blinded key and code mapping for the human message check are withheld**
so the sheet can be rated again by someone else. The rated workbook and all derived numbers
are here.

## Results in this folder

| File | What it is |
|---|---|
| `results/e3_summary.csv` | the headline table: every method, top-1 and top-3 |
| `results/e3_per_case.csv` | per-case results, the unit the intervals bootstrap over |
| `results/e3_paired_differences.csv` | each model against the lookup, paired |
| `results/e3_by_condition.csv` | by noise condition — how far the object list can be wrong |
| `results/e3_noise_recoverable.csv` | which errors were recoverable at all |
| `results/e3_generations.csv` | what each model actually wrote, for inspection |
| `results/cases.jsonl`, `outputs.jsonl` | the cases, and the raw model outputs |
| `results/E3_REPORT.md` | the run's own report |

## Check it

```
python smoke_test_e3.py        # 27 tests
```

Builds cases with a known correct answer, runs the real scorer, and asserts that every method
is scored on the same cases — the failure this guards against is a method quietly scoring a
subset and winning.
