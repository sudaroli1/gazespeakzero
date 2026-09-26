# E4 findings: how long is a message, and how often is it wrong? (23 Sep 2026)

Design fixed before any number was produced: `E4_DESIGN.md`. Code: `e4_sim.py`
(20,000 simulated messages per interface, seed 0); inputs: `e4_build_inputs.py`.
Every parameter comes from E1b (gaze accuracy) or E2 (where the wanted object
sits in the offered list). Figures: `results/fig_e4_tradeoff.pdf`,
`results/fig_e4_accuracy.pdf`.

## The result that reframes the paper

**At calibration-free webcam accuracy, the binding constraint is not speed but
error.** Every unguarded layout speaks the wrong message about half the time or
worse:

| Interface | can say | s per attempt | wrong message | s per correct message |
|---|---|---|---|---|
| 3×3 grid, fixed list | 100% | **1.3** | **77%** | 5.6 |
| Look to Speak, 16 items | 54% | 3.3 | 64% | 17.2 |
| row of 3, scene list | 100% | 5.1 | 47% | 9.6 |
| Look to Speak, 96 items | 100% | 5.8 | 84% | 35.1 |
| row of 3, scene, confirm step | 100% | 9.9 | 24% | 13.0 |
| **row of 3, scene, repeat-guard** | 100% | 11.7 | **11%** | **13.2** |
| row of 3, fixed list, repeat-guard | 100% | 14.3 | 18% | 17.6 |
| **scanning row of 3, scene, repeat-guard** | 100% | 19.1 | **1.9%** | 19.4 |

"Repeat-guard" = the item is accepted only when the same zone is selected
twice in a row. "Can say" = the share of wanted objects the interface's
vocabulary contains at all (a 16-item phrase list covers 54%).

Three claims follow, each with the number that supports it.

1. **A guard is not optional.** Without one, the fastest layouts are the worst:
   the 3×3 grid answers in 1.3 s and is wrong 77% of the time. With a repeat
   guard, the scene row costs 2.3× the time and cuts errors from 47% to 11%.
2. **Scene grounding pays, at equal coverage and equal interface.** Row of 3
   with the guard: scene list 11.7 s and 11% wrong, fixed list 14.3 s and 18%
   wrong — 18% faster with 39% fewer wrong messages, because the wanted object
   is in the scene list's first screen 31% of the time against 16% for the best
   fixed ordering (E2). A short 16-item phrase list is quicker per attempt but
   cannot say half of what the person wants.
3. **Scanning beats direct selection when gaze is poor.** Letting the page
   advance by itself means one decision per message instead of several: 1.9%
   wrong against 11%, for 7 s more. The measured accuracy is not high enough
   for direct selection to be safe.

## The design rule (`fig_e4_accuracy`, and `results/e4_sensitivity.csv`)

To keep wrong messages under 5%, the per-selection accuracy has to be:

| Interface | accuracy needed for ≤5% wrong |
|---|---|
| row of 3, no guard | above 0.95 (never reached in the sweep) |
| row of 3, repeat-guard | 0.90 |
| scanning row of 3, no guard | above 0.95 |
| **scanning row of 3, repeat-guard** | **0.80** |

(The sweep steps in 0.05, so these are the first grid points at or below 5%.)

E1b measured 0.838 with no calibration. **Only the guarded scanning design
clears the bar at the accuracy this system actually has.** That is the
recommendation for Phase 2, and it is derived, not chosen.

Two further knobs:

- **Items per screen.** At each layout's own measured accuracy, 3 zones is the
  best compromise (guarded scanning: 19.4 s per correct message at 1.9% wrong);
  9 zones is faster (13.8 s) but 13% wrong; 2 zones is slower and no safer,
  because the 2-zone split puts the boundary in the middle of the screen where
  most fixations fall.
- **Scan speed.** Advancing every 2 s instead of 3 s cuts a correct message
  from 19.7 s to 13.6 s with no change in error (1.9%). Phase 2 should tune
  this per person; it is the cheapest available speed-up.

## What better vision would buy (`share_in_first_screen` sweep)

Holding everything else fixed, raising the share of wanted objects in the first
screen of three:

| Share in first screen | s per correct message (guarded row of 3) |
|---|---|
| 0.31 (measured, Qwen2.5-VL) | 13.2 |
| 0.50 | 8.6 |
| 0.70 | 5.8 |
| 0.90 | 4.1 |

So roughly **one second saved per message for every 10 points** of first-screen
hit rate. This is the argument for the vision stage stated in the unit the
clinic cares about, and it is also the argument for E2's next step: the audit
showed only 39% of Qwen's first-screen items are both present and worth
offering, so re-ranking by usefulness is where the remaining time is.

## Honest limits (all of these go in the paper)

- **The accuracy figures are per-frame zone classification from E1b, used as if
  they were per-selection accuracies in a live interface.** A real dwell with
  large targets and visual feedback would likely do better; nobody has measured
  that yet, which is exactly why the accuracy sweep is the main figure rather
  than the single operating point.
- A wrong selection is modelled as landing uniformly on another zone. E1b did
  not produce a confusion matrix, so neighbour-biased errors are not modelled.
- 0.8 s per selection (0.5 s dwell + 0.3 s redraw) is an assumption, stated and
  swept for the scan case only.
- The model has no learning, no fatigue, no per-person dwell tuning, and no
  caregiver interpretation — all of which matter and none of which can be
  measured without participants.
- "Wrong message spoken" counts the item, not its consequences; saying "I need
  the toilet" when you meant "I am cold" is not the same cost as the reverse.
  The paper should say so rather than pretend the metric is neutral.
- The scene list is 12 items deep; the fallback to the full vocabulary is
  charged to the scene methods, which is the honest direction.
