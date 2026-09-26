# E3 findings: from the selected objects to the intended message (run 23 Sep 2026, T4)

Design fixed before the run: `E3_DESIGN.md`. Results: `results/`.
60 intents × 4 conditions = 240 cases, every method on the same cases.

## Headline: the language-model stage does not earn its place

The refutation written into the design has happened. **No language model beats a
plain lookup over the intent bank.**

| Method | top-1 | top-3 | s/case (T4) |
|---|---|---|---|
| **prior** (overlap lookup, no vision model, no LM) | **0.538 [0.48, 0.60]** | **0.650 [0.59, 0.71]** | 0 |
| lm_gen_phi3.5 (3.8B writes the message) | 0.471 [0.41, 0.53] | 0.608 [0.55, 0.67] | 0.45 |
| template ("I want X and Y") | 0.450 [0.39, 0.51] | 0.600 [0.54, 0.66] | 0 |
| lm_gen_qwen3b | 0.462 [0.40, 0.53] | 0.579 [0.52, 0.64] | 0.57 |
| lm_gen_qwen1.5b | 0.421 [0.36, 0.48] | 0.579 [0.52, 0.64] | 0.45 |
| lm_gen_smol1.7b | 0.417 [0.35, 0.48] | 0.571 [0.51, 0.63] | 0.28 |
| embed (MiniLM retrieval) | 0.354 [0.29, 0.41] | 0.517 [0.45, 0.58] | 0.01 |
| lm_rank_* (likelihood ranking, 4 models) | 0.06–0.13 | 0.20–0.27 | 0.42–1.00 |

Paired against the retrieval baseline, every generative model is a little
better (top-3 +0.05 to +0.09), and the free lookup is better still
(+0.13 [0.08, 0.19]). Likelihood ranking is far **worse** than retrieval
(−0.25 to −0.32).

## Why, and what it means for the paper

1. **The identification is in the objects, not in the language.** In the bank,
   a selection of 1–3 AAC objects almost always picks out one intent, so
   counting overlapping objects solves the task. The LM adds phrasing, not
   identification. The original paper's architecture (objects → LM → intent)
   therefore rests on a step that a lookup table does for free.
2. **Under a wrong selection, nothing recovers — and that is mostly by
   construction.** 41 of 60 intents need a single object; in the two noise
   conditions that object is replaced, so the intent is unrecoverable by any
   method. Reported separately:

   | Method | noisy, recovery possible (n=38) | noisy, information destroyed (n=82) |
   |---|---|---|
   | prior | **0.947** top-3 | 0.000 |
   | lm_gen_phi3.5 | 0.816 | 0.037 |
   | template | 0.816 | 0.024 |
   | embed | 0.579 | 0.061 |
   | lm_rank_* | 0.13–0.40 | 0.04–0.09 |

   So even where recovery is possible, the lookup wins. The 0.13–0.32 figures
   in the headline table for the noise conditions are dominated by the
   unrecoverable cases and must not be quoted on their own.
3. **Using the models properly does not save them (E3b, run 23 Sep).** Two
   standard fixes were added after the first result and scored on the same 240
   cases:
   - **PMI calibration** (each candidate's score corrected by how much the model
     likes that sentence anyway) lifts likelihood ranking from top-3 0.20–0.27
     to **0.30–0.37**, which confirms the surface-form diagnosis — and still
     leaves it far below plain retrieval (0.517) and the lookup (0.650).
   - **In-context multiple choice** (the model is shown all 60 messages and asked
     for the best three) is *worse*, at top-3 0.06–0.30. The failure is
     instructive rather than a parsing bug: every model emitted parseable
     numbers, but SmolLM2 answered "1, 2, 3" in 97% of cases and Qwen2.5-1.5B
     started from option 1 in 63%. Small models cannot select from a 60-item
     list presented in the prompt.

   So the conclusion holds after the fair-usage check: **no way of using a
   1.5–3.8B model on this task beats counting overlapping objects.** The best
   language method remains free generation (Phi-3.5, top-3 0.608), which is
   level with the "I want X" template (0.600) and below the lookup
   (0.650; lookup − retrieval = +0.133 [0.083, 0.188]).
4. **Speed is not the issue.** The generative models take 0.3–0.6 s per case
   on a T4, ranking up to 1.0 s. E5 will measure CPU.

## What the paper should claim about the LM stage

With E3b done and the message audit outstanding, the defensible position is:

- The contribution of the pipeline is the **vision** stage (E2) and the
  **interface** (E1b), not the language model.
- A language model is worth including only for what a lookup cannot do:
  producing a natural sentence from an item, and covering messages that are
  not in the bank. That is a claim about *wording*, which the automatic score
  cannot test, so it is tested by the blinded message audit below.
- The fair usages did still lose to the lookup, so the paper reports that
  plainly and the system keeps the LM only as an optional phrasing layer,
  justified by the message audit rather than by accuracy.

## Blinded message audit (`results/message_rater1.xlsx`, 300 rows) — still to rate

Automatic scoring only asks whether a generated message maps back to the
reference intent. It cannot ask whether the sentence is one a person would
accept as their own words. The sheet covers the 60 clean cases × 5 message
producers (4 models + the template), method hidden, reference not shown:

- **D:** could this be what the person meant, given the room and their
  selection?
- **E:** would you be happy to have this spoken aloud on your behalf?

Question E is where the LM should win over `template` ("I want water bottle
and straw.") and where a reviewer will look for evidence. Examples from the
run that show what is at stake:

- objects `bed, quilt, pillow` → Qwen3B wrote "I'm comfortable on the bed with
  the quilt and pillow." The reference was "Please straighten my bed covers."
  Fluent, and wrong about the person's state.
- objects `lamp` → "I need the lamp turned on in the bedroom", where the
  intent was to turn the light **off**.

Those are exactly the failures a fluent sentence hides, so the audit asks
about them directly.

## Known limits
- The 60-message bank is a closed set, and small; retrieval is easy on it by
  construction. A realistic device would have hundreds of messages plus
  open-ended composition, where the balance may differ. The paper must say so.
- The automatic mapping of a generated sentence to an intent uses MiniLM
  embeddings; re-scoring without `sentence-transformers` falls back to token
  overlap and gives different numbers (the fallback exists for the smoke
  tests, not for results).
- One rater, as in E2.
