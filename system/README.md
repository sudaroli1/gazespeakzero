# The system

The communication aid itself: three words in a row, a 500 ms dwell to select, an optional
repeat guard, and either a paging key or automatic scanning. It runs on an ordinary laptop with
its built-in webcam, on the CPU, with no eye tracker and no calibration hardware.

**It never writes video, images or audio.** Frames are processed in memory; only decisions,
timings and landmark-derived numbers reach the disk. This is enforced in the code rather than
by policy — the session path has no image-writing call in it — and every ethical claim the
paper makes about the study data depends on that remaining true. Do not add frame saving "just
for debugging".

## Setup

1. **Python 3.11 or 3.12.** MediaPipe has no wheels for 3.13 or later, and `setup_check.py`
   will tell you so rather than failing halfway through a session.

   ```
   python -m venv .venv
   .venv\Scripts\activate            # Windows;  source .venv/bin/activate elsewhere
   pip install -r ../requirements.txt
   ```

2. **The face model** — Google's, downloaded rather than redistributed:

   ```
   curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
   ```

3. **The gaze model** — `gaze_model.joblib` is in this folder. To retrain it, run
   `Train_gaze_model_colab.ipynb` on Colab (about ten minutes, no GPU needed); it trains on the
   eye-only feature set for the reason in
   `../analysis/study1b_dwell_and_ablation/E1c_FINDINGS.md`.

4. **Check the machine before trusting it:**

   ```
   python setup_check.py
   ```

   Go / no-go in about thirty seconds. It writes nothing.

## Running it

```
python gaze_ui.py --mode check                       # live view, nothing recorded
python gaze_ui.py --mode demo                        # free use, items from items_demo.json
python gaze_ui.py --mode study --pid P01             # the cued study: 8 blocks
python gaze_ui.py --mode study --pid P01 --desktop   # a desktop webcam, not a laptop one
```

`q` quits, `n` skips a trial. Sessions are written to `sessions/` as CSV; `data/README.md`
documents every column.

Useful flags: `--zones 2`, `--dwell-ms 500`, `--scan-ms 3000`, `--smooth-ms 180`,
`--arm-ms 800`, `--trials 15`, `--width/--height`, `--items <json>`, `--calibrate`,
`--no-calib`, `--windowed`.

## The three faults this folder is shaped by

Each of these produced a plausible-looking session that measured nothing, and each is in the
paper because finding them was the useful part.

1. **The readiness check timed the wrong thing.** It measured how fast the *camera* delivered
   frames. What decides a selection is capture plus landmark detection plus prediction, in
   series — and a machine that delivers 30 camera fps can run that loop at 7. `camera.py` now
   measures the pipeline (`measure_pipeline_fps`), `setup_check.py` refuses a machine that
   cannot hold 15 fps **end to end**, and `gaze_ui.py` watches the rate during the session and
   puts a banner on screen if it degrades. Section 4.6 is what this cost.

2. **The smoothing window was counted in frames.** Five frames is 167 ms at 30 fps and 667 ms
   at 7.5 — longer than the 500 ms dwell it was supposed to smooth, so on a slow machine the
   interface decided on stale data. The window is now specified in milliseconds
   (`--smooth-ms 180`) and the code comment says why.

3. **The cue was chosen before the page was reset.** On any trial following one that ended on
   a later page, the cued word was drawn from the previous page and was never displayed: the
   trial could not be completed by any gaze behaviour. `begin_trial()` now owns the whole
   sequence — reset, pick, show — and raises if the cue is not on the visible screen.
   `test_engine.py` has the regression test, and it is the one to look at if you want to see
   what the bug did.

`cap.set()` returning `True` is the general lesson: OpenCV reports that a camera request was
*accepted*, not that the driver honoured it. `camera.py` therefore tries every backend, request
order and frame-rate hint, **measures** what each one actually delivers, keeps the winner and
caches the choice in `camera_choice.json`.

## The files

| File | What it is |
|---|---|
| `engine.py` | the selection logic: dwell, guard, paging, scanning. No camera, no drawing, no I/O |
| `test_engine.py` | 31 headless tests of that logic. Run it after any change |
| `gaze_ui.py` | camera, gaze stage, screen, logging — the session itself |
| `camera.py` | opening a camera and proving what it delivers, rather than believing it |
| `setup_check.py` | the go / no-go for a new machine |
| `diagnose.py`, `camera_probe.py`, `mediapipe_probe.py`, `memcheck.py`, `kernel_probe.py` | the diagnostics written to find the four faults that stopped Study 6's operators. Each refuses to run rather than guess when a file it needs is missing, and each reports what it could **not** determine |
| `calib_analysis.py` | per-session calibration comparison, including the iris signal-to-noise check |
| `capture_figure.py` | the separate, clearly marked tool that produced the paper's eye-crop photographs. Not part of a session, and it writes outside the repository |
| `Train_gaze_model_colab.ipynb`, `build_notebook_train.py` | trains and exports `gaze_model.joblib`; the second regenerates the first |
| `items_demo.json` | the words shown in demo mode |

`gaze_ui.py` imports its feature extraction from
`../analysis/study1_zone_classification/extract_features.py` rather than keeping a copy, so the
live features cannot drift from the ones the model was fitted on. That is why this folder is
not self-contained, and `setup_check.py` checks for that file by name.

## Before running anyone but yourself

Read `../analysis/study5_6_live_sessions/PROTOCOL.md`, and run a session on yourself first: it
shakes out camera, lighting and seating problems, and it gives you the pipeline rate for your
machine. Institutional ethics review was not sought for the sessions reported in this paper;
the operators gave written informed consent, and the paper's ethics statement says exactly
that. If you run this with anyone else, follow whatever your institution requires.
