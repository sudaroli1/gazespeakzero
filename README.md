# Seeing is not selecting

Code, data and figures for *"Seeing is not selecting: measuring a webcam-only gaze
communication aid"*.

The archived release the paper cites is **[10.5281/zenodo.22972781](https://doi.org/10.5281/zenodo.22972781)**. This repository
is where the work continues; the DOI is the fixed snapshot.

The paper's claim is that **per-frame benchmark accuracy does not predict live
per-selection accuracy**: the same gaze stage that scores 0.838 on a standard dataset
supports about half that when a person uses it to choose a word. This repository is
arranged so that claim, and every number supporting it, can be checked rather than taken
on trust — including the results we withdraw and the faults we found in our own software.

Nothing here needs a GPU except the two vision/language studies, which ship the notebooks
that produced their outputs on Colab, and the outputs themselves.

## Where things are

```
system/                      the communication aid itself: capture, gaze stage, interface
analysis/
  study1_zone_classification/        Study 1  - zone accuracy on MPIIFaceGaze
  study1b_dwell_and_ablation/        Study 1b - dwell time, and the eyes-only ablation
  study2_scene_vocabulary/           Study 2  — scene-grounded vocabulary
  study3_message_identification/     Study 3  — objects to message
  study4_simulation/                 Study 4  — end-to-end Monte Carlo
  study5_6_live_sessions/            Studies 5 and 6 — protocol, consent, analysis
data/
  sessions/study5_author/            the raw session logs behind Study 5
figures/                     the figures as they appear in the paper
```

The working folders were called `e1`, `e1b`, `e2`, `e3`, `e4`, `study` while the work was
being done, and the notebooks and reports inside them still use those names. The published
folders are named after the study they belong to, because a reader arrives with the paper
and not with our shorthand. `make_release.py` (in the working tree, not here) performs that
renaming and rewrites every cross-folder reference, so the two cannot drift apart.

| Paper | Folder | Old name |
|---|---|---|
| Study 1, Sec. 4.1 | `analysis/study1_zone_classification` | `e1` |
| Study 1b: dwell, calibration, ablation, Sec. 4.1.4-4.1.6 | `analysis/study1b_dwell_and_ablation` | `e1b`, `e1c` |
| Study 2, Sec. 4.2 | `analysis/study2_scene_vocabulary` | `e2` |
| Study 3, Sec. 4.3 | `analysis/study3_message_identification` | `e3` |
| Study 4, Sec. 4.4 | `analysis/study4_simulation` | `e4` |
| Study 5, Sec. 4.5 | `analysis/study5_6_live_sessions` | `study` |
| Study 6, Sec. 4.6 | `analysis/study5_6_live_sessions` | `study`, `e6` |

Every folder has a `README.md` that says what the scripts do, in what order, and which
table or figure of the paper each output belongs to.

## Install

Python 3.11 or 3.12. MediaPipe and scikit-learn have no wheels for 3.13 or later.

```
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate elsewhere
pip install -r requirements.txt
```

Two model files are not in this repository. `system/gaze_model.joblib` is ours and *is*
included. `face_landmarker.task` is Google's and is downloaded rather than redistributed:

```
curl -L -o system/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

## Checking each claim

Every command below runs in a minute or less on a laptop CPU, from the folder shown.

| Claim | Command | Folder |
|---|---|---|
| The selection logic does what the paper says | `python test_engine.py` — 31 tests | `system/` |
| Study 1's pipeline is sound end to end | `python smoke_test.py` | `analysis/study1_zone_classification/` |
| Study 1b's dwell analysis is sound | `python smoke_test_e1b.py` | `analysis/study1b_dwell_and_ablation/` |
| Study 3's scoring is sound | `python smoke_test_e3.py` — 27 tests | `analysis/study3_message_identification/` |
| Study 4's simulator is sound | `python smoke_test_e4.py` — 20 tests | `analysis/study4_simulation/` |
| Study 4's numbers, from its inputs | `python e4_sim.py` then `python e4_figures.py` | `analysis/study4_simulation/` |
| Study 5's numbers, from the raw logs | `python analyse_study.py --out results` | `analysis/study5_6_live_sessions/` |
| Study 6's numbers, from the raw logs | `python verify_paper_numbers.py --sessions <folder>` | `analysis/study5_6_live_sessions/` |

The smoke tests build synthetic inputs with a known answer and assert on the result; they
check the analysis code, not the findings. The two commands that recompute published
numbers are `analyse_study.py` and `verify_paper_numbers.py`. The latter re-derives all 25
numbers in Table 6 and Sec. 4.6 and exits non-zero if any of them disagrees with the paper.

Studies 1, 1b, 2 and 3 depend on datasets we cannot redistribute (MPIIFaceGaze, Eye of the
Typer, LVIS, COCO). Their folders explain what to obtain and from whom, and each ships the
notebook that was actually run, plus the outputs it produced, so the scoring stage can be
re-run without the raw data.

## What is deliberately not here

`EXCLUDED.json` lists it, with the reason for each item. In short: no photograph or video
of any person, the blinded audit answer keys, superseded working copies, and Google's
model file. **Study 6's two session logs are also not here** — the operators have given
written consent, but the folder waits on one open question about institutional review, and
it is easier to add a folder later than to unpublish one. Section 4.6's numbers can be
verified the moment it is added; the command is in
`analysis/study5_6_live_sessions/README.md`.

## Honest notes

- Study 5 has one participant, who is an author. Study 6 has two, neither from the
  intended population, and one of its two sessions ran at a quarter of the intended loop
  rate. **None of these are estimates of how the system serves people with motor
  impairment**, and the paper makes no such claim.
- Three recommendations in this work reverse earlier recommendations in the same work. The
  superseded analyses are described rather than deleted.
- The system's history includes a smoothing window denominated in frames instead of
  milliseconds, a readiness check that timed the camera instead of the pipeline, and a cue
  chosen before the interface reset its page. Each is fixed, each has a regression test
  where one was possible, and each is in the paper, because the faults were more
  informative than the successes.
- Institutional ethics review was not sought for Studies 5 and 6. Both operators gave
  written informed consent, no image or video of any person exists, and the paper's ethics
  statement says exactly this rather than implying an approval that was not obtained.

## Licence and citation

Code: MIT (`LICENSE`). Session logs and audit workbooks: CC BY 4.0. Third-party datasets
and models are under their own licences and are not redistributed. `CITATION.cff` has the
citation metadata.
