# E1c findings: does the accuracy come from the eyes or from the head? (24 Sep 2026)

Run: `E1c_ablation_colab.ipynb`. 51 EOTT participants, 5-fold cross-validation grouped by
participant, one-row three-zone accuracy. Chance is 0.333.

This is the ablation reported in Sec. 4.1.6 of the paper. It exists because of a question that
threatened the whole project: if a webcam gaze model is really reading **head orientation**,
then its accuracy says nothing about someone who cannot move their head — which is the
population this system is for.

## Result 1: it is the eyes, and the head features should be dropped

| Feature set | three-zone accuracy |
|---|---|
| all 39 features (what the first model used) | 0.793 |
| **eye landmarks and eye blendshapes only (21 features)** | **0.825** |
| head pose only (rotation, translation, nose) | 0.596 |

Paired over participants: **eye − all = +0.030, 95% bootstrap CI [+0.003, +0.061]**. The eye
features alone are *better* than the full set. **eye − head = +0.225, CI [+0.170, +0.282]**.

Head pose alone reaches 0.596, well above chance, so people do orient their heads toward what
they look at, and the full model was partly leaning on that. But head pose is not what carries
the result, and including it makes the model slightly worse.

MPIIFaceGaze agrees, and so does a per-session refit on the author's own frames in Study 5:
eye-only 0.642 against eye-plus-head 0.543. Three sources, same direction.

**What changed as a result.** The exported model trains on eye features only — 21 features, no
head pose. It is more accurate on held-out people, and it is the only version whose accuracy
can honestly be claimed for the target population. `Train_gaze_model_colab.ipynb` in `system/`
produces that model, and the interface consumes it.

Per-participant floor: eye-only accuracy has a minimum of 0.604 across the 51 people and a mean
of 0.828. No participant falls near chance.

## Result 2: a claim we withdrew

An earlier draft claimed that accuracy scales with iris resolution in pixels. **Within EOTT it
does not, and the correlation runs the other way.**

| Correlation with eye width in pixels, over 51 participants | Pearson | Spearman |
|---|---|---|
| accuracy, all features | −0.321 | −0.410 |
| accuracy, eye features only | −0.427 | −0.455 |
| accuracy, head features only | +0.069 | +0.065 |

| Tertile | mean eye width (px) | accuracy (all) | accuracy (eye only) |
|---|---|---|---|
| smallest third | 24.1 | 0.852 | 0.864 |
| middle | 31.2 | 0.790 | 0.848 |
| largest third | 39.9 | 0.751 | 0.771 |

EOTT eyes span 20–48 px — which brackets the 33 px at which our own laptop sat at chance — and
the participants with the *smallest* eyes in frame were predicted best. So pixel count is not
the mechanism, and the resolution law is withdrawn.

What survives, and is solidly evidenced on our own setup, is narrower and still consequential:
the same laptop, person and model went from correlation −0.007 and 0.314 accuracy at 640×480 to
+0.881 and 0.654 at 1280×720, with iris signal-to-noise rising from 0.50 to 7.1. Something
about that capture mode — plausibly sensor binning, compression or optics rather than pixel
count alone — destroyed the signal. The negative within-EOTT correlation is probably a
seating-distance confound: closer participants have larger eyes in frame and different
geometry. That is a guess, and it is labelled as one.

**The defensible claim, and the one the paper makes:** capture configuration can silently
reduce this pipeline to chance, and a per-session iris signal-to-noise check at calibration
detects it. Report the check, not a resolution law. `system/calib_analysis.py` computes it, and
`../study5_6_live_sessions/PROTOCOL.md` records resolution and eye width per session.
