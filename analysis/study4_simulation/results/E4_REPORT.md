# E4: how long is a message, and how often is it wrong?

20000 simulated messages per interface, seed 0; 0.8s per selection; scan advances every 3.0s; scene list = qwen_vl; accuracy per layout from E1b: {2: 0.7712158842044764, 3: 0.8384520149758369, 4: 0.5123152891106897, 9: 0.4808581241532665}.

| interface                |   coverage |   selections_mean |   seconds_mean |   wrong_message_rate |   seconds_per_correct_message |   correct_messages_per_minute |
|:-------------------------|-----------:|------------------:|---------------:|---------------------:|------------------------------:|------------------------------:|
| grid9_fixed              |     1      |              1.59 |           1.27 |               0.7725 |                          5.58 |                        10.746 |
| row3_scene               |     1      |              6.37 |           5.09 |               0.4692 |                          9.59 |                         6.253 |
| row3_fixed               |     1      |              4.47 |           3.57 |               0.668  |                         10.76 |                         5.574 |
| row3_fixed16_double      |     0.5277 |              7.34 |           5.87 |               0.0619 |                         11.85 |                         5.062 |
| row3_scene_confirm       |     1      |             12.41 |           9.93 |               0.238  |                         13.03 |                         4.605 |
| row3_scene_double        |     1      |             14.66 |          11.72 |               0.1111 |                         13.19 |                         4.549 |
| look_to_speak_16         |     0.5375 |              4.12 |           3.3  |               0.6422 |                         17.15 |                         3.5   |
| row3_fixed_double        |     1      |             17.93 |          14.34 |               0.1832 |                         17.56 |                         3.417 |
| scan3_scene_double       |     1      |              2.89 |          19.05 |               0.0188 |                         19.42 |                         3.09  |
| scan3_scene              |     1      |              1.03 |          17.66 |               0.1605 |                         21.03 |                         2.853 |
| scan3_fixed_double       |     1      |              2.87 |          20.84 |               0.0179 |                         21.21 |                         2.828 |
| look_to_speak_16_confirm |     0.5347 |             12.24 |           9.79 |               0.347  |                         28.04 |                         2.14  |
| scan2_scene_double       |     1      |              3.18 |          28.38 |               0.0794 |                         30.83 |                         1.946 |
| look_to_speak            |     1      |              7.23 |           5.78 |               0.8354 |                         35.13 |                         1.708 |
| look_to_speak_confirm    |     1      |             25.83 |          20.67 |               0.5885 |                         50.21 |                         1.195 |

## Sensitivity

