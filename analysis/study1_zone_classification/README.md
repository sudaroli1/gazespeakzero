# Study 1 — zone classification from an ordinary webcam (Sec. 4.1)

**Question.** Given one webcam frame and no calibration from the person in it, which region
of the screen are they looking at?

**Answer.** Three zones in a row: **0.838** held out across subjects. Nine zones: 0.526.
Two rows: 0.652. The layout that works is a single row, and the paper's live studies use it.

## What you need

MPIIFaceGaze, from its providers (Max Planck Institute for Informatics). We cannot
redistribute it. 15 subjects, 37,667 frames — the count the dataset states, which is one of
the checks in `results/e1_qa.json`.

Also `face_landmarker.task`, downloaded as the top-level README describes.

## Order of operations

```
python extract_features.py --data MPIIFaceGaze --model face_landmarker.task --out features
python analyze.py --features features --out results
python extra_analysis.py                  # bits per selection, bias vs scatter
```

`extract_features.py` is the one file the rest of the repository imports: the system in
`system/` builds its live features with the same code that built the training features, so
the model cannot be fed differently at run time than it was at fit time. That is the reason
this folder is a dependency of `system/` rather than a leaf.

`E1_gaze_zone_colab.ipynb` runs the same two steps on Colab; `build_notebook.py` regenerates
it from these files.

## Check it without the dataset

```
python smoke_test.py
```

Builds synthetic frames with a known gaze direction, runs the real feature extractor and the
real model over them, and asserts on the result. It needs MediaPipe and the landmarker file
but no dataset.

## Results in this folder

| File | In the paper |
|---|---|
| `results/e1_zone_accuracy.csv` | the zone-accuracy table and `figures/fig_zone_accuracy.pdf` |
| `results/e1_per_subject.csv` | the spread across the 15 subjects |
| `results/e1_calibration.csv`, `..._raw.csv` | Sec. 4.1.5, what calibration buys |
| `results/e1_mm_error.csv` | the angular error, for comparison with published figures |
| `results/e1_bits_per_selection.csv` | the information-rate comparison in Sec. 4.4 |
| `results/e1_bias_vs_scatter*.{csv,json}` | Sec. 3.2, that the error is bias, not scatter |
| `results/e1_qa.json` | the data-integrity checks: frame counts, detection rate, landmark sanity |
| `results/confusion_*.png` | confusion matrices per layout and model |
| `results/E1_REPORT.md` | the run's own report, as written |

`E1_FINDINGS.md` is the readable account, including the negative control (a model trained on
shuffled labels reaches chance) and what Study 1 does **not** establish.
