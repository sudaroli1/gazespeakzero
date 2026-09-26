# The session logs

`sessions/study5_author/` holds every session behind Study 5. Nothing here is derived: these
are the files the interface wrote while it ran, unedited.

**No image or video of any person is in this repository, and none was ever recorded during a
session.** The session software has no image-writing path. Every row below is a decision, a
timing, or a number derived from facial landmarks.

## The sessions

One person — the first author — recorded all of them. `P00`…`P05`, `PILOT`, `PILOT2` and
`PILOT3` are **session tags, not different people**. An analysis that counts them as
participants will report nine; the paper reports one, and says so.

| Session | Trials | Zones | What it is |
|---|---|---|---|
| `P00_check_*` (4 files) | — | — | pre-session checks. Two are empty: the session was abandoned before anything was logged |
| `P00_study_20260924-130843` | 19 | 3 | before the capture fix: the camera was delivering 640x480 |
| `P00_study_20260924-150417` | 24 | 2 | the same fault. The centre zone was selected in 35 of 37 selections — Sec. 4.5.2 |
| `P00_study_20260924-151031` | 48 | 3 | after the capture fix |
| `P01_study_20260924-153534` | 48 | 3 | |
| `P02`…`P05_study_*` | 48 each | 3 | the first sessions that record `cue_zone` |
| `PILOT_study_20260924-165155` | 120 | 3 | the three-zone table in Sec. 4.5.3 |
| `PILOT2_study_20260925-091250` | 80 | 2 | two zones |
| `PILOT3_study_20260925-092109` | 96 | 2 | the two-zone results and the guard table in Sec. 4.5.4 |

`calib_*.json` is the calibration fitted at the start of a session, `calib_frames_*.csv` the
frames it was fitted from (landmark-derived features, not images), and `calib_analysis_*.csv`
the held-out comparison of calibration methods for that session — including, by name, the fit
that was done the wrong way round and the corrected one, which is the regression-dilution
finding in Sec. 4.1.5.

## What a row means

One row per interface event, in the order they happened.

| Column | Meaning |
|---|---|
| `site` | the site tag the operator entered (later logs only) |
| `t_ms` | milliseconds since the session started |
| `block`, `trial` | the block, and the trial within it. **Numbering restarts in each session**, so a trial is identified by session + block + trial, not by block + trial |
| `condition_pattern` | `direct` (the words plus a paging key) or `scan` (the highlight advances automatically) |
| `condition_guard` | `none`, or `double` — a selection must be repeated to count |
| `condition_calib` | `free` (the population model) or `calibrated` (30 s of calibration first) |
| `cue_item` | the word the operator was asked to select on this trial |
| `event` | `dwell`, `select`, `reject`, `page` or `trial_end` — see below |
| `zone` | the screen zone the gaze estimate fell in |
| `item` | the word in that zone at that moment |
| `page` | which page of the vocabulary was displayed |
| `detail` | qualifies the event: `first of two` on a guarded first selection, `none`/`double` on a select, `user`/`auto` on a page change |
| `frame_ms` | **two different quantities.** On `dwell`, `select`, `reject` and `page` rows: the time this frame took to capture, detect and predict — the number the paper's per-frame timings come from. On `trial_end` rows: the duration of the whole trial. Filter by event before averaging it |
| `px`, `py` | the predicted gaze position, normalised to the screen. `py` is fixed in a single-row layout |
| `eye_px` | the width of the eye in the camera image, in pixels — the quantity Sec. 4.5.2 is about |
| `cue_zone` | the zone the cued word was in at that moment, or empty if it was not on screen (later logs only) |

Events:

- **`dwell`** — the gaze estimate stayed in one zone long enough to arm a selection.
- **`select`** — a selection was made.
- **`reject`** — under the repeat guard, the first of a pair, which does not select.
- **`page`** — the displayed page changed, `user` by the paging key or `auto` by scanning.
- **`trial_end`** — closes the trial; `item` is what was finally selected and `frame_ms` how long the trial took.

Two columns appear only in logs recorded on or after 25 Sep 2026: `site`, and `cue_zone`.
**A missing `cue_zone` means the column did not exist, not that the cue was off screen** —
the analysis script makes that distinction explicitly, because conflating the two would
discard two whole sessions. `data/audit/` and `data/results/` from earlier drafts of this
repository are gone: each study's results now sit in its own folder under `analysis/`, next
to the code that produced them.