| knob                  |   value | interface           |   coverage |   selections_mean |   seconds_mean |   wrong_message_rate |   seconds_per_correct_message |   correct_messages_per_minute |
|:----------------------|--------:|:--------------------|-----------:|------------------:|---------------:|---------------------:|------------------------------:|------------------------------:|
| accuracy_3zones       |    0.6  | row3_fixed16_double |     0.544  |             10.42 |           8.34 |               0.4858 |                         29.81 |                         2.013 |
| accuracy_3zones       |    0.6  | row3_fixed          |     1      |              2.32 |           1.86 |               0.8622 |                         13.47 |                         4.455 |
| accuracy_3zones       |    0.6  | row3_fixed_double   |     1      |             13.81 |          11.05 |               0.7215 |                         39.68 |                         1.512 |
| accuracy_3zones       |    0.6  | row3_scene          |     1      |              5.09 |           4.07 |               0.7358 |                         15.42 |                         3.892 |
| accuracy_3zones       |    0.6  | row3_scene_confirm  |     1      |             12.59 |          10.07 |               0.5175 |                         20.88 |                         2.874 |
| accuracy_3zones       |    0.6  | row3_scene_double   |     1      |             14.12 |          11.3  |               0.5205 |                         23.56 |                         2.547 |
| accuracy_3zones       |    0.6  | scan3_scene         |     1      |              1.02 |          17.64 |               0.389  |                         28.87 |                         2.078 |
| accuracy_3zones       |    0.6  | scan3_scene_double  |     1      |              4.7  |          20.89 |               0.182  |                         25.53 |                         2.35  |
| accuracy_3zones       |    0.6  | scan3_fixed_double  |     1      |              4.62 |          22.19 |               0.1755 |                         26.92 |                         2.229 |
| accuracy_3zones       |    0.65 | row3_fixed16_double |     0.5355 |             10.37 |           8.29 |               0.3903 |                         25.4  |                         2.362 |
| accuracy_3zones       |    0.65 | row3_fixed          |     1      |              2.58 |           2.07 |               0.8522 |                         13.99 |                         4.288 |
| accuracy_3zones       |    0.65 | row3_fixed_double   |     1      |             15.35 |          12.28 |               0.6255 |                         32.79 |                         1.83  |
| accuracy_3zones       |    0.65 | row3_scene          |     1      |              5.39 |           4.31 |               0.6897 |                         13.9  |                         4.316 |
| accuracy_3zones       |    0.65 | row3_scene_confirm  |     1      |             12.63 |          10.1  |               0.4642 |                         18.85 |                         3.182 |
| accuracy_3zones       |    0.65 | row3_scene_double   |     1      |             14.49 |          11.59 |               0.4435 |                         20.82 |                         2.881 |
| accuracy_3zones       |    0.65 | scan3_scene         |     1      |              1.04 |          17.01 |               0.3543 |                         26.34 |                         2.278 |
| accuracy_3zones       |    0.65 | scan3_scene_double  |     1      |              4.23 |          20.16 |               0.1158 |                         22.79 |                         2.632 |
| accuracy_3zones       |    0.65 | scan3_fixed_double  |     1      |              4.22 |          22.52 |               0.119  |                         25.56 |                         2.347 |
| accuracy_3zones       |    0.7  | row3_fixed16_double |     0.5405 |              9.65 |           7.72 |               0.2562 |                         19.21 |                         3.124 |
| accuracy_3zones       |    0.7  | row3_fixed          |     1      |              2.95 |           2.36 |               0.8087 |                         12.35 |                         4.86  |
| accuracy_3zones       |    0.7  | row3_fixed_double   |     1      |             16.08 |          12.87 |               0.5092 |                         26.22 |                         2.289 |
| accuracy_3zones       |    0.7  | row3_scene          |     1      |              5.55 |           4.44 |               0.647  |                         12.59 |                         4.767 |
| accuracy_3zones       |    0.7  | row3_scene_confirm  |     1      |             12.51 |          10.01 |               0.416  |                         17.14 |                         3.501 |
| accuracy_3zones       |    0.7  | row3_scene_double   |     1      |             15.17 |          12.13 |               0.3493 |                         18.64 |                         3.218 |
| accuracy_3zones       |    0.7  | scan3_scene         |     1      |              1.03 |          17.81 |               0.3    |                         25.45 |                         2.358 |
| accuracy_3zones       |    0.7  | scan3_scene_double  |     1      |              3.82 |          20.15 |               0.0855 |                         22.03 |                         2.724 |
| accuracy_3zones       |    0.7  | scan3_fixed_double  |     1      |              3.9  |          22.04 |               0.0945 |                         24.34 |                         2.465 |
| accuracy_3zones       |    0.75 | row3_fixed16_double |     0.522  |              8.89 |           7.11 |               0.1719 |                         16.45 |                         3.648 |
| accuracy_3zones       |    0.75 | row3_fixed          |     1      |              3.45 |           2.76 |               0.7788 |                         12.47 |                         4.81  |
| accuracy_3zones       |    0.75 | row3_fixed_double   |     1      |             17.72 |          14.17 |               0.4032 |                         23.75 |                         2.526 |
| accuracy_3zones       |    0.75 | row3_scene          |     1      |              5.83 |           4.66 |               0.6068 |                         11.85 |                         5.062 |
| accuracy_3zones       |    0.75 | row3_scene_confirm  |     1      |             12.52 |          10.02 |               0.3675 |                         15.84 |                         3.788 |
| accuracy_3zones       |    0.75 | row3_scene_double   |     1      |             15.36 |          12.29 |               0.248  |                         16.34 |                         3.672 |
| accuracy_3zones       |    0.75 | scan3_scene         |     1      |              1.04 |          16.96 |               0.2497 |                         22.61 |                         2.654 |
| accuracy_3zones       |    0.75 | scan3_scene_double  |     1      |              3.43 |          19.14 |               0.0527 |                         20.21 |                         2.969 |
| accuracy_3zones       |    0.75 | scan3_fixed_double  |     1      |              3.47 |          21.11 |               0.0578 |                         22.41 |                         2.678 |
| accuracy_3zones       |    0.8  | row3_fixed16_double |     0.5292 |              8.09 |           6.47 |               0.094  |                         13.49 |                         4.448 |
| accuracy_3zones       |    0.8  | row3_fixed          |     1      |              3.92 |           3.14 |               0.7095 |                         10.8  |                         5.553 |
| accuracy_3zones       |    0.8  | row3_fixed_double   |     1      |             17.86 |          14.29 |               0.272  |                         19.62 |                         3.058 |
| accuracy_3zones       |    0.8  | row3_scene          |     1      |              6    |           4.8  |               0.5162 |                          9.93 |                         6.043 |
| accuracy_3zones       |    0.8  | row3_scene_confirm  |     1      |             12.64 |          10.11 |               0.3063 |                         14.57 |                         4.118 |
| accuracy_3zones       |    0.8  | row3_scene_double   |     1      |             14.93 |          11.95 |               0.1705 |                         14.4  |                         4.166 |
| accuracy_3zones       |    0.8  | scan3_scene         |     1      |              1.04 |          17.1  |               0.2052 |                         21.51 |                         2.789 |
| accuracy_3zones       |    0.8  | scan3_scene_double  |     1      |              3.12 |          19.23 |               0.0297 |                         19.82 |                         3.028 |
| accuracy_3zones       |    0.8  | scan3_fixed_double  |     1      |              3.1  |          21.81 |               0.0245 |                         22.35 |                         2.684 |
| accuracy_3zones       |    0.85 | row3_fixed16_double |     0.5262 |              7.11 |           5.69 |               0.0542 |                         11.42 |                         5.252 |
| accuracy_3zones       |    0.85 | row3_fixed          |     1      |              4.81 |           3.85 |               0.6558 |                         11.18 |                         5.365 |
| accuracy_3zones       |    0.85 | row3_fixed_double   |     1      |             17.87 |          14.29 |               0.1608 |                         17.03 |                         3.523 |
| accuracy_3zones       |    0.85 | row3_scene          |     1      |              6.48 |           5.19 |               0.445  |                          9.35 |                         6.42  |
| accuracy_3zones       |    0.85 | row3_scene_confirm  |     1      |             12.41 |           9.92 |               0.2338 |                         12.95 |                         4.633 |
| accuracy_3zones       |    0.85 | row3_scene_double   |     1      |             14.9  |          11.92 |               0.1005 |                         13.25 |                         4.529 |
| accuracy_3zones       |    0.85 | scan3_scene         |     1      |              1.03 |          17.72 |               0.1485 |                         20.81 |                         2.883 |
| accuracy_3zones       |    0.85 | scan3_scene_double  |     1      |              2.86 |          19.62 |               0.0177 |                         19.98 |                         3.003 |
| accuracy_3zones       |    0.85 | scan3_fixed_double  |     1      |              2.8  |          20.39 |               0.0152 |                         20.7  |                         2.898 |
| accuracy_3zones       |    0.9  | row3_fixed16_double |     0.5222 |              6.29 |           5.03 |               0.0201 |                          9.83 |                         6.106 |
| accuracy_3zones       |    0.9  | row3_fixed          |     1      |              5.97 |           4.78 |               0.5415 |                         10.42 |                         5.759 |
| accuracy_3zones       |    0.9  | row3_fixed_double   |     1      |             16.26 |          13.01 |               0.0658 |                         13.92 |                         4.31  |
| accuracy_3zones       |    0.9  | row3_scene          |     1      |              7.12 |           5.7  |               0.3643 |                          8.96 |                         6.697 |
| accuracy_3zones       |    0.9  | row3_scene_confirm  |     1      |             12.29 |           9.83 |               0.149  |                         11.56 |                         5.193 |
| accuracy_3zones       |    0.9  | row3_scene_double   |     1      |             13.98 |          11.18 |               0.0452 |                         11.71 |                         5.122 |
| accuracy_3zones       |    0.9  | scan3_scene         |     1      |              1.03 |          17.26 |               0.0973 |                         19.12 |                         3.138 |
| accuracy_3zones       |    0.9  | scan3_scene_double  |     1      |              2.52 |          18.36 |               0.0037 |                         18.43 |                         3.256 |
| accuracy_3zones       |    0.9  | scan3_fixed_double  |     1      |              2.54 |          20.76 |               0.0045 |                         20.86 |                         2.877 |
| accuracy_3zones       |    0.95 | row3_fixed16_double |     0.5323 |              5.71 |           4.57 |               0.0042 |                          8.61 |                         6.965 |
| accuracy_3zones       |    0.95 | row3_fixed          |     1      |              7.62 |           6.1  |               0.347  |                          9.34 |                         6.426 |
| accuracy_3zones       |    0.95 | row3_fixed_double   |     1      |             14.58 |          11.67 |               0.014  |                         11.83 |                         5.071 |
| accuracy_3zones       |    0.95 | row3_scene          |     1      |              8.25 |           6.6  |               0.2325 |                          8.6  |                         6.98  |
| accuracy_3zones       |    0.95 | row3_scene_confirm  |     1      |             12.19 |           9.75 |               0.0755 |                         10.55 |                         5.688 |
| accuracy_3zones       |    0.95 | row3_scene_double   |     1      |             12.16 |           9.72 |               0.0085 |                          9.81 |                         6.117 |
| accuracy_3zones       |    0.95 | scan3_scene         |     1      |              1.04 |          18.02 |               0.0535 |                         19.04 |                         3.151 |
| accuracy_3zones       |    0.95 | scan3_scene_double  |     1      |              2.29 |          19.39 |               0.0022 |                         19.43 |                         3.088 |
| accuracy_3zones       |    0.95 | scan3_fixed_double  |     1      |              2.28 |          20.41 |               0.0022 |                         20.46 |                         2.933 |
| zones_per_screen      |    2    | direct2_scene       |     1      |              9.73 |           7.79 |               0.6885 |                         25    |                         2.4   |
| zones_per_screen      |    2    | scan2_scene_double  |     1      |              3.21 |          29.29 |               0.079  |                         31.8  |                         1.887 |
| zones_per_screen      |    3    | direct3_scene       |     1      |              6.47 |           5.18 |               0.4665 |                          9.7  |                         6.185 |
| zones_per_screen      |    3    | scan3_scene_double  |     1      |              2.92 |          19.32 |               0.0185 |                         19.68 |                         3.049 |
| zones_per_screen      |    4    | direct4_scene       |     1      |              3.78 |           3.03 |               0.7268 |                         11.08 |                         5.416 |
| zones_per_screen      |    4    | scan4_scene_double  |     1      |              5.93 |          17.46 |               0.22   |                         22.39 |                         2.68  |
| zones_per_screen      |    9    | direct9_scene       |     1      |              2.44 |           1.95 |               0.6405 |                          5.43 |                        11.04  |
| zones_per_screen      |    9    | scan9_scene_double  |     1      |              7.58 |          12.11 |               0.1325 |                         13.96 |                         4.299 |
| share_in_first_screen |    0.1  | row3_scene_double   |     1      |             13.79 |          11.03 |               0.099  |                         12.24 |                         4.9   |
| share_in_first_screen |    0.1  | scan3_scene_double  |     1      |              2.88 |          17.16 |               0.0158 |                         17.43 |                         3.442 |
| share_in_first_screen |    0.2  | row3_scene_double   |     1      |             12.45 |           9.96 |               0.0905 |                         10.95 |                         5.478 |
| share_in_first_screen |    0.2  | scan3_scene_double  |     1      |              2.94 |          15.94 |               0.0187 |                         16.24 |                         3.694 |
| share_in_first_screen |    0.3  | row3_scene_double   |     1      |             11.03 |           8.82 |               0.0815 |                          9.6  |                         6.248 |
| share_in_first_screen |    0.3  | scan3_scene_double  |     1      |              2.9  |          14.05 |               0.0192 |                         14.33 |                         4.188 |
| share_in_first_screen |    0.4  | row3_scene_double   |     1      |             10.33 |           8.26 |               0.07   |                          8.88 |                         6.753 |
| share_in_first_screen |    0.4  | scan3_scene_double  |     1      |              2.89 |          12.33 |               0.0195 |                         12.58 |                         4.77  |
| share_in_first_screen |    0.5  | row3_scene_double   |     1      |              9.19 |           7.35 |               0.0633 |                          7.85 |                         7.642 |
| share_in_first_screen |    0.5  | scan3_scene_double  |     1      |              2.91 |          11.19 |               0.0168 |                         11.38 |                         5.271 |
| share_in_first_screen |    0.6  | row3_scene_double   |     1      |              8.03 |           6.42 |               0.0578 |                          6.82 |                         8.804 |
| share_in_first_screen |    0.6  | scan3_scene_double  |     1      |              2.92 |           9.17 |               0.0205 |                          9.36 |                         6.411 |
| share_in_first_screen |    0.7  | row3_scene_double   |     1      |              7.03 |           5.62 |               0.0512 |                          5.93 |                        10.124 |
| share_in_first_screen |    0.7  | scan3_scene_double  |     1      |              2.85 |           6.92 |               0.0145 |                          7.02 |                         8.545 |
| share_in_first_screen |    0.8  | row3_scene_double   |     1      |              6.12 |           4.9  |               0.042  |                          5.11 |                        11.737 |
| share_in_first_screen |    0.8  | scan3_scene_double  |     1      |              2.87 |           5.74 |               0.018  |                          5.84 |                        10.268 |
| share_in_first_screen |    0.9  | row3_scene_double   |     1      |              5.11 |           4.09 |               0.0285 |                          4.21 |                        14.25  |
| share_in_first_screen |    0.9  | scan3_scene_double  |     1      |              2.87 |           4.07 |               0.0182 |                          4.14 |                        14.482 |
| scan_seconds          |    2    | scan3_scene         |     1      |              1.03 |          11.69 |               0.1603 |                         13.92 |                         4.311 |
| scan_seconds          |    2    | scan3_scene_double  |     1      |              2.92 |          13.32 |               0.0155 |                         13.53 |                         4.435 |
| scan_seconds          |    3    | scan3_scene         |     1      |              1.03 |          17.26 |               0.1693 |                         20.78 |                         2.887 |
| scan_seconds          |    3    | scan3_scene_double  |     1      |              2.89 |          19.01 |               0.0173 |                         19.35 |                         3.101 |
| scan_seconds          |    4    | scan3_scene         |     1      |              1.03 |          23.19 |               0.1603 |                         27.62 |                         2.172 |
| scan_seconds          |    4    | scan3_scene_double  |     1      |              2.88 |          24.6  |               0.021  |                         25.13 |                         2.388 |
| scan_seconds          |    5    | scan3_scene         |     1      |              1.03 |          29.29 |               0.166  |                         35.12 |                         1.708 |
| scan_seconds          |    5    | scan3_scene_double  |     1      |              2.89 |          30.82 |               0.0175 |                         31.37 |                         1.913 |
| scan_seconds          |    7    | scan3_scene         |     1      |              1.03 |          40.63 |               0.1685 |                         48.87 |                         1.228 |
| scan_seconds          |    7    | scan3_scene_double  |     1      |              2.89 |          41.37 |               0.0195 |                         42.19 |                         1.422 |

