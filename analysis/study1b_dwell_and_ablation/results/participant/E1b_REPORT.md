# E1b (v3): dwell-level gaze-zone accuracy on EOTT (webcam video, Tobii ground truth)

Clock correction: **participant**. Webcam-to-Tobii lag estimated from stage-1 out-of-fold predictions, by setup (median ms): {'Laptop': 380.0, 'PC': 40.0}.

51 participants ({'Laptop': 27, 'PC': 24}), 152634 frames, face detected in 100.0%, median 29.7 fps; per-frame model trained on 135219 labelled frames (10-fold, grouped by participant).

**Timing check after correction:** best lag between predicted and Tobii x has median -6 ms; 92% of participants within ±200 ms.

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
| 1x2 | 0.802 | 0.772–0.824 | 0.789 | 0.816 |
| 2x1 | 0.674 | 0.634–0.709 | 0.630 | 0.723 |
| 1x3 | 0.854 | 0.808–0.884 | 0.815 | 0.899 |
| 2x2 | 0.547 | 0.506–0.583 | 0.502 | 0.598 |
| 3x3 | 0.468 | 0.419–0.520 | 0.385 | 0.561 |
| 4x4 | 0.308 | 0.272–0.345 | 0.262 | 0.360 |

## Dwell 500 ms (primary stability threshold 0.03)

| Grid | single frame | mean | median | vote | answered | mean, Laptop | mean, PC |
|---|---|---|---|---|---|---|---|
| 1x2 | 0.765 | 0.766 (0.729–0.797) | 0.765 | 0.765 | 0.97 | 0.758 | 0.774 |
| 2x1 | 0.653 | 0.653 (0.603–0.695) | 0.657 | 0.657 | 0.97 | 0.595 | 0.714 |
| 1x3 | 0.828 | 0.827 (0.773–0.861) | 0.830 | 0.831 | 0.97 | 0.780 | 0.876 |
| 2x2 | 0.522 | 0.522 (0.471–0.570) | 0.525 | 0.525 | 0.97 | 0.472 | 0.575 |
| 3x3 | 0.468 | 0.465 (0.409–0.523) | 0.469 | 0.469 | 0.97 | 0.366 | 0.568 |
| 4x4 | 0.301 | 0.304 (0.263–0.347) | 0.305 | 0.304 | 0.97 | 0.245 | 0.366 |

## Dwell 1000 ms (primary stability threshold 0.03)

| Grid | single frame | mean | median | vote | answered | mean, Laptop | mean, PC |
|---|---|---|---|---|---|---|---|
| 1x2 | 0.733 | 0.741 (0.667–0.785) | 0.740 | 0.740 | 0.98 | 0.701 | 0.782 |
| 2x1 | 0.668 | 0.658 (0.589–0.711) | 0.670 | 0.670 | 0.98 | 0.606 | 0.713 |
| 1x3 | 0.899 | 0.897 (0.839–0.933) | 0.900 | 0.898 | 0.98 | 0.879 | 0.915 |
| 2x2 | 0.489 | 0.504 (0.439–0.564) | 0.498 | 0.498 | 0.98 | 0.453 | 0.557 |
| 3x3 | 0.497 | 0.477 (0.403–0.550) | 0.478 | 0.481 | 0.98 | 0.382 | 0.576 |
| 4x4 | 0.268 | 0.273 (0.221–0.328) | 0.270 | 0.272 | 0.98 | 0.189 | 0.360 |

## Sensitivity: mean-of-dwell accuracy at other stability thresholds

| stability | dwell | 1x2 | 1x3 | 2x2 | 3x3 |
|---|---|---|---|---|---|
| 0.02 | 500 ms | 0.767 | 0.835 | 0.523 | 0.466 |
| 0.02 | 1000 ms | 0.718 | 0.915 | 0.474 | 0.508 |
| 0.03 | 500 ms | 0.766 | 0.827 | 0.522 | 0.465 |
| 0.03 | 1000 ms | 0.741 | 0.897 | 0.504 | 0.477 |
| 0.05 | 500 ms | 0.765 | 0.824 | 0.527 | 0.463 |
| 0.05 | 1000 ms | 0.757 | 0.877 | 0.523 | 0.477 |

## How much of the error is shared across a dwell

ICC near 1: averaging cannot help. Near 0: averaging removes most of the error.

| stability | dwell | axis | ICC | RMSE single frame | RMSE dwell mean | frames per window |
|---|---|---|---|---|---|---|
| 0.03 | 500 ms | x | 0.95 | 0.112 | 0.110 | 14.8 |
| 0.03 | 500 ms | y | 0.98 | 0.214 | 0.212 | 14.8 |
| 0.03 | 1000 ms | x | 0.93 | 0.116 | 0.112 | 29.4 |
| 0.03 | 1000 ms | y | 0.97 | 0.221 | 0.217 | 29.4 |
| 0.02 | 500 ms | x | 0.95 | 0.103 | 0.101 | 14.8 |
| 0.02 | 500 ms | y | 0.98 | 0.214 | 0.212 | 14.8 |
| 0.02 | 1000 ms | x | 0.92 | 0.109 | 0.105 | 29.6 |
| 0.02 | 1000 ms | y | 0.97 | 0.222 | 0.219 | 29.6 |
| 0.05 | 500 ms | x | 0.95 | 0.116 | 0.114 | 14.7 |
| 0.05 | 500 ms | y | 0.98 | 0.216 | 0.215 | 14.7 |
| 0.05 | 1000 ms | x | 0.93 | 0.119 | 0.115 | 29.1 |
| 0.05 | 1000 ms | y | 0.97 | 0.220 | 0.216 | 29.1 |

## QA

```
{
  "version": "v3 (clock correction: participant; stability windows; model on all labelled frames)",
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
  "train_frames": 135219,
  "lag_median_ms": -6.0,
  "lag_within_200ms_frac": 0.9215686274509803,
  "r_predx_tobiix_at_zero_median": 0.9474540106843881
}
```
