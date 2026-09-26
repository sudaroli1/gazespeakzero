# E3: from selected objects to the intended message

240 cases (60 intents x 4 conditions), methods: embed, lm_choice_phi3.5, lm_choice_qwen1.5b, lm_choice_qwen3b, lm_choice_smol1.7b, lm_gen_phi3.5, lm_gen_qwen1.5b, lm_gen_qwen3b, lm_gen_smol1.7b, lm_pmi_phi3.5, lm_pmi_qwen1.5b, lm_pmi_qwen3b, lm_pmi_smol1.7b, lm_rank_phi3.5, lm_rank_qwen1.5b, lm_rank_qwen3b, lm_rank_smol1.7b, prior, template.

## Summary (top-1 = offered first, top-3 = on the first screen of candidate messages)

| method             |   cases |   median_seconds |   top1 | top1_ci          |   top3 | top3_ci          |   top5 | top5_ci          |   top1_clean |   top3_clean |   top1_partial |   top3_partial |   top1_wrong_label |   top3_wrong_label |   top1_wrong_pick |   top3_wrong_pick |   top3_needs |   top3_information |   top3_social |   top3_etiquette |
|:-------------------|--------:|-----------------:|-------:|:-----------------|-------:|:-----------------|-------:|:-----------------|-------------:|-------------:|---------------:|---------------:|-------------------:|-------------------:|------------------:|------------------:|-------------:|-------------------:|--------------:|-----------------:|
| prior              |     240 |          0.0001  | 0.5375 | (0.475, 0.6042)  | 0.65   | (0.5875, 0.7083) | 0.6542 | (0.5917, 0.7167) |       0.8667 |       1      |         0.8    |         1      |             0.2333 |             0.2833 |            0.25   |            0.3167 |       0.7197 |              0.55  |         0.5   |           0.6786 |
| lm_gen_phi3.5      |     240 |          0.4467  | 0.4708 | (0.4083, 0.5333) | 0.6083 | (0.5458, 0.6708) | 0.65   | (0.5875, 0.7083) |       0.7667 |       0.95   |         0.7667 |         0.9167 |             0.15   |             0.2667 |            0.2    |            0.3    |       0.6894 |              0.525 |         0.55  |           0.4286 |
| template           |     240 |          0       | 0.45   | (0.3875, 0.5125) | 0.6    | (0.5375, 0.6625) | 0.65   | (0.5917, 0.7083) |       0.7333 |       0.9333 |         0.75   |         0.9167 |             0.15   |             0.25   |            0.1667 |            0.3    |       0.697  |              0.5   |         0.5   |           0.4286 |
| lm_gen_qwen3b      |     240 |          0.5741  | 0.4625 | (0.4, 0.525)     | 0.5792 | (0.5167, 0.6417) | 0.625  | (0.5625, 0.6875) |       0.7833 |       0.9167 |         0.7667 |         0.8833 |             0.15   |             0.2667 |            0.15   |            0.25   |       0.6742 |              0.475 |         0.525 |           0.3571 |
| lm_gen_qwen1.5b    |     240 |          0.4516  | 0.4208 | (0.3583, 0.4833) | 0.5792 | (0.5167, 0.6375) | 0.625  | (0.5625, 0.6833) |       0.6667 |       0.9    |         0.6667 |         0.8833 |             0.1667 |             0.2333 |            0.1833 |            0.3    |       0.6818 |              0.4   |         0.525 |           0.4286 |
| lm_gen_smol1.7b    |     240 |          0.27605 | 0.4167 | (0.3542, 0.4792) | 0.5708 | (0.5083, 0.6333) | 0.625  | (0.5625, 0.6875) |       0.6833 |       0.8667 |         0.7167 |         0.8667 |             0.15   |             0.2833 |            0.1167 |            0.2667 |       0.6515 |              0.45  |         0.525 |           0.4286 |
| embed              |     240 |          0.0062  | 0.3542 | (0.2917, 0.4125) | 0.5167 | (0.4542, 0.5792) | 0.5958 | (0.5333, 0.6583) |       0.5833 |       0.8167 |         0.6    |         0.8    |             0.1167 |             0.2167 |            0.1167 |            0.2333 |       0.5985 |              0.325 |         0.4   |           0.5714 |
| lm_pmi_smol1.7b    |     240 |          0.42445 | 0.2    | (0.15, 0.2542)   | 0.3667 | (0.3042, 0.425)  | 0.4083 | (0.3458, 0.4708) |       0.3333 |       0.5833 |         0.3167 |         0.5333 |             0.0667 |             0.1667 |            0.0833 |            0.1833 |       0.447  |              0.35  |         0.325 |           0.0714 |
| lm_pmi_qwen1.5b    |     240 |          0.4234  | 0.1292 | (0.0875, 0.1708) | 0.3417 | (0.2833, 0.4)    | 0.4542 | (0.3917, 0.5167) |       0.2    |       0.5167 |         0.1833 |         0.4833 |             0.0667 |             0.2167 |            0.0667 |            0.15   |       0.5076 |              0.225 |         0.15  |           0      |
| lm_pmi_qwen3b      |     240 |          0.80955 | 0.2    | (0.15, 0.25)     | 0.3375 | (0.2792, 0.3958) | 0.4333 | (0.3708, 0.4958) |       0.35   |       0.5    |         0.2833 |         0.4833 |             0.0833 |             0.1667 |            0.0833 |            0.2    |       0.4773 |              0.3   |         0.05  |           0.1429 |
| lm_pmi_phi3.5      |     240 |          1.10605 | 0.175  | (0.1292, 0.2208) | 0.3    | (0.2417, 0.3583) | 0.3708 | (0.3083, 0.4292) |       0.2667 |       0.4833 |         0.2667 |         0.45   |             0.0833 |             0.1333 |            0.0833 |            0.1333 |       0.3712 |              0.375 |         0.15  |           0.0714 |
| lm_choice_phi3.5   |     240 |          0.9306  | 0.2292 | (0.1792, 0.2833) | 0.2958 | (0.2416, 0.3501) | 0.2958 | (0.2417, 0.3542) |       0.3333 |       0.4167 |         0.3333 |         0.4333 |             0.1167 |             0.1667 |            0.1333 |            0.1667 |       0.5076 |              0.05  |         0     |           0.0714 |
| lm_rank_qwen1.5b   |     240 |          0.4214  | 0.0583 | (0.0292, 0.0875) | 0.2667 | (0.2125, 0.325)  | 0.3    | (0.2417, 0.3583) |       0.1167 |       0.3667 |         0.0667 |         0.3333 |             0.0167 |             0.1833 |            0.0333 |            0.1833 |       0.3106 |              0.15  |         0.175 |           0.3571 |
| lm_rank_qwen3b     |     240 |          0.84115 | 0.125  | (0.0875, 0.1667) | 0.2625 | (0.2083, 0.3208) | 0.3208 | (0.2625, 0.3792) |       0.1833 |       0.3833 |         0.1667 |         0.3667 |             0.0833 |             0.15   |            0.0667 |            0.15   |       0.3333 |              0.1   |         0.05  |           0.4643 |
| lm_rank_smol1.7b   |     240 |          0.4447  | 0.1083 | (0.0708, 0.15)   | 0.2333 | (0.1792, 0.2875) | 0.3083 | (0.25, 0.3626)   |       0.1833 |       0.3667 |         0.15   |         0.3    |             0.0333 |             0.1333 |            0.0667 |            0.1333 |       0.3182 |              0.075 |         0.05  |           0.3214 |
| lm_choice_qwen3b   |     240 |          0.89075 | 0.1458 | (0.1, 0.1917)    | 0.225  | (0.1749, 0.2792) | 0.225  | (0.175, 0.2792)  |       0.2    |       0.3333 |         0.2167 |         0.3167 |             0.0667 |             0.1333 |            0.1    |            0.1167 |       0.3333 |              0.125 |         0.05  |           0.1071 |
| lm_choice_qwen1.5b |     240 |          0.6258  | 0.1583 | (0.1125, 0.2083) | 0.2    | (0.15, 0.25)     | 0.2    | (0.15, 0.25)     |       0.2333 |       0.2833 |         0.2667 |         0.3167 |             0.0667 |             0.1167 |            0.0667 |            0.0833 |       0.3636 |              0     |         0     |           0      |
| lm_rank_phi3.5     |     240 |          0.996   | 0.1    | (0.0625, 0.1375) | 0.1958 | (0.1458, 0.2458) | 0.275  | (0.2208, 0.3333) |       0.1333 |       0.2667 |         0.1333 |         0.25   |             0.0667 |             0.1333 |            0.0667 |            0.1333 |       0.3333 |              0     |         0     |           0.1071 |
| lm_choice_smol1.7b |     240 |          0.3931  | 0.0333 | (0.0125, 0.0583) | 0.0583 | (0.0292, 0.0875) | 0.0583 | (0.0333, 0.0875) |       0.05   |       0.0667 |         0.05   |         0.0667 |             0.0167 |             0.05   |            0.0167 |            0.05   |       0.1061 |              0     |         0     |           0      |

