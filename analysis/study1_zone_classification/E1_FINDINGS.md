# E1 findings: webcam gaze-zone accuracy on MPIIFaceGaze (run 19 Sep 2026)

Run on Colab, and reproduced afterwards from the saved feature files. Raw report: `results/E1_REPORT.md`. Follow-up analyses:
`results/e1_bits_per_selection.csv` and `results/e1_bias_vs_scatter*.{csv,json}`.

## The data is sound

- **Frames:** 15 subjects, **37,667 frames**, which is exactly the number
  MPIIFaceGaze states for the dataset. The per-subject counts differ (1,498–2,929)
  because the dataset is built that way; no frames were lost.
- **Face detection:** a face was found in 99.8% of frames (lowest subject 96.4%).
  No images were unreadable.
- **Landmark check:** MediaPipe's eye corners fall within 0.04 interocular
  distances of the dataset's hand-annotated corners (median). Only 0.01% of
  frames are off by more than 0.2.
- **Targets:** 0.65% of gaze targets lie just off the screen edge and are
  counted in the edge zone.
- **Reproducibility:** re-running the analysis from the saved features gives
  identical ridge results. The gradient-boosting results differ by at most
  **0.003** in accuracy, because the Colab and workspace library builds differ.
  For the paper, pin the library versions and report several seeds.

## 1. The original estimator does not track gaze

The original GazeSpeakZero estimator (`mean(iris) − nose + 0.5`, thresholds at
thirds) returns **zone 4, the centre, for 96.8% of frames** and zone 1 for 3.0%.
Its 3×3 accuracy is **11.3%, where chance is 11.1%**.

Its input numbers stay in a narrow band:

- the horizontal value (x) stays between 0.478 and 0.522 (1st–99th percentile);
- the vertical value (y) stays between 0.310 and 0.441.

The original thresholds sit at 0.333 and 0.666, so the output is almost always
the centre. Even a model *trained* on these two numbers (M0-fit) stays at chance
on every grid. The information isn't in the feature at all.

**Consequence:** the ICVGIP numbers (87.3% intent accuracy, and so on) could not
have come from this code. Nothing from that draft survives.

## 2. What a webcam can do with no calibration from the user (M2, gradient boosting, leave-one-subject-out)

| Layout | Zones | Accuracy (mean of 15 people) | 95% CI | Worst person | Bits per selection |
|---|---|---|---|---|---|
| left / right | 2 | **0.916** | 0.900–0.927 | 0.852 | 0.59 |
| top / bottom | 2 | 0.750 | 0.711–0.791 | 0.620 | 0.21 |
| **3 across** | 3 | **0.827** | 0.803–0.848 | 0.739 | **0.76** |
| 2×2 | 4 | 0.690 | 0.646–0.734 | 0.549 | 0.64 |
| 3×3 | 9 | 0.467 | 0.427–0.518 | 0.355 | 0.60 |
| 4×4 | 16 | 0.338 | 0.302–0.391 | 0.242 | 0.51 |

"Bits per selection" uses the standard Wolpaw formula, averaged over people.
Every figure is **per single frame**; see section 4.

- **Three zones in a row carry the most information per frame** (0.76 bits).
  Adding more zones lowers accuracy faster than it adds choices.
- **Horizontal gaze is much easier than vertical.** Left/right is 91.6% accurate
  but top/bottom only 75.0%. The vertical error is also larger: 35 mm of scatter
  against 29 mm horizontally, on a screen only about 180 mm tall against about
  290 mm wide.
- **The 3×3 grid in the original design is not supported:** fewer than half of
  single frames land in the right cell.
- **Head pose adds little:** eye features alone (M1) come within 0–5 points of M2 (the largest gap is 3 across: 78.2% vs 82.7%).
- **Median on-screen error is 39 mm** (mean 43, 90th percentile 78).

## 3. Calibration barely helps, and we now know why

The "first session" scheme calibrates on day 1 and scores the later days.

| Layout | No calibration | k = 1 | k = 5 | k = 16 |
|---|---|---|---|---|
| 3 across | 0.827 | 0.775 | 0.809 | 0.837 |
| 2×2 | 0.690 | 0.617 | 0.689 | 0.722 |
| 3×3 | 0.467 | 0.388 | 0.459 | 0.493 |

- **Sixteen calibration frames add at most about 3 points.**
- **One calibration frame makes things worse**, because the offset is learned
  from a single noisy frame.

Why: splitting the error shows that a **per-person constant offset — the only
thing a calibration can remove — accounts for just 10% of the squared error
horizontally and 25% vertically.** The rest is frame-to-frame scatter:

- horizontal: 29 mm, about 10% of screen width;
- vertical: 35 mm, about 20% of screen height.

A person's offset is small (RMS 9 mm horizontally, 21 mm vertically), so the
population model is not badly miscalibrated for new people. It is noisy for
everyone.

**This supports the positioning:** calibration is not where the gain is, so
"calibration-free" costs little. It also undercuts calibration-free as a
selling point, since calibrating costs little too. Either way, the bottleneck
is frame-level noise.

## 4. The limitation that decides the next experiment

MPIIFaceGaze is a set of **still images**. A real interface decides from a
**dwell** of about 0.5–1 s (15–30 frames at 30 fps). If the scatter were
independent from frame to frame, averaging a dwell would shrink it by roughly
√15–√30 and lift 3×3 accuracy a long way. But within a dwell the head and eyes
barely move, so much of the error is probably shared across frames and would
not average out. **Still images cannot tell these two cases apart.** We cannot
claim any dwell-level accuracy from E1, and the interface design (3 across vs
3×3) cannot be settled until we measure it on video.

→ **New experiment E1b: dwell-level accuracy on video.** It needs a dataset of
webcam video in which people look at known on-screen points. The best fit is
**EVE** (Park et al., ECCV 2020, ETH Zürich): user-facing webcam views with
on-screen gaze targets, available on request through a Google Form under
CC BY-NC-SA 4.0 ([ait.ethz.ch/eve](https://ait.ethz.ch/eve)). **The user needs
to submit that request.** The backup is to record the authors themselves;
check with the institution whether that needs ethics approval.

## What this means for the claims (see POSITIONING.md)

**C1 (answered for single frames):** with no per-user calibration, a laptop
webcam separates **3 horizontal zones at 82.7%** (worst person 73.9%) and
**2 at 91.6%**. It separates **9 zones at only 46.7%**. Calibration with up to
16 frames adds about 3 points.

**The concession we wrote down has partly come true.** A single frame cannot
reliably tell more than about three zones apart, so unless dwell averaging
changes the picture (E1b):

- the scene vocabulary should be offered as **three items at a time in a
  horizontal row**, not as a 3×3 partition of the scene;
- the head-to-head with Look to Speak (E4) becomes a clean comparison: a
  **3-way, scene-ranked choice against 2-way list halving**, under measured
  error rates;
- the paper's advantage has to come from the **vocabulary** (C2–C4), not from
  finer gaze.

**For the paper's method section:** we report the original estimator's failure
as a negative control (it shows a plausible-looking pipeline can sit at chance),
without dwelling on the history.
