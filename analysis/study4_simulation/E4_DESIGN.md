# E4 design (fixed 23 Sep 2026, before any E4 number was produced)

**Question (claim C4):** given what E1b measured about calibration-free webcam
gaze and what E2 measured about scene-grounded item lists, **what should the
interface look like, and does scene grounding beat a fixed list once the errors
of both stages are paid for?**

E1–E3 measured components. E4 is the only experiment that answers the question
a clinician would ask: *how long does one message take, and how often is the
wrong thing said?*

## What is simulated

One message = the user selects one target item. The simulator counts
**selections**, **seconds**, and whether the **wrong item is finally spoken**.

Nothing in the simulator is a guess where a measurement exists:

| Quantity | Source | Value |
|---|---|---|
| Per-selection accuracy, 2 zones | E1b, 0.5 s dwell, single frame | 0.771 |
| Per-selection accuracy, 3 zones in a row | E1b | 0.838 |
| Per-selection accuracy, 3×3 grid | E1b | 0.481 |
| Share of dwells with no answer | E1b (`answered_frac`) | 0.031 |
| Rank of the wanted object in a scene-grounded list | E2 (`qwen_vl`, `clip`) | measured curve |
| Rank of the wanted object in the best fixed list | E2 (`static`, frequency order over the 96-item AAC vocabulary) | measured curve |
| Objects present per scene | E2 set | 5.6 on average |

## Interfaces compared

| Code | What the user sees | Selections per screen |
|---|---|---|
| `look_to_speak` | binary halving of the fixed vocabulary, left vs right (the Look to Speak pattern) | 1 of 2 |
| `grid9_fixed` | 3×3 page over the fixed vocabulary: 8 items + "next" | 1 of 9 |
| `row3_fixed` | one row of 3 over the fixed vocabulary: 2 items + "next" | 1 of 3 |
| `row3_scene` | one row of 3 over the **scene-grounded** list: 2 items + "next" | 1 of 3 |
| `row3_scene_confirm` | as above, plus a yes/no confirm after each item | 1 of 3, then 1 of 2 |

The fixed vocabulary is the 96 AAC items, ordered by how often they occur
across the E2 scenes — the best a pre-written list can do, exactly as in E2.

## Error model

- A selection lands on the intended zone with probability *a(k)* from E1b;
  otherwise it lands on one of the other zones, chosen uniformly. A wrong zone
  may be an item (wrong item selected) or "next" (the page moves on).
- A dwell that produces no answer (3.1%) costs one extra dwell.
- Without a confirm step, a wrong item is spoken: that is a **message error**.
- With a confirm step, the user is asked yes/no; the confirm itself is a
  2-zone selection with accuracy 0.771, so it can both catch errors and
  introduce them.
- If the wanted object is not in the scene-grounded list at all (measured:
  49% for Qwen at 12 items), the user pages to the end, then falls back to the
  fixed-vocabulary interface. That cost is charged to the scene-grounded
  method.

Nothing here models learning, fatigue or dwell tuning; those need Phase 2.

## Timing

0.5 s dwell + 0.3 s to settle and redraw = **0.8 s per selection**, stated as
an assumption and varied in the sensitivity analysis. Scene analysis is paid
once per message and is taken from E2's measured seconds per scene; the CPU
figure comes later from E5.

## Outcomes

- selections per message, and seconds per message;
- probability the wrong item is spoken;
- **effective bits per selection** (Wolpaw), so interfaces with different page
  sizes can be compared on one scale;
- messages per minute.

## Sensitivity (the part that makes this a design rule, not one number)

1. Per-selection accuracy swept from 0.60 to 0.95, to find where each layout
   wins and how much accuracy a 3×3 grid would need to be worth using.
2. Number of items per screen k from 2 to 9, at the measured accuracy for each
   k, to find the optimum.
3. Quality of the scene list: measured Qwen and CLIP curves, plus a sweep of
   "share of wanted objects in the top 3" from 0.1 to 0.9, to say how good a
   scene model has to be before scene grounding pays.

## What would refute C4

If `row3_scene` needs as many selections as `look_to_speak` or `row3_fixed`,
or if its message-error rate is higher at equal speed, then scene grounding
does not pay once gaze errors are included, and the paper says so. Given E2,
the risk is real: the wanted object is in Qwen's first screen only 31% of the
time, and in the fixed list's first screen 16% of the time.

## Reproducibility

Monte Carlo, 20,000 messages per configuration, one fixed seed, 95% CIs over
trials. `e4_sim.py` runs on a laptop CPU in under a minute; `smoke_test_e4.py`
checks the model against hand-computable cases (perfect accuracy, one item,
no scene model).
