# E1b findings: does holding the gaze longer make webcam gaze more accurate? (EOTT, v3, 21 Sep 2026)

Results: `results/setup/` (primary) and `results/participant/`
(sensitivity check). The superseded `results_v1/` and `results_v2/` (not published: superseded outputs are kept in the working tree and are available on request); see the
README in each.

## Data and timing
- **Data:** 51 participants (27 laptop, 24 desktop PC), 152,634 webcam frames
  at 29.7 fps. A face was detected in 99.95% of frames. The model was trained
  on 135,217 frames that have an eye-tracker label, with 10-fold
  cross-validation grouped by participant.
- **Clock offset found and corrected.** In the EOTT recordings, each laptop's
  webcam frames show the eye about **380 ms** later than their timestamps say.
  Desktops are off by about **40 ms**.
  - Laptops: 21 of 27 fall between 350 and 450 ms.
  - Desktops: all 24 fall between 20 and 70 ms.

  After a single correction per setup, the leftover lag has a **median of 27 ms,
  and 100% of participants are within ±200 ms**. Correcting each person
  individually gives the same results to within about 1–2 points.
- **Exception:** P_33 (laptop) has a weak signal at every lag (r = 0.30), and
  should be reported as a data-quality exception.
- **This offset is worth reporting for anyone who uses the EOTT webcam videos.**

## Result 1: the E1 numbers replicate on a second, independent dataset

Single frames, no calibration from the test person:

| Layout | E1 (MPIIFaceGaze, 15 people, still photos) | E1b (EOTT, 51 people, webcam video) |
|---|---|---|
| left / right | 91.6% | 81.2% |
| **3 across** | **82.7%** | **86.7%** (95% CI 83.6–89.1) |
| 2×2 | 69.0% | 54.9% |
| 3×3 | 46.7% | 48.0% (43.2–53.3) |
| top / bottom | 75.0% | 67.2% |

**3 across is the best layout on both datasets, and 3×3 stays below 50% on
both.** Vertical position remains the weak axis. In EOTT the vertical error
(0.21 of the screen height) is more than twice the horizontal error (0.096 of
the width).

## Result 2: dwelling longer does not help. The error is systematic, not jitter

Accuracy when a whole dwell is averaged, compared with a single frame from that
dwell (gaze-stability threshold 0.03):

| Layout | 0.5 s: single frame → dwell average | 1 s: single frame → dwell average |
|---|---|---|
| 3 across | 83.8% → 84.4% | 91.1% → 91.2% |
| 3×3 | 48.1% → 48.2% | 49.8% → 49.8% |
| left / right | 77.1% → 77.3% | 74.4% → 74.5% |

- **All four ways of combining a dwell** (single frame, mean, median, majority
  vote) agree to within about 1 point.
- **92–99% of the per-frame error is common to every frame of a dwell** (ICC
  0.92–0.99 on both axes, for both dwell lengths and all three stability
  thresholds).
- Averaging 15–30 frames therefore reduces the horizontal RMSE only from 0.096
  to 0.094 of the screen.
- The higher 1 s figure for 3 across (91% rather than 84%) is **not** an effect
  of dwelling: the single frame gives the same 91% on those windows. Stretches
  of steady gaze lasting a full second are simply a different, easier set of
  moments.

**Interpretation.** The webcam's error depends on where the person is looking
and how their head is posed at that moment. It does not come from random noise
that averages out over time. E1 pointed the same way: a per-person offset
explained only 10–25% of the error, and calibration added about 3 points.
**Neither longer dwells nor a simple calibration fixes it.** More accuracy has
to come from wider separation between targets, which means fewer zones, laid
out horizontally.

## Setup differences

On 3×3 and 4×4, desktop PCs are more accurate than laptops: 3×3 is 56–60% on PCs
against 37–41% on laptops. For 3 across, the two are closer (PC 87–92%, laptop
78–91%).

## What this settles for the paper
- **C1 is answered on two datasets.** With no per-user calibration, a webcam
  tells apart **3 horizontal zones at 83–87%** and 9 zones at under 50%, and
  neither calibration nor longer dwells change this materially.
- **The interface design follows:** present scene items **three at a time in a
  horizontal row**, with a short dwell (0.5 s; longer buys nothing). Because a
  misreading tends to repeat for the same target, every selection needs a
  **confirm/undo step**. This matches the authorship position in POSITIONING.md.
- **E4 is now fully specified.** It simulates Look to Speak's 2-way list halving
  against 3-way scene-ranked selection, using the measured per-frame confusion
  rates. Errors that repeat within a dwell should be modelled as one draw per
  selection, not as independent draws per frame.
- **Caveats to state:**
  - EOTT participants were able-bodied, at laptops and desktops, not people with
    ALS.
  - Screen positions are normalised to each screen.
  - Tobii Pro X3-120 gaze serves as ground truth.
