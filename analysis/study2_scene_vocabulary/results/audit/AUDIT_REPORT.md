# E2 human audit (blinded)

Rater file(s): audit_rater2.xlsx, audit_rater1.xlsx. Primary rater: audit_rater2.xlsx. 1045 items over 50 scenes.

## Per method (human judgement, top items of each method)

| method        |   scenes |   items_rated |   human_precision@3 | human_precision@3_ci   |   useful@3 | useful@3_ci      |   human_hit@3 | human_hit@3_ci   |   useful_hit@3 | useful_hit@3_ci   |   human_precision@6 | human_precision@6_ci   |   useful@6 | useful@6_ci      |
|:--------------|---------:|--------------:|--------------------:|:-----------------------|-----------:|:-----------------|--------------:|:-----------------|---------------:|:------------------|--------------------:|:-----------------------|-----------:|:-----------------|
| static        |       50 |           300 |              0.2533 | (0.1867, 0.32)         |     0.1333 | (0.0867, 0.1867) |          0.6  | (0.46, 0.74)     |           0.38 | (0.26, 0.52)      |              0.2    | (0.16, 0.2433)         |     0.0867 | (0.06, 0.1133)   |
| clip          |       50 |           300 |              0.5933 | (0.52, 0.6667)         |     0.2867 | (0.2, 0.3733)    |          0.98 | (0.94, 1.0)      |           0.54 | (0.4, 0.68)       |              0.4767 | (0.42, 0.53)           |     0.2433 | (0.19, 0.3)      |
| blip2_orig    |       50 |           150 |              0.1    | (0.06, 0.14)           |     0.0067 | (0.0, 0.02)      |          0.3  | (0.18, 0.44)     |           0.02 | (0.0, 0.06)       |              0.05   | (0.03, 0.07)           |     0.0033 | (0.0, 0.01)      |
| blip2_caption |       50 |           156 |              0.7733 | (0.7067, 0.84)         |     0.2467 | (0.1733, 0.3267) |          1    | (1.0, 1.0)       |           0.5  | (0.36, 0.64)      |              0.4167 | (0.3733, 0.4567)       |     0.1367 | (0.0933, 0.18)   |
| blip2_qa      |       50 |           145 |              0.68   | (0.6, 0.7533)          |     0.28   | (0.2067, 0.36)   |          0.96 | (0.9, 1.0)       |           0.58 | (0.44, 0.72)      |              0.3833 | (0.3367, 0.4267)       |     0.15   | (0.11, 0.1933)   |
| qwen_vl       |       50 |           272 |              0.78   | (0.6933, 0.8533)       |     0.3867 | (0.2867, 0.4867) |          0.96 | (0.9, 1.0)       |           0.64 | (0.5, 0.76)       |              0.68   | (0.6133, 0.74)         |     0.3533 | (0.2767, 0.4301) |

- `human_precision@K`: share of the first K items that the rater could point to in the photo.
- `useful@K`: share of the first K items that are both in the photo and something a person there might want or mention.
- `human_hit@3` / `useful_hit@3`: at least one such item on the first screen.

## Paired differences on the audited scenes

