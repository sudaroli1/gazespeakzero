# The figures

The figures as they appear in the paper. Nothing here is a source file: every value plotted is
in one of the result files listed below, so each figure can be checked against the data
whether or not you redraw it.

| File | Paper | Every plotted value is in |
|---|---|---|
| `fig_zone_accuracy.pdf` | Sec. 4.1, zone accuracy by layout, two datasets | `study1_zone_classification/results/e1_zone_accuracy.csv`, `study1b_dwell_and_ablation/results/setup/e1b_frame_accuracy.csv` |
| `fig_ablation.pdf` | Sec. 4.1.6, the eyes-only ablation | `study1b_dwell_and_ablation/E1c_FINDINGS.md` (from `E1c_ablation_colab.ipynb`) |
| `fig_vocabulary.pdf` | Sec. 4.2, what each method puts in front of the user | `study2_scene_vocabulary/results/e2_summary.csv` |
| `fig_message.pdf` | Sec. 4.3, message identification, 240 cases | `study3_message_identification/results/e3_summary.csv` |
| `fig_e4_tradeoff.pdf` | Sec. 4.4, seconds per message against wrong-message rate | `study4_simulation/results/e4_sensitivity.csv` |
| `fig_e4_accuracy.pdf` | Sec. 4.4, the design rule the simulation produces | `study4_simulation/results/e4_interfaces.csv` |
| `fig_resolution.pdf` | Sec. 4.5.2, the same session at two capture resolutions | the three measures in Sec. 4.5.2's table; `system/calib_analysis.py` computes them per session |
| `fig_eyecrop.pdf` | Sec. 4.5.2, the same eye at two capture resolutions | two photographs, not published — see below |
| `fig_benchmark_vs_live.pdf` | Sec. 4.5.3, **the paper's central result** | `study5_6_live_sessions/verify_study5_numbers.py`, which recomputes each of them from the session logs |
| `fig_deployment.pdf` | Sec. 4.6, the same software on two machines | `study5_6_live_sessions/verify_paper_numbers.py`, likewise |

## Redrawing them

Two of the drawing scripts are in the repository:

```
cd analysis/study4_simulation       && python e4_figures.py --results results --out ../../figures
cd analysis/study5_6_live_sessions  && python make_fig_deploy.py
```

The remaining composites were drawn by one-off plotting scripts that were not kept, and we would
rather say so than imply a `make_figures.py` that does not exist. It costs a reader nothing in
what matters: every number in every one of those figures is in the files named above, and the
two studies whose figures carry the paper's central claims have verifier scripts that recompute
each plotted value from the raw logs and fail if it has drifted.

`fig_eyecrop.pdf` is the one figure that cannot be regenerated from this repository, and
deliberately so. It is built from two photographs of a face, taken by an author, of that author,
outside any session, expressly for that figure, with written consent. **The photographs are not
published.** `system/capture_figure.py` is the tool that made them; it writes to a folder
outside the repository which `.gitignore` also covers. No participant is photographed at any
stage of this work.

All figures use one palette, chosen to stay legible in the three common forms of colour vision
deficiency and in greyscale, and every one prints its values rather than relying on bar height
alone.
