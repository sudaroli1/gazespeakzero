# E1b (v3): dwell-level gaze-zone accuracy on EOTT (webcam video, Tobii ground truth)

Clock correction: **setup**. Webcam-to-Tobii lag estimated from stage-1 out-of-fold predictions, by setup (median ms): {'Laptop': 380.0, 'PC': 40.0}.

51 participants ({'Laptop': 27, 'PC': 24}), 152634 frames, face detected in 100.0%, median 29.7 fps; per-frame model trained on 135217 labelled frames (10-fold, grouped by participant).

**Timing check after correction:** best lag between predicted and Tobii x has median 27 ms; 100% of participants within ±200 ms.

## Windows found

| stability (std) | dwell | windows | participants | median per participant |
|---|---|---|---|---|
| 0.03 | 500 ms | 4582 | 49 | 94 |
| 0.03 | 1000 ms | 1223 | 49 | 23 |
| 0.02 | 500 ms | 3539 | 49 | 75 |
| 0.02 | 1000 ms | 901 | 44 | 18 |
| 0.05 | 500 ms | 5461 | 49 | 111 |
| 0.05 | 1000 ms | 1538 | 49 | 29 |

## Single frames (all labelled frames; comparable with E1)

| Grid | Accuracy | 95% CI | Laptop | PC |
|---|---|---|---|---|
| 1x2 | 0.812 | 0.787–0.831 | 0.805 | 0.819 |
| 2x1 | 0.672 | 0.636–0.707 | 0.635 | 0.715 |
| 1x3 | 0.867 | 0.836–0.891 | 0.849 | 0.888 |
| 2x2 | 0.549 | 0.512–0.583 | 0.511 | 0.593 |
| 3x3 | 0.480 | 0.432–0.533 | 0.408 | 0.562 |
| 4x4 | 0.318 | 0.284–0.354 | 0.279 | 0.362 |

## Dwell 500 ms (primary stability threshold 0.03)

| Grid | single frame | mean | median | vote | answered | mean, Laptop | mean, PC |
|---|---|---|---|---|---|---|---|
| 1x2 | 0.771 | 0.773 (0.736–0.804) | 0.774 | 0.774 | 0.97 | 0.771 | 0.775 |
| 2x1 | 0.646 | 0.649 (0.606–0.688) | 0.646 | 0.646 | 0.97 | 0.604 | 0.695 |
| 1x3 | 0.838 | 0.844 (0.801–0.871) | 0.845 | 0.845 | 0.97 | 0.817 | 0.873 |
| 2x2 | 0.512 | 0.519 (0.471–0.562) | 0.515 | 0.514 | 0.97 | 0.478 | 0.562 |
| 3x3 | 0.481 | 0.482 (0.420–0.546) | 0.484 | 0.484 | 0.97 | 0.387 | 0.582 |
| 4x4 | 0.299 | 0.306 (0.263–0.349) | 0.305 | 0.304 | 0.97 | 0.246 | 0.367 |

## Dwell 1000 ms (primary stability threshold 0.03)

| Grid | single frame | mean | median | vote | answered | mean, Laptop | mean, PC |
|---|---|---|---|---|---|---|---|
| 1x2 | 0.744 | 0.745 (0.673–0.790) | 0.745 | 0.745 | 0.98 | 0.713 | 0.777 |
| 2x1 | 0.668 | 0.681 (0.624–0.732) | 0.676 | 0.676 | 0.98 | 0.663 | 0.699 |
| 1x3 | 0.911 | 0.912 (0.870–0.938) | 0.912 | 0.912 | 0.98 | 0.914 | 0.910 |
| 2x2 | 0.488 | 0.499 (0.436–0.560) | 0.498 | 0.497 | 0.98 | 0.456 | 0.544 |
| 3x3 | 0.498 | 0.498 (0.420–0.574) | 0.499 | 0.501 | 0.98 | 0.396 | 0.603 |
| 4x4 | 0.274 | 0.285 (0.233–0.339) | 0.282 | 0.281 | 0.98 | 0.215 | 0.358 |

## Sensitivity: mean-of-dwell accuracy at other stability thresholds

| stability | dwell | 1x2 | 1x3 | 2x2 | 3x3 |
|---|---|---|---|---|---|
| 0.02 | 500 ms | 0.779 | 0.845 | 0.516 | 0.476 |
| 0.02 | 1000 ms | 0.752 | 0.927 | 0.476 | 0.492 |
| 0.03 | 500 ms | 0.773 | 0.844 | 0.519 | 0.482 |
| 0.03 | 1000 ms | 0.745 | 0.912 | 0.499 | 0.498 |
| 0.05 | 500 ms | 0.771 | 0.839 | 0.523 | 0.475 |
| 0.05 | 1000 ms | 0.763 | 0.896 | 0.523 | 0.490 |

## How much of the error is shared across a dwell

ICC near 1: averaging cannot help. Near 0: averaging removes most of the error.

| stability | dwell | axis | ICC | RMSE single frame | RMSE dwell mean | frames per window |
|---|---|---|---|---|---|---|
| 0.03 | 500 ms | x | 0.96 | 0.096 | 0.094 | 14.8 |
| 0.03 | 500 ms | y | 0.98 | 0.214 | 0.212 | 14.8 |
| 0.03 | 1000 ms | x | 0.93 | 0.096 | 0.093 | 29.5 |
| 0.03 | 1000 ms | y | 0.97 | 0.220 | 0.216 | 29.5 |
| 0.02 | 500 ms | x | 0.95 | 0.084 | 0.082 | 14.8 |
| 0.02 | 500 ms | y | 0.99 | 0.212 | 0.210 | 14.8 |
| 0.02 | 1000 ms | x | 0.92 | 0.085 | 0.082 | 29.6 |
| 0.02 | 1000 ms | y | 0.97 | 0.219 | 0.216 | 29.6 |
| 0.05 | 500 ms | x | 0.96 | 0.101 | 0.100 | 14.7 |
| 0.05 | 500 ms | y | 0.98 | 0.216 | 0.214 | 14.7 |
| 0.05 | 1000 ms | x | 0.93 | 0.102 | 0.099 | 29.1 |
| 0.05 | 1000 ms | y | 0.97 | 0.219 | 0.215 | 29.1 |

## QA

```
{
  "version": "v3 (clock correction: setup; stability windows; model on all labelled frames)",
  "clock_lag_median_ms_by_setup": {
    "Laptop": 380.0,
    "PC": 40.0
  },
  "n_participants": 51,
  "setups": {
    "Laptop": 27,
    "PC": 24
  },
  "n_frames": 152634,
  "face_detected": 0.9995217317242554,
  "frames_with_tobii_label": 0.8863097343973164,
  "median_tobii_dt_ms": 2.0,
  "median_fps": 29.65850037119525,
  "train_frames": 135217,
  "lag_median_ms": 27.0,
  "lag_within_200ms_frac": 1.0,
  "r_predx_tobiix_at_zero_median": 0.9494594086655925
}
```