| a        | b          | metric            |   a_minus_b |   ci_lo |   ci_hi |   n_scenes |
|:---------|:-----------|:------------------|------------:|--------:|--------:|-----------:|
| qwen_vl  | clip       | human_precision@3 |      0.1867 |  0.0733 |  0.2933 |         50 |
| qwen_vl  | clip       | useful@3          |      0.1    | -0.02   |  0.22   |         50 |
| qwen_vl  | clip       | human_hit@3       |     -0.02   | -0.1    |  0.04   |         50 |
| qwen_vl  | clip       | useful_hit@3      |      0.1    | -0.06   |  0.26   |         50 |
| qwen_vl  | clip       | human_precision@6 |      0.2033 |  0.1333 |  0.27   |         50 |
| qwen_vl  | clip       | useful@6          |      0.11   |  0.04   |  0.1833 |         50 |
| qwen_vl  | static     | human_precision@3 |      0.5267 |  0.4267 |  0.62   |         50 |
| qwen_vl  | static     | useful@3          |      0.2533 |  0.16   |  0.3467 |         50 |
| qwen_vl  | static     | human_hit@3       |      0.36   |  0.22   |  0.5    |         50 |
| qwen_vl  | static     | useful_hit@3      |      0.26   |  0.1    |  0.4    |         50 |
| qwen_vl  | static     | human_precision@6 |      0.48   |  0.4133 |  0.5467 |         50 |
| qwen_vl  | static     | useful@6          |      0.2667 |  0.1933 |  0.3401 |         50 |
| clip     | static     | human_precision@3 |      0.34   |  0.2533 |  0.4267 |         50 |
| clip     | static     | useful@3          |      0.1533 |  0.0667 |  0.2467 |         50 |
| clip     | static     | human_hit@3       |      0.38   |  0.24   |  0.52   |         50 |
| clip     | static     | useful_hit@3      |      0.16   |  0      |  0.32   |         50 |
| clip     | static     | human_precision@6 |      0.2767 |  0.2167 |  0.3367 |         50 |
| clip     | static     | useful@6          |      0.1567 |  0.1033 |  0.2133 |         50 |
| qwen_vl  | blip2_qa   | human_precision@3 |      0.1    | -0.0067 |  0.1933 |         50 |
| qwen_vl  | blip2_qa   | useful@3          |      0.1067 |  0.0133 |  0.2002 |         50 |
| qwen_vl  | blip2_qa   | human_hit@3       |      0      | -0.06   |  0.06   |         50 |
| qwen_vl  | blip2_qa   | useful_hit@3      |      0.06   | -0.0605 |  0.2    |         50 |
| qwen_vl  | blip2_qa   | human_precision@6 |      0.2967 |  0.2333 |  0.36   |         50 |
| qwen_vl  | blip2_qa   | useful@6          |      0.2033 |  0.1367 |  0.2767 |         50 |
| clip     | blip2_qa   | human_precision@3 |     -0.0867 | -0.1733 |  0.0067 |         50 |
| clip     | blip2_qa   | useful@3          |      0.0067 | -0.0667 |  0.0733 |         50 |
| clip     | blip2_qa   | human_hit@3       |      0.02   | -0.04   |  0.1    |         50 |
| clip     | blip2_qa   | useful_hit@3      |     -0.04   | -0.18   |  0.1    |         50 |
| clip     | blip2_qa   | human_precision@6 |      0.0933 |  0.0367 |  0.15   |         50 |
| clip     | blip2_qa   | useful@6          |      0.0933 |  0.05   |  0.1333 |         50 |
| blip2_qa | static     | human_precision@3 |      0.4267 |  0.3333 |  0.5133 |         50 |
| blip2_qa | static     | useful@3          |      0.1467 |  0.0667 |  0.2267 |         50 |
| blip2_qa | static     | human_hit@3       |      0.36   |  0.22   |  0.52   |         50 |
| blip2_qa | static     | useful_hit@3      |      0.2    |  0.04   |  0.36   |         50 |
| blip2_qa | static     | human_precision@6 |      0.1833 |  0.1233 |  0.2367 |         50 |
| blip2_qa | static     | useful@6          |      0.0633 |  0.02   |  0.11   |         50 |
| qwen_vl  | blip2_orig | human_precision@3 |      0.68   |  0.58   |  0.7733 |         50 |
| qwen_vl  | blip2_orig | useful@3          |      0.38   |  0.28   |  0.4733 |         50 |
| qwen_vl  | blip2_orig | human_hit@3       |      0.66   |  0.52   |  0.8    |         50 |
| qwen_vl  | blip2_orig | useful_hit@3      |      0.62   |  0.48   |  0.76   |         50 |
| qwen_vl  | blip2_orig | human_precision@6 |      0.63   |  0.5666 |  0.6933 |         50 |
| qwen_vl  | blip2_orig | useful@6          |      0.35   |  0.2733 |  0.4267 |         50 |

## Sensitivity: generic names removed (area, object, room names)