## By condition

| method             | condition   |   n |      top1 |      top3 |
|:-------------------|:------------|----:|----------:|----------:|
| embed              | clean       |  60 | 0.583333  | 0.816667  |
| embed              | partial     |  60 | 0.6       | 0.8       |
| embed              | wrong_label |  60 | 0.116667  | 0.216667  |
| embed              | wrong_pick  |  60 | 0.116667  | 0.233333  |
| lm_choice_phi3.5   | clean       |  60 | 0.333333  | 0.416667  |
| lm_choice_phi3.5   | partial     |  60 | 0.333333  | 0.433333  |
| lm_choice_phi3.5   | wrong_label |  60 | 0.116667  | 0.166667  |
| lm_choice_phi3.5   | wrong_pick  |  60 | 0.133333  | 0.166667  |
| lm_choice_qwen1.5b | clean       |  60 | 0.233333  | 0.283333  |
| lm_choice_qwen1.5b | partial     |  60 | 0.266667  | 0.316667  |
| lm_choice_qwen1.5b | wrong_label |  60 | 0.0666667 | 0.116667  |
| lm_choice_qwen1.5b | wrong_pick  |  60 | 0.0666667 | 0.0833333 |
| lm_choice_qwen3b   | clean       |  60 | 0.2       | 0.333333  |
| lm_choice_qwen3b   | partial     |  60 | 0.216667  | 0.316667  |
| lm_choice_qwen3b   | wrong_label |  60 | 0.0666667 | 0.133333  |
| lm_choice_qwen3b   | wrong_pick  |  60 | 0.1       | 0.116667  |
| lm_choice_smol1.7b | clean       |  60 | 0.05      | 0.0666667 |
| lm_choice_smol1.7b | partial     |  60 | 0.05      | 0.0666667 |
| lm_choice_smol1.7b | wrong_label |  60 | 0.0166667 | 0.05      |
| lm_choice_smol1.7b | wrong_pick  |  60 | 0.0166667 | 0.05      |
| lm_gen_phi3.5      | clean       |  60 | 0.766667  | 0.95      |
| lm_gen_phi3.5      | partial     |  60 | 0.766667  | 0.916667  |
| lm_gen_phi3.5      | wrong_label |  60 | 0.15      | 0.266667  |
| lm_gen_phi3.5      | wrong_pick  |  60 | 0.2       | 0.3       |
| lm_gen_qwen1.5b    | clean       |  60 | 0.666667  | 0.9       |
| lm_gen_qwen1.5b    | partial     |  60 | 0.666667  | 0.883333  |
| lm_gen_qwen1.5b    | wrong_label |  60 | 0.166667  | 0.233333  |
| lm_gen_qwen1.5b    | wrong_pick  |  60 | 0.183333  | 0.3       |
| lm_gen_qwen3b      | clean       |  60 | 0.783333  | 0.916667  |
| lm_gen_qwen3b      | partial     |  60 | 0.766667  | 0.883333  |
| lm_gen_qwen3b      | wrong_label |  60 | 0.15      | 0.266667  |
| lm_gen_qwen3b      | wrong_pick  |  60 | 0.15      | 0.25      |
| lm_gen_smol1.7b    | clean       |  60 | 0.683333  | 0.866667  |
| lm_gen_smol1.7b    | partial     |  60 | 0.716667  | 0.866667  |
| lm_gen_smol1.7b    | wrong_label |  60 | 0.15      | 0.283333  |
| lm_gen_smol1.7b    | wrong_pick  |  60 | 0.116667  | 0.266667  |
| lm_pmi_phi3.5      | clean       |  60 | 0.266667  | 0.483333  |
| lm_pmi_phi3.5      | partial     |  60 | 0.266667  | 0.45      |
| lm_pmi_phi3.5      | wrong_label |  60 | 0.0833333 | 0.133333  |
| lm_pmi_phi3.5      | wrong_pick  |  60 | 0.0833333 | 0.133333  |
| lm_pmi_qwen1.5b    | clean       |  60 | 0.2       | 0.516667  |
| lm_pmi_qwen1.5b    | partial     |  60 | 0.183333  | 0.483333  |
| lm_pmi_qwen1.5b    | wrong_label |  60 | 0.0666667 | 0.216667  |
| lm_pmi_qwen1.5b    | wrong_pick  |  60 | 0.0666667 | 0.15      |
| lm_pmi_qwen3b      | clean       |  60 | 0.35      | 0.5       |
| lm_pmi_qwen3b      | partial     |  60 | 0.283333  | 0.483333  |
| lm_pmi_qwen3b      | wrong_label |  60 | 0.0833333 | 0.166667  |
| lm_pmi_qwen3b      | wrong_pick  |  60 | 0.0833333 | 0.2       |
| lm_pmi_smol1.7b    | clean       |  60 | 0.333333  | 0.583333  |
| lm_pmi_smol1.7b    | partial     |  60 | 0.316667  | 0.533333  |
| lm_pmi_smol1.7b    | wrong_label |  60 | 0.0666667 | 0.166667  |
| lm_pmi_smol1.7b    | wrong_pick  |  60 | 0.0833333 | 0.183333  |
| lm_rank_phi3.5     | clean       |  60 | 0.133333  | 0.266667  |
| lm_rank_phi3.5     | partial     |  60 | 0.133333  | 0.25      |
| lm_rank_phi3.5     | wrong_label |  60 | 0.0666667 | 0.133333  |
| lm_rank_phi3.5     | wrong_pick  |  60 | 0.0666667 | 0.133333  |
| lm_rank_qwen1.5b   | clean       |  60 | 0.116667  | 0.366667  |
| lm_rank_qwen1.5b   | partial     |  60 | 0.0666667 | 0.333333  |
| lm_rank_qwen1.5b   | wrong_label |  60 | 0.0166667 | 0.183333  |
| lm_rank_qwen1.5b   | wrong_pick  |  60 | 0.0333333 | 0.183333  |
| lm_rank_qwen3b     | clean       |  60 | 0.183333  | 0.383333  |
| lm_rank_qwen3b     | partial     |  60 | 0.166667  | 0.366667  |
| lm_rank_qwen3b     | wrong_label |  60 | 0.0833333 | 0.15      |
| lm_rank_qwen3b     | wrong_pick  |  60 | 0.0666667 | 0.15      |
| lm_rank_smol1.7b   | clean       |  60 | 0.183333  | 0.366667  |
| lm_rank_smol1.7b   | partial     |  60 | 0.15      | 0.3       |
| lm_rank_smol1.7b   | wrong_label |  60 | 0.0333333 | 0.133333  |
| lm_rank_smol1.7b   | wrong_pick  |  60 | 0.0666667 | 0.133333  |
| prior              | clean       |  60 | 0.866667  | 1         |
| prior              | partial     |  60 | 0.8       | 1         |
| prior              | wrong_label |  60 | 0.233333  | 0.283333  |
| prior              | wrong_pick  |  60 | 0.25      | 0.316667  |
| template           | clean       |  60 | 0.733333  | 0.933333  |
| template           | partial     |  60 | 0.75      | 0.916667  |
| template           | wrong_label |  60 | 0.15      | 0.25      |
| template           | wrong_pick  |  60 | 0.166667  | 0.3       |

