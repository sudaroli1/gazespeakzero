# The studies

One folder per study, named as the paper names it. Each has its own `README.md` saying what
to run and in what order, a `*_FINDINGS.md` written when the study was run, a `results/`
folder holding exactly the outputs the paper draws on, and — for the two studies that
needed a GPU — the Colab notebook that produced them.

| Folder | Paper | What it answers |
|---|---|---|
| `study1_zone_classification` | Sec. 4.1 | How many screen zones can an ordinary webcam separate, without calibration? |
| `study1b_dwell_and_ablation` | Sec. 4.1.4-4.1.6 | Does holding the gaze longer help? Does the accuracy come from the eyes or the head? |
| `study2_scene_vocabulary` | Sec. 4.2 | Should the screen offer a fixed word list or words grounded in what the camera sees? |
| `study3_message_identification` | Sec. 4.3 | Does a language model earn its place between selected objects and the spoken message? |
| `study4_simulation` | Sec. 4.4 | How do the stages compose, and what is the binding constraint? |
| `study5_6_live_sessions` | Sec. 4.5-4.6 | What happens when a person uses the system, and when two other people install it? |

Two conventions hold throughout:

- **A design document exists for every study whose result could be talked away.**
  `E2_DESIGN.md`, `E3_DESIGN.md` and `E4_DESIGN.md` were written and fixed before any
  number was produced, and each names the outcome that would refute its hypothesis. For
  Study 3 that refutation happened, and the folder says so.
- **Superseded results are described, not deleted.** Where a later run replaced an earlier
  one, the findings file says what changed and why. The superseded output tables are not
  published; they are in the working tree and available on request.

The three folders whose results came from a hosted GPU (`study1b`, `study2`, `study3`) ship
`build_notebook*.py` scripts. Those regenerate the Colab notebooks from the same source
files that run locally, so the notebook and the local code cannot diverge — the notebook is
a build artefact, not a second copy of the analysis.