| method        |   scenes |   items_rated |   human_precision@3 | human_precision@3_ci   |   useful@3 | useful@3_ci      |   human_hit@3 | human_hit@3_ci   |   useful_hit@3 | useful_hit@3_ci   |   human_precision@6 | human_precision@6_ci   |   useful@6 | useful@6_ci      |
|:--------------|---------:|--------------:|--------------------:|:-----------------------|-----------:|:-----------------|--------------:|:-----------------|---------------:|:------------------|--------------------:|:-----------------------|-----------:|:-----------------|
| static        |       50 |           300 |              0.2533 | (0.1867, 0.32)         |     0.1333 | (0.0867, 0.18)   |          0.6  | (0.46, 0.74)     |           0.38 | (0.24, 0.52)      |              0.2    | (0.1567, 0.2433)       |     0.0867 | (0.06, 0.1133)   |
| clip          |       50 |           300 |              0.5933 | (0.52, 0.6667)         |     0.2867 | (0.2, 0.3733)    |          0.98 | (0.94, 1.0)      |           0.54 | (0.4, 0.68)       |              0.4767 | (0.42, 0.53)           |     0.2433 | (0.19, 0.3001)   |
| blip2_orig    |       50 |            50 |              0.1    | (0.06, 0.14)           |     0.0067 | (0.0, 0.02)      |          0.3  | (0.18, 0.42)     |           0.02 | (0.0, 0.06)       |              0.05   | (0.03, 0.0733)         |     0.0033 | (0.0, 0.01)      |
| blip2_caption |       50 |           121 |              0.6133 | (0.54, 0.6867)         |     0.24   | (0.1667, 0.32)   |          0.96 | (0.9, 1.0)       |           0.5  | (0.36, 0.64)      |              0.3167 | (0.2767, 0.3567)       |     0.1233 | (0.0867, 0.1633) |
| blip2_qa      |       50 |           142 |              0.66   | (0.5867, 0.7333)       |     0.28   | (0.2067, 0.36)   |          0.96 | (0.9, 1.0)       |           0.58 | (0.44, 0.72)      |              0.3733 | (0.3267, 0.42)         |     0.15   | (0.11, 0.19)     |
| qwen_vl       |       50 |           271 |              0.78   | (0.6933, 0.8533)       |     0.3867 | (0.2933, 0.4867) |          0.96 | (0.9, 1.0)       |           0.64 | (0.5, 0.7605)     |              0.68   | (0.62, 0.74)           |     0.3533 | (0.28, 0.43)     |

## Human judgement vs the automatic LVIS+COCO labels

| method        |   items |   label_verdict |   agreement_with_labels |   label_correct_human_N |   label_wrong_human_Y |   unverifiable_items |   unverifiable_in_photo |   unverifiable_useful |
|:--------------|--------:|----------------:|------------------------:|------------------------:|----------------------:|---------------------:|------------------------:|----------------------:|
| static        |     300 |             258 |                  0.9302 |                      14 |                     4 |                   42 |                  0.0952 |                0.0952 |
| clip          |     300 |             155 |                  0.8258 |                      24 |                     3 |                  145 |                  0.3241 |                0.1379 |
| blip2_orig    |     150 |              50 |                  1      |                       0 |                     0 |                  100 |                  0      |                0      |
| blip2_caption |     156 |              70 |                  0.8571 |                      10 |                     0 |                   86 |                  0.7558 |                0.1744 |
| blip2_qa      |     145 |              94 |                  0.8404 |                      13 |                     2 |                   51 |                  0.7059 |                0.2157 |
| qwen_vl       |     272 |             162 |                  0.8086 |                      29 |                     2 |                  110 |                  0.6818 |                0.3455 |

## Second-pass review (a second person went over the same answers; this is NOT independent inter-rater agreement)

| method        |   items |   in_photo_changed |   in_photo_changed_pct |   useful_compared |   useful_changed |
|:--------------|--------:|-------------------:|-----------------------:|------------------:|-----------------:|
| blip2_caption |     156 |                  3 |                   1.92 |               123 |                3 |
| blip2_orig    |     150 |                  0 |                   0    |                15 |                0 |
| blip2_qa      |     145 |                  3 |                   2.07 |               115 |                3 |
| clip          |     300 |                  5 |                   1.67 |               143 |                6 |
| qwen_vl       |     272 |                  3 |                   1.1  |               204 |                9 |
| static        |     300 |                  0 |                   0    |                60 |                2 |
| ALL           |    1323 |                 14 |                   1.06 |               660 |               23 |

