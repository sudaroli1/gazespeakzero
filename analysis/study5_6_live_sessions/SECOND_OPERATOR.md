# Second-operator pilot — instructions

**What this is.** A technical shake-down of the software on a second person, a second laptop
and a second room, before the real study is run. It checks that the system works outside its
author's setup and gives a second reading on calibration quality.

**What this is not.** It is **not** part of the research study. Ethics approval has not yet
been granted, so this session produces *engineering* evidence, not study data. Nothing from it
counts toward the twelve participants, and it will appear in the paper only as a pilot, if at
all. You may stop at any point and ask for your files to be deleted.

**What is recorded.** Which box you looked at, the timing, and numbers derived from the camera
image (where your eyes are pointing, how wide your eye is in pixels). **No video, photograph or
sound is recorded at any point** — the software has no code that can save an image.

---

## 1. Set up (about 10 minutes, once)

You need **Python 3.11 or 3.12**. Not 3.14 — the libraries have no version for it.

```
cd <the prototype folder>
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Check the machine before anything else

```
python setup_check.py
```

It prints OK or FAIL for each item. **If anything says FAIL, stop and send me those lines.**

Two checks matter more than the rest:

- `camera gives 1280x720 or better` — below that the system does not work at all, and we know
  why (it is a finding in the paper).
- `frame rate >= 15 fps` — the software decides where you looked by taking a short window of
  recent frames. Too few frames per second and that window stretches back past the moment you
  moved your eyes, so it answers with where you were looking *before*. It still looks normal
  on screen, which is exactly why this is a hard stop rather than a warning.

**If the frame rate fails**, run:

```
python camera_probe.py
```

and send me the whole output. It tests the camera several ways and usually names the cause
itself. The two common ones, both fixable in a minute:

- The camera is sending uncompressed video, which cannot fit through a USB 2 port fast enough.
  Plug it straight into the laptop rather than a hub, dock or monitor, and prefer a blue
  (USB 3) port. If it is a built-in webcam this is rarely the problem.
- The room is dim, so the camera holds the shutter open longer and drops to 15 or 7.5 fps.
  Put a lamp or window **in front of** your face and try again.

Also close anything else that might hold the camera: Teams, Zoom, Meet, the Camera app.

### If the run stops and just says `Killed`

That word, with no Python error underneath it, means the operating system stopped the
program — usually because it ran out of memory. The program never sees it coming, so
there is nothing useful in the output.

Run:

```
python memcheck.py
```

It loads the system one piece at a time and prints the memory used after each. If it is
killed again, **the last line it printed names the piece that would not fit** — send me
everything it printed, including any half-finished line. It also checks the system log
and will usually say outright whether memory was the cause.

For reference, the whole thing needs about **250 MB**, which is not much. So if memory is
really the problem, the machine had almost nothing free — closing the browser before
running usually settles it.

## 3. Sit properly — this matters more than it sounds

- **Light in front of you**, not behind. A window or lamp behind your head puts your eyes in
  shadow and the system cannot see where you are looking.
- 50–70 cm from the screen, roughly arm's length.
- Screen brightness up.
- Head still during the session. Move your **eyes**, not your head.

## 4. Run the session (about 12 minutes)

```
python gaze_ui.py --mode study --pid T01 --site PILOT --zones 2 --trials 10
```

What happens:

1. **Calibration.** A dot appears at five places across the screen, twice. Look at each dot and
   hold still. It then prints a held-out accuracy — **please note that number down**.
2. **Eight blocks of 10 trials.** Each trial shows one word alone in the middle of the screen.
   Read it, then the two boxes appear. Look at the box with that word and hold your gaze there
   for about half a second.
3. There is a short "read the words" pause at the start of every trial — selection is switched
   off during it, so take that moment to read.
4. `q` quits at any time. `n` skips a trial you are stuck on.

## 5. Send back

From the `prototype\sessions\` folder:

- `T01_study_<timestamp>.csv`
- `T01_study_<timestamp>_meta.json`
- `calib_T01.json`
- `calib_frames_T01.csv`

Please do **not** send anything from `paper\figs_raw\` — that folder holds photographs.

## 6. Tell me, in your own words

These are worth as much as the files:

1. Was anything confusing about what you were meant to do?
2. Did the pace feel right — too fast, too slow, tiring?
3. Did it ever select something you were not looking at? Roughly how often?
4. Did your eyes get tired, and at what point?
5. Anything that would have made it easier?

Honest answers are more useful than kind ones. If it was frustrating, say so — that is a result.
