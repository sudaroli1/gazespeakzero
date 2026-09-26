"""
GazeSpeakZero prototype: webcam -> zone -> item, with dwell, guard and scanning.

    python gaze_ui.py --check                 # camera, model and speed only
    python gaze_ui.py --mode demo             # free use, scene items on screen
    python gaze_ui.py --mode study --pid P01  # the cued-selection study

It runs on a laptop CPU. **No video and no images are ever written to disk**: each frame
produces landmark-derived numbers, and only decisions and timings are logged. That is a
requirement of the ethics application, not a preference.

Needs: opencv-python, mediapipe, numpy, joblib, scikit-learn, and two files beside it —
  face_landmarker.task   (MediaPipe FaceLandmarker, downloaded once)
  gaze_model.joblib      (trained in Train_gaze_model_colab.ipynb from the E1b features)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import random
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "analysis", "study1_zone_classification"))
from extract_features import features_from_result  # noqa: E402

from engine import Engine  # noqa: E402

FONT = cv2.FONT_HERSHEY_SIMPLEX
BG, INK, DIM = (26, 26, 25), (245, 245, 245), (120, 120, 118)
HILITE, GOOD, BAD = (214, 120, 42), (122, 175, 27), (72, 72, 227)     # BGR

# Below this the 500 ms dwell holds too few independent samples for the min_frac vote to
# mean anything (at 7.5 fps it is under 4 frames), so sessions are refused rather than
# collected and thrown away later. 15 fps gives ~7 samples per dwell.
MIN_FPS = 15.0


# ---------------------------------------------------------------- gaze
class Gaze:
    """MediaPipe landmarks -> the E1b features -> predicted screen point -> zone."""

    def __init__(self, model_path, landmarker_path, zones=3, is_laptop=1, calib=None,
                 smooth_ms=180):
        import joblib
        import mediapipe as mp
        b = joblib.load(model_path)
        self.mx, self.my, self.feats = b["model_x"], b["model_y"], b["features"]
        self.zones, self.is_laptop = zones, is_laptop
        base = mp.tasks.BaseOptions(model_asset_path=landmarker_path)
        opts = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=base, running_mode=mp.tasks.vision.RunningMode.VIDEO,
            output_face_blendshapes=True, output_facial_transformation_matrixes=True, num_faces=1)
        self.lm = mp.tasks.vision.FaceLandmarker.create_from_options(opts)
        self.mp = mp
        self.last_ms = -1.0
        self.last_features = None
        # A per-person correction stretches the model's output - x2.2 on this laptop - and
        # stretches its noise with it, which flips the zone from frame to frame. Take the median
        # of the recent frames before deciding the zone.
        #
        # The window is specified in TIME, not frames. Frame-based smoothing silently
        # changes length with the camera: 5 frames is 0.18 s at 28 fps but 0.67 s at
        # 7.5 fps - longer than the 0.5 s dwell, so the zone would be decided from gaze
        # collected before the person looked at the target, and the overlapping samples
        # would agree with each other well enough to pass the dwell vote. Confidently wrong
        # is worse than noisy. In time, the window is the same everywhere.
        self.smooth_ms = max(1, int(smooth_ms))
        self._px_hist = []          # (t_ms, px)
        # calib: {"ax":..,"bx":..,"ay":..,"by":..} maps the model's output onto this person's
        # screen. Without it the prediction is used raw (the calibration-free condition).
        self.calib = calib

    def zone_of(self, frame_bgr, t_ms):
        """Returns (zone or None, x, y, ms_spent). x is 0..1 across the screen."""
        t0 = time.perf_counter()
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        ts = int(max(t_ms, self.last_ms + 1))
        self.last_ms = ts
        res = self.lm.detect_for_video(img, ts)
        h, w = frame_bgr.shape[:2]
        f = features_from_result(res, w, h)
        if not f or not f.get("detected"):
            return None, np.nan, np.nan, (time.perf_counter() - t0) * 1000
        f["is_laptop"] = self.is_laptop
        self.last_features = f          # kept so the calibration can save what the model saw
        x = np.array([[f.get(k, np.nan) for k in self.feats]], dtype=float)
        px, py = float(self.mx.predict(x)[0]), float(self.my.predict(x)[0])
        if self.calib:
            k = self.calib.get("knots_x")
            if k:                       # monotone (isotonic) mapping: handles the compression
                px = float(np.clip(np.interp(px, k, self.calib["knots_y"]), 0.0, 1.0))
            else:                       # older calibrations kept only a straight line
                px = float(np.clip(self.calib["ax"] * px + self.calib["bx"], 0.0, 1.0))
            py = float(np.clip(self.calib["ay"] * py + self.calib["by"], 0.0, 1.0))
        self._px_hist.append((t_ms, px))
        cut = t_ms - self.smooth_ms
        self._px_hist = [(t, v) for t, v in self._px_hist if t >= cut]
        px = float(np.median([v for _, v in self._px_hist]))
        z = int(np.clip(px * self.zones, 0, self.zones - 1))
        return z, px, py, (time.perf_counter() - t0) * 1000


# ---------------------------------------------------------------- drawing
def draw(canvas, labels, zone, cue=None, banner="", sub="", pending=None):
    h, w = canvas.shape[:2]
    canvas[:] = BG
    k = len(labels)
    for i, text in enumerate(labels):
        x0, x1 = int(i * w / k), int((i + 1) * w / k)
        box = (x0 + 8, 90, x1 - 8, h - 90)
        colour = HILITE if i == zone else (60, 60, 58)
        cv2.rectangle(canvas, (box[0], box[1]), (box[2], box[3]), colour, -1 if i == zone else 2)
        if cue is not None and i == cue:
            cv2.rectangle(canvas, (box[0] - 4, box[1] - 4), (box[2] + 4, box[3] + 4), GOOD, 3)
        if pending is not None and i == pending:
            cv2.rectangle(canvas, (box[0] + 6, box[1] + 6), (box[2] - 6, box[3] - 6), INK, 1)
        size = cv2.getTextSize(text, FONT, 0.9, 2)[0]
        cv2.putText(canvas, text, (int((x0 + x1 - size[0]) / 2), int(h / 2)), FONT, 0.9,
                    INK if i != zone else (20, 20, 20), 2, cv2.LINE_AA)
    if banner:
        cv2.putText(canvas, banner, (20, 50), FONT, 0.8, INK, 2, cv2.LINE_AA)
    if sub:
        cv2.putText(canvas, sub, (20, h - 30), FONT, 0.6, DIM, 1, cv2.LINE_AA)


# ---------------------------------------------------------------- study conditions
CONDITIONS = [                      # (pattern, guard, calibrated) — the four E4 designs, each
    ("direct", None, False),        # run twice: once calibration-free, once after a 30-second
    ("direct", "double", False),    # per-person correction. Calibration is a factor, not a
    ("scan", None, False),          # footnote, because the population model turns out to use
    ("scan", "double", False),      # only part of the screen on an unseen camera.
    ("direct", None, True),
    ("direct", "double", True),
    ("scan", None, True),
    ("scan", "double", True),
]


def study_blocks(pid, trials_per_condition):
    """A fixed, per-participant order. The two calibration halves are counterbalanced against
    practice and fatigue: half the participants do the calibration-free blocks first."""
    rng = random.Random(hash(pid) % (2 ** 31))
    free = [c for c in CONDITIONS if not c[2]]
    cal = [c for c in CONDITIONS if c[2]]
    rng.shuffle(free)
    rng.shuffle(cal)
    halves = [free, cal] if rng.random() < 0.5 else [cal, free]
    return [(p, g, c, trials_per_condition) for half in halves for p, g, c in half]


CAL_POINTS = [0.08, 0.30, 0.50, 0.70, 0.92]      # where the dot appears, across the screen


def calibrate(gaze, cap, canvas, pid, out_dir, hold_ms=2200, settle_ms=700):
    """Two passes over five dots: the first fits the correction, the second checks it on frames
    the fit never saw. The held-out number is the one worth reporting."""
    xs, ys, tx, ty = [], [], [], []
    hx, ht = [], []                                   # the held-out pass
    frames = []                                       # every frame, with the features behind it
    nz = int(getattr(gaze, "zones", 3))               # score against the layout actually in use
    h, w = canvas.shape[:2]
    order = [(0, fx) for fx in CAL_POINTS] + [(1, fx) for fx in reversed(CAL_POINTS)]
    for i, (pass_no, fx) in enumerate(order):
        t_end = time.time() + hold_ms / 1000
        t_use = time.time() + settle_ms / 1000
        got = 0
        deadline = time.time() + 3 * hold_ms / 1000       # never wait forever on a lost face
        while time.time() < t_end or (got < 8 and time.time() < deadline):
            ok, frame = cap.read()
            if not ok:
                continue
            z, px, py, _ = gaze.zone_of(frame, time.time() * 1000)
            canvas[:] = BG
            cv2.circle(canvas, (int(fx * w), h // 2), 26, HILITE, -1)
            cv2.circle(canvas, (int(fx * w), h // 2), 8, (255, 255, 255), -1)
            cv2.putText(canvas, f"Look at the dot  ({i + 1} of {len(order)})", (30, 60),
                        FONT, 0.9, INK, 2, cv2.LINE_AA)
            if px != px:
                cv2.putText(canvas, "FACE LOST - sit back, uncover your face, more light",
                            (30, 110), FONT, 0.8, BAD, 2, cv2.LINE_AA)
            cv2.putText(canvas, "keep your head still - move only your eyes - do not touch your face",
                        (30, h - 40), FONT, 0.6, DIM, 1, cv2.LINE_AA)
            cv2.putText(canvas, f"frames: {got}", (w - 220, h - 40), FONT, 0.6,
                        DIM if got >= 8 else BAD, 1, cv2.LINE_AA)
            cv2.imshow("GazeSpeakZero", canvas)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                return None
            if time.time() >= t_use and px == px:
                got += 1
                fr = dict(gaze.last_features or {})
                fr.update({"target_x": fx, "pass": pass_no, "px_raw": px, "py_raw": py})
                frames.append(fr)
                if pass_no == 0:
                    xs.append(px)
                    tx.append(fx)
                    ys.append(py)
                    ty.append(0.5)
                else:
                    hx.append(px)
                    ht.append(fx)
    if len(xs) < 20:
        print(f"calibration failed: only {len(xs)} frames with a face out of the {len(order)} "
              f"dots (need 20+).")
        print("  the face must be fully visible: do not rest your chin on your hand, keep the "
              "light in front of you rather than behind, and sit 50-70 cm from the screen.")
        return None
    # Fit prediction-on-target, then invert. Regressing the target on the prediction (the
    # obvious way round) is attenuated by the noise in the prediction - regression dilution -
    # which returned a slope of 1.03 when the model's output actually needed stretching by 1.6,
    # so the correction did nothing and the outer zones stayed unreachable.
    a_fwd, b_fwd = np.polyfit(np.array(tx), np.array(xs), 1)    # pred = a * target + b
    if abs(a_fwd) < 1e-3:
        print("calibration failed: the prediction does not move with the dot at all")
        return None
    ax, bx = 1.0 / a_fwd, -b_fwd / a_fwd                        # target = (pred - b) / a
    ay, by = (1.0, 0.0) if np.std(ys) < 1e-6 else np.polyfit(np.array(ys), np.array(ty), 1)
    calib = {"ax": float(ax), "bx": float(bx), "ay": float(ay), "by": float(by),
             "n_frames": len(xs), "raw_range": [float(min(xs)), float(max(xs))]}
    pred = np.clip(ax * np.array(xs) + bx, 0, 1)
    zone_ok = float((np.clip(pred * nz, 0, nz - 1).astype(int)
                     == np.clip(np.array(tx) * nz, 0, nz - 1).astype(int)).mean())
    calib["zone_accuracy_in_sample"] = round(zone_ok, 3)

    # The model's output is compressed, and not symmetrically: on this laptop the right-hand
    # zone was recovered 0.72 of the time by a straight line and 1.00 by a monotone fit. Fit
    # both, score both on the held-out pass, and keep whichever actually does better.
    def _z3(v):
        return np.clip((np.clip(np.asarray(v), 0, 1) * nz).astype(int), 0, nz - 1)

    if len(hx) > 20:
        try:
            from sklearn.isotonic import IsotonicRegression
            iso = IsotonicRegression(out_of_bounds="clip").fit(np.array(xs), np.array(tx))
            grid = np.linspace(min(xs), max(xs), 24)
            calib["_iso_x"], calib["_iso_y"] = list(map(float, grid)), \
                list(map(float, iso.predict(grid)))
            lin_acc = float((_z3(ax * np.array(hx) + bx) == _z3(ht)).mean())
            iso_acc = float((_z3(np.interp(hx, calib["_iso_x"], calib["_iso_y"])) == _z3(ht)).mean())
            calib["zone_accuracy_linear"] = round(lin_acc, 3)
            calib["zone_accuracy_isotonic"] = round(iso_acc, 3)
            if iso_acc >= lin_acc:
                calib["knots_x"], calib["knots_y"] = calib["_iso_x"], calib["_iso_y"]
                calib["mapping"] = "isotonic"
            else:
                calib["mapping"] = "linear"
            calib.pop("_iso_x", None)
            calib.pop("_iso_y", None)
        except ImportError:
            calib["mapping"] = "linear"
    if len(hx) > 20:                                   # the honest number: frames the fit never saw
        ph = np.clip(ax * np.array(hx) + bx, 0, 1)
        held = float((np.clip(ph * nz, 0, nz - 1).astype(int)
                      == np.clip(np.array(ht) * nz, 0, nz - 1).astype(int)).mean())
        # the number reported is the mapping actually kept, not always the straight line
        if calib.get("mapping") == "isotonic":
            held = calib.get("zone_accuracy_isotonic", held)
        calib["zone_accuracy_held_out"] = round(held, 3)
        calib["held_out_frames"] = len(hx)
    path = os.path.join(out_dir, f"calib_{pid}.json")
    calib["zones"] = nz
    json.dump(calib, open(path, "w"), indent=1)
    if frames:
        import csv as _csv
        fpath = os.path.join(out_dir, f"calib_frames_{pid}.csv")
        keys = sorted({k for fr in frames for k in fr})
        with open(fpath, "w", newline="") as fh:
            w_ = _csv.DictWriter(fh, fieldnames=keys)
            w_.writeheader()
            w_.writerows(frames)
        print(f"  raw calibration frames: {fpath} ({len(frames)} rows)")
    print(f"\ncalibration saved: {path}")
    print(f"  the model used {calib['raw_range'][0]:.2f}-{calib['raw_range'][1]:.2f} of the screen; "
          f"correction x' = {ax:.2f}x + {bx:.2f}")
    print(f"  {nz}-zone accuracy, fitted frames: {zone_ok:.2f}")
    if calib.get("mapping"):
        print(f"  mapping chosen: {calib['mapping']}  "
              f"(straight line {calib.get('zone_accuracy_linear')}, "
              f"monotone {calib.get('zone_accuracy_isotonic')} on the held-out pass)")
    if "zone_accuracy_held_out" in calib:
        print(f"  {nz}-zone accuracy, HELD-OUT frames ({calib['held_out_frames']}): "
              f"{calib['zone_accuracy_held_out']:.2f}   <- the number that counts")
    return calib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["demo", "study", "check"], default="demo")
    ap.add_argument("--pid", default="P00", help="participant id (study mode)")
    ap.add_argument("--items", default=os.path.join(HERE, "items_demo.json"))
    ap.add_argument("--model", default=os.path.join(HERE, "gaze_model.joblib"))
    ap.add_argument("--landmarker", default=os.path.join(HERE, "face_landmarker.task"))
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--site", default="",
                    help="site code (S1..S4). Required in study mode: the multi-site protocol "
                         "records which institution each session was run at.")
    ap.add_argument("--laptop", default="",
                    help="short laptop/webcam description, e.g. 'DellVostro-integrated'. "
                         "Recorded once per session so capture hardware is reportable.")
    ap.add_argument("--lighting", default="", choices=["", "front", "behind", "neither", "artificial"],
                    help="where the main light is relative to the participant")
    ap.add_argument("--smooth-ms", type=int, default=180, dest="smooth_ms",
                    help="milliseconds of median smoothing on the predicted x before the zone "
                         "is decided. 180 ms is the 5 frames the pilot used at 28 fps, but "
                         "specified in time so a slower camera does not silently widen it into "
                         "the dwell window and decide on stale gaze.")
    ap.add_argument("--allow-slow-camera", action="store_true", dest="allow_slow",
                    help="permit a study session below the frame-rate floor. Practice only - "
                         "the data cannot be pooled across sites.")
    ap.add_argument("--arm-ms", type=int, default=800, dest="arm_ms",
                    help="reading time at the start of each trial, before dwell can select. "
                         "Without it the dwell detector fires while the eyes are still sweeping "
                         "across the three words, which lands in the middle zone.")
    ap.add_argument("--width", type=int, default=1280,
                    help="capture width. The gaze signal lives in the iris, which is a few "
                         "pixels wide: at 640x480 one screen-third moves the iris less than the "
                         "landmark noise, so this must be as high as the webcam supports.")
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--zones", type=int, default=3)
    ap.add_argument("--dwell-ms", type=int, default=500)
    ap.add_argument("--scan-ms", type=int, default=3000)
    ap.add_argument("--trials", type=int, default=15, help="trials per condition (study mode)")
    ap.add_argument("--desktop", action="store_true", help="a desktop webcam, not a laptop one")
    ap.add_argument("--out", default=os.path.join(HERE, "sessions"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--calibrate", action="store_true",
                    help="run the 10-second five-point calibration and save it for this --pid")
    ap.add_argument("--no-calib", action="store_true",
                    help="skip calibration entirely; in study mode the calibrated blocks are "
                         "then dropped and only the four calibration-free ones run")
    ap.add_argument("--windowed", action="store_true",
                    help="do not go full screen (only for debugging: the zones then do not line "
                         "up with the screen positions the gaze model predicts)")
    a = ap.parse_args()
    if a.check:
        a.mode = "check"
    if a.mode == "study" and not a.site:
        raise SystemExit("--site is required in study mode (S1..S4); see study/PROTOCOL.md")
    os.makedirs(a.out, exist_ok=True)

    for p in (a.model, a.landmarker):
        if not os.path.exists(p):
            raise SystemExit(f"missing {p} — see the README in this folder")
    items = json.load(open(a.items)) if os.path.exists(a.items) else \
        ["water", "blanket", "toilet", "tv", "light", "phone", "book", "food"]

    calib = None
    cal_path = os.path.join(a.out, f"calib_{a.pid}.json")
    if os.path.exists(cal_path) and not a.no_calib and not a.calibrate:
        calib = json.load(open(cal_path))
        print(f"using the calibration in {cal_path}: x' = {calib['ax']:.2f}x + {calib['bx']:.2f}")
    elif not a.calibrate:
        print("no calibration in use (calibration-free)")
    gaze = Gaze(a.model, a.landmarker, zones=a.zones, is_laptop=0 if a.desktop else 1,
                calib=calib, smooth_ms=a.smooth_ms)
    from camera import (diagnose_low_fps, measure_fps, measure_pipeline_fps,
                        open_camera)
    cap, cam_info = open_camera(a.camera, a.width, a.height)
    if not cap.isOpened():
        raise SystemExit("no camera")
    got_w, got_h = cam_info["width"], cam_info["height"]
    print(f"camera: asked for {a.width}x{a.height}, got {got_w}x{got_h} [{cam_info['fourcc']}]")
    if got_w < a.width:
        print("  the webcam would not give that resolution - try --width 1920 --height 1080, "
              "or a different --camera")
    # The frame rate is measured, not assumed. Everything downstream - the median window,
    # the dwell vote - is specified in milliseconds, but a camera running at a quarter speed
    # still puts so few samples inside a 500 ms dwell that the vote stops meaning anything.
    cam_fps = measure_fps(cap, seconds=2.0)
    print(f"camera: {cam_fps:.1f} fps measured")
    # The camera rate is not the rate selections are decided at. Time the real loop -
    # face detection and gaze prediction on real frames - because that is what fills the
    # dwell window. A machine can have a healthy camera and still be too slow to use.
    loop_fps, loop_ms = measure_pipeline_fps(cap, gaze, seconds=3.0)
    print(f"pipeline: {loop_fps:.1f} fps end to end ({loop_ms:.0f} ms/frame) - "
          f"about {loop_fps * 0.5:.0f} readings per dwell")
    if loop_fps < MIN_FPS:
        print(f"  the camera is fine but this machine takes {loop_ms:.0f} ms per frame, so a "
              f"{a.dwell_ms} ms dwell would hold only {loop_fps * a.dwell_ms / 1000:.0f} readings.")
        if a.study and not a.allow_slow:
            raise SystemExit(
                f"\nrefusing to start a study session: the pipeline runs at {loop_fps:.1f} fps "
                f"(need >= {MIN_FPS}).\nThis is the machine, not the camera. Close other "
                "applications and try again; if it stays slow the study needs a faster "
                "machine.\nUse --allow-slow-camera only for practice runs whose data is "
                "discarded.")
        print(f"  WARNING: pipeline at {loop_fps:.1f} fps - practice only, not study data.")
    if cam_fps < MIN_FPS:
        for t in diagnose_low_fps(cam_fps, cam_info):
            print("  - " + t)
        if a.study and not a.allow_slow:
            # Refuse rather than quietly collect data that cannot be pooled with the other
            # sites. A session at 7.5 fps looks normal on screen and is unusable afterwards.
            raise SystemExit(
                f"\nrefusing to start a study session at {cam_fps:.1f} fps (need >= {MIN_FPS}).\n"
                "Run  python camera_probe.py  and send the output to Sudaroli.\n"
                "Use --allow-slow-camera only for a practice run whose data will be discarded.")
        print(f"  WARNING: {cam_fps:.1f} fps is below {MIN_FPS} - practice only, not study data.")
    # Full screen matters: the model predicts where on the SCREEN the person is looking, so the
    # three zones must span the whole screen. In a small window every zone maps to the same x.
    cv2.namedWindow("GazeSpeakZero", cv2.WINDOW_NORMAL)
    if a.windowed:
        cv2.resizeWindow("GazeSpeakZero", 1000, 520)
    else:
        cv2.setWindowProperty("GazeSpeakZero", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    canvas = np.zeros((720, 1280, 3), np.uint8)
    xhist = []

    if a.calibrate:
        cal = calibrate(gaze, cap, canvas, a.pid, a.out)
        cap.release()
        cv2.destroyAllWindows()
        return 0 if cal else 1

    if a.mode == "study" and calib is None and not a.no_calib:
        # half the study blocks need a per-person correction, so collect it before the blocks
        calib = calibrate(gaze, cap, canvas, a.pid, a.out)
        canvas[:] = BG
        held = (calib or {}).get("zone_accuracy_held_out")
        msg = "calibration done - the study starts now"
        if held is not None and held < 0.5:
            msg = f"held-out accuracy only {held:.2f} - re-seat and run --calibrate again"
            print("\n*** the correction is poor. Re-seat, check the lighting, and run "
                  "  python gaze_ui.py --calibrate --pid <id>   before the blocks. ***\n")
        cv2.putText(canvas, msg, (60, 120), FONT, 0.9, INK, 2, cv2.LINE_AA)
        cv2.imshow("GazeSpeakZero", canvas)
        cv2.waitKey(1500)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(a.out, f"{a.pid}_{a.mode}_{stamp}.csv")
    log = csv.writer(open(log_path, "w", newline=""))
    import hashlib
    import subprocess
    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                             capture_output=True, text=True, timeout=5).stdout.strip() or "nogit"
    except Exception:
        rev = "nogit"
    model_sum = hashlib.md5(open(a.model, "rb").read()).hexdigest()[:10]
    meta = open(log_path.replace(".csv", "_meta.json"), "w")
    json.dump({"pid": a.pid, "site": a.site, "laptop": a.laptop, "lighting": a.lighting,
               "mode": a.mode, "zones": a.zones, "trials": a.trials,
               "requested_capture": [a.width, a.height], "granted_capture": [got_w, got_h],
               "dwell_ms": a.dwell_ms, "arm_ms": a.arm_ms, "smooth_ms": a.smooth_ms,
               "camera_fps": round(cam_fps, 1), "camera_fourcc": cam_info["fourcc"],
               "pipeline_fps": round(loop_fps, 1), "pipeline_ms_per_frame": round(loop_ms, 1),
               "readings_per_dwell": round(loop_fps * a.dwell_ms / 1000, 1),
               "camera_strategy": cam_info.get("strategy", "?"),
               "camera_wh": f"{got_w}x{got_h}", "fps_floor": MIN_FPS,
               "below_fps_floor": bool(cam_fps < MIN_FPS),
               "code_revision": rev, "model_md5": model_sum,
               # Library versions, because they differ between sites and we found that out
               # the slow way: probes were being validated against a different mediapipe
               # build from the one the operators were actually running.
               "python": platform.python_version(), "os": f"{platform.system()} {platform.release()}",
               "mediapipe": _ver("mediapipe"), "opencv": cv2.__version__,
               "numpy": _ver("numpy"), "sklearn": _ver("sklearn"),
               "started": time.strftime("%Y-%m-%dT%H:%M:%S")}, meta, indent=1)
    meta.close()
    print(f"session metadata: site={a.site or '-'} code={rev} model={model_sum}")

    log.writerow(["site", "t_ms", "block", "condition_pattern", "condition_guard", "condition_calib",
                  "trial", "cue_item",
                  "event", "zone", "item", "page", "detail", "frame_ms", "px", "py",
                  "eye_px", "cue_zone"])

    blocks = study_blocks(a.pid, a.trials) if a.mode == "study" else [(None, None, bool(calib), 0)]
    if a.mode == "study" and calib is None:
        blocks = [b for b in blocks if not b[2]]
        print("no calibration: running the four calibration-free blocks only")
    print(f"{len(blocks)} blocks x {a.trials} trials")
    t_start = time.time()
    frame_ms_hist = []
    slow_frames = total_frames = 0
    last_slow_warn = -1e9

    try:
        for bi, (pattern, guard, calibrated, n_trials) in enumerate(blocks):
            gaze.calib = calib if (calibrated and calib) else None
            eng = Engine(items=items, zones=a.zones,
                         pattern=pattern or "direct", guard=guard if a.mode == "study" else "double",
                         dwell_ms=a.dwell_ms, scan_ms=a.scan_ms, t0=(time.time() - t_start) * 1000)
            trial, cue_item, cue_zone, trial_t0 = 0, None, None, None
            if a.mode == "study":
                trial = 1
                cue_item, trial_t0 = begin_trial(
                    eng, items, canvas, trial, n_trials, a.pid, bi, t_start, first=True,
                    label=f"block {bi + 1} of {len(blocks)}: {pattern}, guard={guard or 'none'}, "
                          f"{'calibrated' if calibrated else 'no calibration'}")
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                # NO horizontal flip: the gaze model was trained on unflipped webcam frames,
                # and nothing shows the camera image, so flipping would only mirror left/right.
                t_ms = (time.time() - t_start) * 1000
                z, px, py, fms = gaze.zone_of(frame, t_ms)
                armed = (a.mode != "study") or (t_ms - trial_t0 >= a.arm_ms)
                if not armed:
                    z = None                      # still reading: measure, but do not select
                frame_ms_hist.append(fms)
                # The startup gate fires once. A 12-minute session on a machine whose load
                # changes can pass that gate and then degrade, which is exactly what happened
                # at one site: 48 ms/frame when checked, 89 ms/frame during the session, and
                # nothing noticed until the data was analysed days later. So watch it live.
                if len(frame_ms_hist) >= 40:
                    recent = float(np.median(frame_ms_hist[-40:]))
                    slow_now = recent > (1000.0 / MIN_FPS)
                    slow_frames += 1 if slow_now else 0
                    total_frames += 1
                    if slow_now and t_ms - last_slow_warn > 4000:
                        last_slow_warn = t_ms
                        print(f"  SLOW: {recent:.0f} ms/frame ({1000 / recent:.1f} fps) - "
                              "close other applications", flush=True)
                if px == px:
                    xhist.append(px)
                    xhist = xhist[-150:]                      # about 5 seconds
                if z is None and a.mode != "check":          # never leave a stale highlight up
                    draw(canvas, [""] * a.zones, None,
                         banner="face not found - sit back in view of the camera", sub="")
                    cv2.imshow("GazeSpeakZero", canvas)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        return report(log_path, frame_ms_hist, slow_frames, total_frames)
                if a.mode == "check":
                    rng_txt = (f"x range over 5 s: {min(xhist):.2f}-{max(xhist):.2f}"
                               if len(xhist) > 5 else "x range: collecting")
                    draw(canvas, [f"zone {i}" for i in range(a.zones)], z,
                         banner=f"camera OK  |  face: {'yes' if z is not None else 'no'}",
                         sub=f"{np.median(frame_ms_hist[-60:]):.0f} ms/frame  |  x={px:.2f}  |  "
                             f"{rng_txt}  |  press q to quit")
                    cv2.imshow("GazeSpeakZero", canvas)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        return report(log_path, frame_ms_hist, slow_frames, total_frames)
                    continue

                evs = eng.tick(t_ms, z)
                screen = eng.screen()
                cue_zone = screen.index(cue_item) if (cue_item in screen) else None
                _lf = gaze.last_features or {}
                _epx = np.nanmean([_lf.get("reye_width_px", np.nan),
                                   _lf.get("leye_width_px", np.nan)])
                for e in evs:
                    log.writerow([a.site, round(e.t_ms, 1), bi, pattern, guard or "none",
                                  "calibrated" if calibrated else "free", trial, cue_item, e.kind,
                                  e.zone, e.item, e.page, e.detail, round(fms, 2),
                                  round(px, 4) if px == px else "", round(py, 4) if py == py else "",
                                  round(float(_epx), 1) if _epx == _epx else "",
                                  cue_zone if cue_zone is not None else ""])
                sel = [e for e in evs if e.kind == "select"]
                banner = ("" if a.mode == "study" else "Look at what you want")
                if total_frames and slow_frames / total_frames > 0.10 and a.mode == "study":
                    cv2.putText(canvas, "computer running slowly - close other apps",
                                (30, canvas.shape[0] - 70), FONT, 0.7, BAD, 2, cv2.LINE_AA)
                if a.mode == "study" and not armed:
                    cv2.putText(canvas, "read the three words", (30, 60), FONT, 0.8, DIM, 2,
                                cv2.LINE_AA)
                sub = (f"block {bi + 1}/{len(blocks)}  trial {trial}/{n_trials}  "
                       f"[{pattern}, guard={guard or 'none'}, "
                       f"{'calibrated' if calibrated else 'no calibration'}]  |  q quits, n skips"
                       if a.mode == "study" else f"[scene items]  |  q quits")
                draw(canvas, screen, z, cue=cue_zone, banner=banner, sub=sub, pending=eng.pending)
                if sel:
                    hit = (sel[0].item == cue_item)
                    cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 12), GOOD if hit else BAD, -1)
                cv2.imshow("GazeSpeakZero", canvas)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    return report(log_path, frame_ms_hist, slow_frames, total_frames)
                if sel or key == ord("n"):
                    if a.mode != "study":
                        continue
                    log.writerow([a.site, round(t_ms, 1), bi, pattern, guard or "none",
                                  "calibrated" if calibrated else "free", trial, cue_item, "trial_end",
                                  "", sel[0].item if sel else "", "", "skipped" if not sel else "",
                                  round(t_ms - trial_t0, 1), "", "",
                                  round(float(_epx), 1) if _epx == _epx else "",
                                  cue_zone if cue_zone is not None else ""])
                    trial += 1
                    if trial > n_trials:
                        break
                    # begin_trial also moves "next" from side to side so cued items are not
                    # always in the same zone: with it fixed, every direct trial at two
                    # zones cued the left.
                    cue_item, trial_t0 = begin_trial(
                        eng, items, canvas, trial, n_trials, a.pid, bi, t_start)
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return report(log_path, frame_ms_hist, slow_frames, total_frames)


def _ver(mod):
    """Installed version of a module, for the session record. Never fatal."""
    try:
        m = __import__(mod)
        return getattr(m, "__version__", "?")
    except Exception:
        return "not installed"


def pick_cue(eng, items, seed):
    """Cue an item that is ON SCREEN, so one correct look can reach it.
    Paging is not part of what this study measures - E4 already models it - and cueing an item
    on a later page makes the trial unreachable rather than hard.

    This reads eng.screen(), so the engine must already be on the page the trial will
    START on. Call begin_trial() rather than calling this directly."""
    on_screen = [i for i in eng.screen() if i and i.lower() not in ("next", "more", "")]
    return random.Random(seed).choice(on_screen or items)


def begin_trial(eng, items, canvas, trial, n_trials, pid, bi, t_start,
                first=False, label=""):
    """Start a trial, in the one order that is correct.

    The order matters and is easy to get wrong - it was wrong here, in two places, and
    cost 8 of 77 trials in the first live session. `reset()` sends the page back to 0, so
    the cue must be chosen AFTER that reset or it is chosen from the page the previous
    trial happened to end on, and the cued word is then not on screen at all. But the
    reset also re-bases the scanning timer, so it has to happen again AFTER the cue
    screen, or the page auto-advances the instant the trial begins.

    Hence: reset, pick, show, reset. Encapsulated here so no call site has to remember.
    """
    eng.next_first = random.Random(f"{pid}-{bi}-{trial}-side").random() < 0.5
    eng.reset((time.time() - t_start) * 1000)          # page -> 0 BEFORE choosing the cue
    cue_item = pick_cue(eng, items, f"{pid}-{bi}-{trial}")
    # The guarantee this function exists to provide, checked rather than assumed.
    if cue_item not in eng.screen():
        raise RuntimeError(
            f"cue {cue_item!r} is not on the starting screen {eng.screen()!r} - "
            "the trial would be unreachable and would score as an error")
    show_cue(canvas, cue_item, trial, n_trials, first=first, label=label)
    eng.reset((time.time() - t_start) * 1000)          # re-base the scan timer after the cue
    return cue_item, (time.time() - t_start) * 1000


def show_cue(canvas, item, trial, n_trials, seconds=1.6, first=False, label=""):
    """The word to choose, alone in the middle of the screen. Nothing is measured here, so
    reading it cannot be mistaken for a selection."""
    h, w = canvas.shape[:2]
    end = time.time() + (seconds + 1.4 if first else seconds)
    while time.time() < end:
        canvas[:] = BG
        if label:
            cv2.putText(canvas, label, (30, 60), FONT, 0.8, DIM, 2, cv2.LINE_AA)
        cv2.putText(canvas, "choose:", (int(w / 2) - 70, int(h / 2) - 70), FONT, 0.9, DIM, 2, cv2.LINE_AA)
        size = cv2.getTextSize(item, FONT, 2.0, 3)[0]
        cv2.putText(canvas, item, (int((w - size[0]) / 2), int(h / 2) + 30), FONT, 2.0, INK, 3, cv2.LINE_AA)
        cv2.putText(canvas, f"trial {trial} of {n_trials}", (30, h - 40), FONT, 0.6, DIM, 1, cv2.LINE_AA)
        cv2.imshow("GazeSpeakZero", canvas)
        if cv2.waitKey(30) & 0xFF == ord("q"):
            return False
    return True


def report(log_path, frame_ms_hist, slow_frames=0, total_frames=0):
    """Close the session out, and write what actually happened into the metadata.

    The metadata is written before the session starts, so it records intentions. This
    adds the outcome - in particular how much of the session ran below the frame-rate
    floor, which is the one thing that silently ruins a session and cannot be recovered
    afterwards from anything else in the log.
    """
    print(f"\nsession log: {log_path}")
    med = pct = None
    if frame_ms_hist:
        h = np.array(frame_ms_hist)
        med = float(np.median(h))
        print(f"per-frame processing: median {med:.1f} ms, 95th {np.percentile(h, 95):.1f} ms "
              f"({1000 / max(1e-6, med):.1f} fps)")
    if total_frames:
        pct = 100.0 * slow_frames / total_frames
        print(f"time spent below the {MIN_FPS:.0f} fps floor: {pct:.1f}% of the session")
        if pct > 10:
            print("  ^ a meaningful part of this session ran too slowly. Selections were")
            print("    decided from fewer readings than intended. Tell Sudaroli before")
            print("    treating this as study data.")
    meta_path = log_path.replace(".csv", "_meta.json")
    try:
        with open(meta_path) as f:
            m = json.load(f)
        m["session_median_ms_per_frame"] = round(med, 1) if med is not None else None
        m["session_pct_below_fps_floor"] = round(pct, 1) if pct is not None else None
        m["session_frames"] = int(total_frames)
        with open(meta_path, "w") as f:
            json.dump(m, f, indent=1)
    except Exception as e:
        print(f"(could not update {os.path.basename(meta_path)}: {type(e).__name__})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
