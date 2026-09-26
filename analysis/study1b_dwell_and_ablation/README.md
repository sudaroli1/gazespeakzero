# Study 1b — dwell time, calibration, and the eyes-only ablation (Sec. 4.1.4-4.1.6)

Three questions that Study 1's single-frame design cannot answer, on a second and
independent dataset.

1. **Does holding the gaze longer make the estimate better?** Barely. Pooling frames over a
   dwell window raises accuracy by a few points and then flattens, because the per-frame
   errors inside one dwell are correlated (ICC 0.92-0.99): averaging correlated errors does
   not cancel them. This is the finding that makes the paper's central claim inevitable
   rather than surprising.
2. **What does 30 seconds of calibration buy?** Less than the literature implies, and the
   reason is regression dilution — `E1b_reanalyze_colab.ipynb` is the corrected analysis, and
   `E1b_FINDINGS.md` says what the first one got wrong.
3. **Does the accuracy come from the eyes, or from head pose?** From the eyes. This is the
   ablation in `E1c_ablation_colab.ipynb`, and it is what makes the whole approach relevant to
   someone who cannot turn their head. Without it the paper would be measuring head pointing.

## What you need

The **Eye of the Typer** dataset (EOTT) and its `participant_characteristics.csv`, from its
providers. We cannot redistribute it. 51 participants, 152,634 frames at 29.7 fps.

One property of that dataset matters and is easy to miss: **the laptop recordings' webcam
frames show the eye about 380 ms later than their timestamps claim** (desktops, about 40 ms).
`eott_extract.py` finds and corrects that offset, and `results/*/e1b_clock_lags.csv` reports
it per participant. An uncorrected analysis silently pairs each frame with the wrong gaze
target.

## Order of operations

```
python eott_extract.py --zip eott.zip --chars participant_characteristics.csv \
       --model face_landmarker.task --out features
python eott_analyze.py --features features --out results/setup
```

`results/setup/` is the primary analysis (the recording setup grouping) and
`results/participant/` is the sensitivity check; both are reported.

`build_notebook_e1b.py`, `build_reanalyze_nb.py` regenerate the Colab notebooks from these
same files, inlining `study1_zone_classification/extract_features.py` and `analyze.py` so the
notebook runs the same code as the local scripts.

## Check it without the dataset

```
python smoke_test_e1b.py
```

Synthesises a short video per participant with a known gaze pattern, runs the real extractor
and analysis, and asserts on the output. Needs `av` (`pip install av`) as well as MediaPipe.

## Results in this folder

| File | What it is |
|---|---|
| `results/setup/e1b_dwell_accuracy.csv` | accuracy against dwell length — the flattening curve |
| `results/setup/e1b_frame_accuracy.csv` | the single-frame baseline on this dataset |
| `results/setup/e1b_shared_error.csv` | the ICC: how much of the error is shared within a dwell |
| `results/setup/e1b_window_counts.csv` | how many frames fall inside each window length |
| `results/setup/e1b_clock_lags.csv`, `e1b_lag_check.csv` | the clock offset, and the check that fixing it helped |
| `results/setup/e1b_qa.json` | frame counts, detection rate, and the train/test grouping |
| `results/participant/` | the same analysis grouped by participant instead of setup |
| `results/*/E1b_REPORT.md` | each run's own report, as written |

`E1b_FINDINGS.md` is the readable account. Study 4 takes its gaze-accuracy parameters from
`results/setup/`.
