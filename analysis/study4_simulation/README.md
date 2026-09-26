# Study 4 — end-to-end simulation (Sec. 4.4)

**Question.** Given the gaze accuracy measured in Study 1b and the vocabulary behaviour
measured in Study 2, how long does a message take and how often is it wrong?

**Answer, and the result that reframed the paper:** at calibration-free webcam accuracy the
binding constraint is **not speed but error**. Every unguarded layout speaks the wrong message
about half the time. Optimising seconds-per-message — which is what the literature mostly
does — optimises the wrong quantity at this accuracy.

**This study also produced a recommendation that Study 5 then contradicted.** The simulator
recommends a repeat guard. Live, the guard roughly doubled the wrong-item rate, because the
simulator assumed successive selection errors are independent and they are not: the gaze error
is systematic within a sitting, so a guard asks the same question twice and gets the same wrong
answer twice. `E4_DESIGN.md` states the independence assumption; Sec. 4.4.2 and Sec. 4.5 report
what it cost. The assumption, not the arithmetic, was the error.

## Order of operations

```
python e4_build_inputs.py --e1b ../study1b_dwell_and_ablation/results/setup \
       --e2 ../study2_scene_vocabulary/results --out inputs.json
python e4_sim.py --inputs inputs.json --out results          # 20,000 messages per interface, seed 0
python e4_figures.py --results results --out results
```

Deterministic and seeded: the same command gives the same numbers. `inputs.json` is checked
in, so the simulation can be reproduced without re-running Studies 1b and 2, and every
parameter in it is traceable to one of them rather than chosen.

To redraw the paper's copies of the figures, point the last step at the figures folder:

```
python e4_figures.py --results results --out ../../figures
```

## Check it

```
python smoke_test_e4.py       # 20 tests
```

Includes the sanity anchors that catch a broken information-rate calculation: a perfect binary
choice must be 1 bit, chance must be 0, and a perfect 8-way choice must be 3.

## Results in this folder

| File | What it is |
|---|---|
| `results/e4_interfaces.csv` | seconds per message and wrong-message rate for each interface |
| `results/e4_sensitivity.csv` | the same across the accuracy range, which is what the figures plot |
| `results/fig_e4_tradeoff.{pdf,png}` | published as `figures/fig_e4_tradeoff.pdf` |
| `results/fig_e4_accuracy.{pdf,png}` | published as `figures/fig_e4_accuracy.pdf` |
| `results/E4_REPORT.md` | the run's own report |

Study 5's analysis (`../study5_6_live_sessions/analyse_study.py`) reads `inputs.json` from
this folder to compare what the simulator predicted with what happened.