## Paired differences vs the baselines

| a                  | b        | metric   |   a_minus_b |   ci_lo |   ci_hi |   n |
|:-------------------|:---------|:---------|------------:|--------:|--------:|----:|
| embed              | template | top1     |     -0.0958 | -0.1458 | -0.05   | 240 |
| embed              | template | top3     |     -0.0833 | -0.1375 | -0.0332 | 240 |
| embed              | prior    | top1     |     -0.1833 | -0.2458 | -0.1208 | 240 |
| embed              | prior    | top3     |     -0.1333 | -0.1875 | -0.0833 | 240 |
| lm_choice_phi3.5   | embed    | top1     |     -0.125  | -0.1833 | -0.0667 | 240 |
| lm_choice_phi3.5   | embed    | top3     |     -0.2208 | -0.2833 | -0.1583 | 240 |
| lm_choice_phi3.5   | template | top1     |     -0.2208 | -0.2833 | -0.1625 | 240 |
| lm_choice_phi3.5   | template | top3     |     -0.3042 | -0.3667 | -0.2417 | 240 |
| lm_choice_phi3.5   | prior    | top1     |     -0.3083 | -0.3792 | -0.2416 | 240 |
| lm_choice_phi3.5   | prior    | top3     |     -0.3542 | -0.4167 | -0.2917 | 240 |
| lm_choice_qwen1.5b | embed    | top1     |     -0.1958 | -0.2542 | -0.1375 | 240 |
| lm_choice_qwen1.5b | embed    | top3     |     -0.3167 | -0.3833 | -0.25   | 240 |
| lm_choice_qwen1.5b | template | top1     |     -0.2917 | -0.3542 | -0.2292 | 240 |
| lm_choice_qwen1.5b | template | top3     |     -0.4    | -0.4667 | -0.3333 | 240 |
| lm_choice_qwen1.5b | prior    | top1     |     -0.3792 | -0.45   | -0.3125 | 240 |
| lm_choice_qwen1.5b | prior    | top3     |     -0.45   | -0.5125 | -0.3833 | 240 |
| lm_choice_qwen3b   | embed    | top1     |     -0.2083 | -0.2708 | -0.1458 | 240 |
| lm_choice_qwen3b   | embed    | top3     |     -0.2917 | -0.3625 | -0.2208 | 240 |
| lm_choice_qwen3b   | template | top1     |     -0.3042 | -0.3708 | -0.2417 | 240 |
| lm_choice_qwen3b   | template | top3     |     -0.375  | -0.4417 | -0.3083 | 240 |
| lm_choice_qwen3b   | prior    | top1     |     -0.3917 | -0.4625 | -0.3208 | 240 |
| lm_choice_qwen3b   | prior    | top3     |     -0.425  | -0.4917 | -0.3583 | 240 |
| lm_choice_smol1.7b | embed    | top1     |     -0.3208 | -0.3875 | -0.2583 | 240 |
| lm_choice_smol1.7b | embed    | top3     |     -0.4583 | -0.5251 | -0.3875 | 240 |
| lm_choice_smol1.7b | template | top1     |     -0.4167 | -0.4792 | -0.3542 | 240 |
| lm_choice_smol1.7b | template | top3     |     -0.5417 | -0.6083 | -0.475  | 240 |
| lm_choice_smol1.7b | prior    | top1     |     -0.5042 | -0.5667 | -0.4417 | 240 |
| lm_choice_smol1.7b | prior    | top3     |     -0.5917 | -0.6583 | -0.525  | 240 |
| lm_gen_phi3.5      | embed    | top1     |      0.1167 |  0.0708 |  0.1667 | 240 |
| lm_gen_phi3.5      | embed    | top3     |      0.0917 |  0.0375 |  0.1458 | 240 |
| lm_gen_phi3.5      | template | top1     |      0.0208 | -0.0167 |  0.0583 | 240 |
| lm_gen_phi3.5      | template | top3     |      0.0083 | -0.025  |  0.0417 | 240 |
| lm_gen_phi3.5      | prior    | top1     |     -0.0667 | -0.1208 | -0.0125 | 240 |
| lm_gen_phi3.5      | prior    | top3     |     -0.0417 | -0.0792 | -0.0083 | 240 |
| lm_gen_qwen1.5b    | embed    | top1     |      0.0667 |  0.0083 |  0.125  | 240 |
| lm_gen_qwen1.5b    | embed    | top3     |      0.0625 |  0.0083 |  0.1167 | 240 |
| lm_gen_qwen1.5b    | template | top1     |     -0.0292 | -0.075  |  0.0167 | 240 |
| lm_gen_qwen1.5b    | template | top3     |     -0.0208 | -0.0542 |  0.0125 | 240 |
| lm_gen_qwen1.5b    | prior    | top1     |     -0.1167 | -0.175  | -0.0583 | 240 |
| lm_gen_qwen1.5b    | prior    | top3     |     -0.0708 | -0.1125 | -0.0333 | 240 |
| lm_gen_qwen3b      | embed    | top1     |      0.1083 |  0.0667 |  0.1542 | 240 |
| lm_gen_qwen3b      | embed    | top3     |      0.0625 |  0.0125 |  0.1125 | 240 |
| lm_gen_qwen3b      | template | top1     |      0.0125 | -0.025  |  0.05   | 240 |
| lm_gen_qwen3b      | template | top3     |     -0.0208 | -0.0583 |  0.0125 | 240 |
| lm_gen_qwen3b      | prior    | top1     |     -0.075  | -0.1333 | -0.0208 | 240 |
| lm_gen_qwen3b      | prior    | top3     |     -0.0708 | -0.1125 | -0.0332 | 240 |
| lm_gen_smol1.7b    | embed    | top1     |      0.0625 |  0.0083 |  0.1167 | 240 |
| lm_gen_smol1.7b    | embed    | top3     |      0.0542 |  0      |  0.1083 | 240 |
| lm_gen_smol1.7b    | template | top1     |     -0.0333 | -0.075  |  0.0083 | 240 |
| lm_gen_smol1.7b    | template | top3     |     -0.0292 | -0.0667 |  0.0083 | 240 |
| lm_gen_smol1.7b    | prior    | top1     |     -0.1208 | -0.1833 | -0.0624 | 240 |
| lm_gen_smol1.7b    | prior    | top3     |     -0.0792 | -0.125  | -0.0333 | 240 |
| lm_pmi_phi3.5      | embed    | top1     |     -0.1792 | -0.2458 | -0.1125 | 240 |
| lm_pmi_phi3.5      | embed    | top3     |     -0.2167 | -0.2875 | -0.1458 | 240 |
| lm_pmi_phi3.5      | template | top1     |     -0.275  | -0.3417 | -0.2125 | 240 |
| lm_pmi_phi3.5      | template | top3     |     -0.3    | -0.3625 | -0.2375 | 240 |
| lm_pmi_phi3.5      | prior    | top1     |     -0.3625 | -0.4333 | -0.2958 | 240 |
| lm_pmi_phi3.5      | prior    | top3     |     -0.35   | -0.4125 | -0.2875 | 240 |
| lm_pmi_qwen1.5b    | embed    | top1     |     -0.225  | -0.2833 | -0.1667 | 240 |
| lm_pmi_qwen1.5b    | embed    | top3     |     -0.175  | -0.2375 | -0.1083 | 240 |
| lm_pmi_qwen1.5b    | template | top1     |     -0.3208 | -0.3833 | -0.2583 | 240 |
| lm_pmi_qwen1.5b    | template | top3     |     -0.2583 | -0.3208 | -0.1958 | 240 |
| lm_pmi_qwen1.5b    | prior    | top1     |     -0.4083 | -0.4792 | -0.3375 | 240 |
| lm_pmi_qwen1.5b    | prior    | top3     |     -0.3083 | -0.375  | -0.2417 | 240 |
| lm_pmi_qwen3b      | embed    | top1     |     -0.1542 | -0.2125 | -0.0958 | 240 |
| lm_pmi_qwen3b      | embed    | top3     |     -0.1792 | -0.2417 | -0.1167 | 240 |
| lm_pmi_qwen3b      | template | top1     |     -0.25   | -0.3125 | -0.1917 | 240 |
| lm_pmi_qwen3b      | template | top3     |     -0.2625 | -0.325  | -0.2    | 240 |
| lm_pmi_qwen3b      | prior    | top1     |     -0.3375 | -0.4083 | -0.2708 | 240 |
| lm_pmi_qwen3b      | prior    | top3     |     -0.3125 | -0.375  | -0.2458 | 240 |
| lm_pmi_smol1.7b    | embed    | top1     |     -0.1542 | -0.2125 | -0.0958 | 240 |
| lm_pmi_smol1.7b    | embed    | top3     |     -0.15   | -0.2167 | -0.0833 | 240 |
| lm_pmi_smol1.7b    | template | top1     |     -0.25   | -0.3083 | -0.1917 | 240 |
| lm_pmi_smol1.7b    | template | top3     |     -0.2333 | -0.3    | -0.1667 | 240 |
| lm_pmi_smol1.7b    | prior    | top1     |     -0.3375 | -0.4042 | -0.2708 | 240 |
| lm_pmi_smol1.7b    | prior    | top3     |     -0.2833 | -0.35   | -0.2167 | 240 |
| lm_rank_phi3.5     | embed    | top1     |     -0.2542 | -0.3208 | -0.1917 | 240 |
| lm_rank_phi3.5     | embed    | top3     |     -0.3208 | -0.3917 | -0.2458 | 240 |
| lm_rank_phi3.5     | template | top1     |     -0.35   | -0.4125 | -0.2875 | 240 |
| lm_rank_phi3.5     | template | top3     |     -0.4042 | -0.4708 | -0.3333 | 240 |
| lm_rank_phi3.5     | prior    | top1     |     -0.4375 | -0.5083 | -0.3708 | 240 |
| lm_rank_phi3.5     | prior    | top3     |     -0.4542 | -0.5208 | -0.3875 | 240 |
| lm_rank_qwen1.5b   | embed    | top1     |     -0.2958 | -0.3625 | -0.2292 | 240 |
| lm_rank_qwen1.5b   | embed    | top3     |     -0.25   | -0.3208 | -0.1792 | 240 |
| lm_rank_qwen1.5b   | template | top1     |     -0.3917 | -0.4583 | -0.3208 | 240 |
| lm_rank_qwen1.5b   | template | top3     |     -0.3333 | -0.4043 | -0.2625 | 240 |
| lm_rank_qwen1.5b   | prior    | top1     |     -0.4792 | -0.5458 | -0.4167 | 240 |
| lm_rank_qwen1.5b   | prior    | top3     |     -0.3833 | -0.4542 | -0.3125 | 240 |
| lm_rank_qwen3b     | embed    | top1     |     -0.2292 | -0.3    | -0.1583 | 240 |
| lm_rank_qwen3b     | embed    | top3     |     -0.2542 | -0.3167 | -0.1917 | 240 |
| lm_rank_qwen3b     | template | top1     |     -0.325  | -0.3958 | -0.2583 | 240 |
| lm_rank_qwen3b     | template | top3     |     -0.3375 | -0.4042 | -0.2708 | 240 |
| lm_rank_qwen3b     | prior    | top1     |     -0.4125 | -0.4833 | -0.3458 | 240 |
| lm_rank_qwen3b     | prior    | top3     |     -0.3875 | -0.4542 | -0.3208 | 240 |
| lm_rank_smol1.7b   | embed    | top1     |     -0.2458 | -0.3084 | -0.1833 | 240 |
| lm_rank_smol1.7b   | embed    | top3     |     -0.2833 | -0.35   | -0.2125 | 240 |
| lm_rank_smol1.7b   | template | top1     |     -0.3417 | -0.4083 | -0.2792 | 240 |
| lm_rank_smol1.7b   | template | top3     |     -0.3667 | -0.4333 | -0.3    | 240 |
| lm_rank_smol1.7b   | prior    | top1     |     -0.4292 | -0.5    | -0.3583 | 240 |
| lm_rank_smol1.7b   | prior    | top3     |     -0.4167 | -0.4833 | -0.35   | 240 |
| prior              | embed    | top1     |      0.1833 |  0.1208 |  0.2458 | 240 |
| prior              | embed    | top3     |      0.1333 |  0.0833 |  0.1875 | 240 |
| prior              | template | top1     |      0.0875 |  0.0292 |  0.1458 | 240 |
| prior              | template | top3     |      0.05   |  0.0167 |  0.0833 | 240 |
| template           | embed    | top1     |      0.0958 |  0.05   |  0.1458 | 240 |
| template           | embed    | top3     |      0.0833 |  0.0292 |  0.1333 | 240 |
| template           | prior    | top1     |     -0.0875 | -0.1458 | -0.0292 | 240 |
| template           | prior    | top3     |     -0.05   | -0.0833 | -0.0167 | 240 |

