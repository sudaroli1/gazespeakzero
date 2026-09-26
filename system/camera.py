"""Camera opening, shared by setup_check.py, camera_probe.py and gaze_ui.py.

Why this file exists
--------------------
A webcam asked for 1280x720 hands back whatever pixel format the driver prefers,
and that is very often YUY2 (uncompressed): 1280*720*2 = 1.84 MB per frame, which
over USB 2.0 tops out around 7-10 fps. The same camera in MJPG, compressed on the
camera itself, manages 30 fps at the same size.

The catch is that asking for MJPG is a *request*. `cap.set(CAP_PROP_FOURCC, ...)`
returns True whether or not the driver honoured it, and on Windows's DirectShow
backend it is frequently ignored outright. An earlier version of this file set the
format, read back the value it had just asked for, and believed it. Two operators
lost an evening to that.

So the format is never assumed here. Several ways of asking are tried, the frame
rate of each is MEASURED, and the one that actually delivers is kept. The winner
is cached so only the first run pays for the search.

Why not just drop to 640x480 and take the frame rate for free: at 480p the iris is
too few pixels across to carry the signal (measured signal-to-noise 0.50 and
correlation -0.007 with true gaze, against 7.07 and +0.881 at 720p). A fast feed
of useless frames is worse than a slow one, because it looks like it is working.
"""
import json
import os
import platform
import time

import cv2

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "camera_choice.json")
MIN_USABLE_FPS = 15.0


def _is_windows():
    return os.name == "nt"


def _fourcc_str(v) -> str:
    v = int(v)
    if v <= 0:
        return "?"
    s = "".join(chr((v >> (8 * i)) & 0xFF) for i in range(4))
    return s if s.isprintable() else "?"


def _backends():
    """(label, cv2 backend id) worth trying, most likely first."""
    if _is_windows():
        out = [("dshow", getattr(cv2, "CAP_DSHOW", 700))]
        if hasattr(cv2, "CAP_MSMF"):
            # Media Foundation often negotiates MJPG where DirectShow will not.
            out.append(("msmf", cv2.CAP_MSMF))
        return out
    if platform.system() == "Darwin":
        return [("avfoundation", getattr(cv2, "CAP_AVFOUNDATION", 1200)), ("default", 0)]
    return [("v4l2", getattr(cv2, "CAP_V4L2", 200)), ("default", 0)]


def _strategies():
    """Ways of asking, tried in order. Order matters: some drivers ignore a format
    change once the resolution is fixed, others ignore the resolution if the format
    is set first, and a few only cooperate if the frame rate is requested too."""
    for blabel, backend in _backends():
        for order in ("fourcc_first", "size_first"):
            yield (f"{blabel}, mjpg {order.replace('_', ' ')}", backend, order, True, False)
        yield (f"{blabel}, mjpg + fps hint", backend, "fourcc_first", True, True)
    for blabel, backend in _backends():
        yield (f"{blabel}, no format request", backend, "size_first", False, False)


def _apply(cap, width, height, order, mjpg, fps_hint):
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    if order == "fourcc_first":
        if mjpg:
            cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    else:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if mjpg:
            cap.set(cv2.CAP_PROP_FOURCC, fourcc)
    if fps_hint:
        cap.set(cv2.CAP_PROP_FPS, 30)


def _observe(cap):
    return (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
            _fourcc_str(cap.get(cv2.CAP_PROP_FOURCC)))


def measure_fps(cap, seconds=3.0, warmup=10):
    """Frames actually delivered per second.

    The first frames after opening are slow - the driver is settling and
    auto-exposure is still hunting - so they are discarded rather than dragging a
    healthy camera below the threshold.
    """
    for _ in range(warmup):
        cap.read()
    t0, n = time.perf_counter(), 0
    while time.perf_counter() - t0 < seconds:
        if cap.read()[0]:
            n += 1
    dt = time.perf_counter() - t0
    return n / dt if dt > 0 else 0.0


def _try_one(index, width, height, spec, measure_s=1.2):
    label, backend, order, mjpg, fps_hint = spec
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        cap.release()
        return None
    _apply(cap, width, height, order, mjpg, fps_hint)
    w, h, fourcc = _observe(cap)
    fps = measure_fps(cap, seconds=measure_s, warmup=5)
    return {"label": label, "backend": backend, "order": order, "mjpg": mjpg,
            "fps_hint": fps_hint, "width": w, "height": h, "fourcc": fourcc,
            "fps": fps, "cap": cap}


def _score(r, width, height):
    """Big enough first, then fast enough, then fastest."""
    big = r["width"] >= width and r["height"] >= height
    return (1 if big else 0, 1 if r["fps"] >= MIN_USABLE_FPS else 0, r["fps"])


def open_camera(index=0, width=1280, height=720, prefer_mjpg=True, search=None, report=None):
    """Open the camera the way that actually works on this machine.

    Returns (cap, info). info carries width/height/fourcc/fps/strategy/searched.
    Never raises on a shortfall - the caller decides what to do about it.
    """
    if search is None:                      # search unless told otherwise
        search = prefer_mjpg
    cached = _load_cache()
    if cached:
        spec = (cached["label"], cached["backend"], cached["order"],
                cached["mjpg"], cached["fps_hint"])
        r = _try_one(index, width, height, spec)
        if r and _score(r, width, height)[:2] == (1, 1):
            cap = r.pop("cap")
            r.update(opened=True, requested=(width, height), strategy=r["label"],
                     searched=False)
            return cap, r
        if r:
            r["cap"].release()              # cached choice no longer delivers

    if not search:
        spec = (f"plain", _backends()[0][1], "fourcc_first", prefer_mjpg, False)
        r = _try_one(index, width, height, spec, measure_s=0.6)
        if r is None:
            return cv2.VideoCapture(index), {"opened": False, "width": 0, "height": 0,
                                             "fourcc": "?", "fps": 0.0,
                                             "requested": (width, height),
                                             "strategy": "none", "searched": False}
        cap = r.pop("cap")
        r.update(opened=True, requested=(width, height), strategy=r["label"], searched=False)
        return cap, r

    tried, best = [], None
    for spec in _strategies():
        r = _try_one(index, width, height, spec)
        if r is None:
            tried.append({"label": spec[0], "opened": False})
            continue
        tried.append({k: r[k] for k in ("label", "width", "height", "fourcc", "fps")})
        if report:
            report(tried[-1])
        if best is None or _score(r, width, height) > _score(best, width, height):
            if best is not None:
                best["cap"].release()
            best = r
        else:
            r["cap"].release()
        if _score(best, width, height)[:2] == (1, 1):
            break                            # good enough; stop burning time

    if best is None:
        return cv2.VideoCapture(index), {"opened": False, "width": 0, "height": 0,
                                         "fourcc": "?", "fps": 0.0, "tried": tried,
                                         "requested": (width, height),
                                         "strategy": "none", "searched": True}
    cap = best.pop("cap")
    info = dict(best, opened=True, requested=(width, height), strategy=best["label"],
                tried=tried, searched=True)
    if _score(best, width, height)[:2] == (1, 1):
        _save_cache(best)
    return cap, info


def _load_cache():
    try:
        with open(CACHE) as f:
            d = json.load(f)
        if all(k in d for k in ("label", "backend", "order", "mjpg", "fps_hint")):
            return d
    except Exception:
        pass
    return None


def _save_cache(r):
    try:
        with open(CACHE, "w") as f:
            json.dump({k: r[k] for k in ("label", "backend", "order", "mjpg", "fps_hint")}, f)
    except Exception:
        pass


def diagnose_low_fps(fps, info):
    """Turn a low frame rate into something the person at the other end can act on."""
    tips = []
    got_mjpg = info.get("fourcc", "?").upper() in ("MJPG", "MJPB")
    if not got_mjpg:
        tips.append(
            f"the camera insists on {info.get('fourcc')} (uncompressed) - every way of "
            "asking for MJPG was tried and refused. Uncompressed 720p does not fit "
            "through USB 2.0 at 15 fps. Plug the camera straight into the laptop rather "
            "than a hub, dock or monitor, and prefer a blue USB 3 port. A built-in "
            "webcam that does this is usually just an older sensor.")
    else:
        tips.append(
            "the camera IS sending compressed frames, so bandwidth is not the limit. "
            "That points at light: in a dim room the camera holds the shutter open "
            "longer and drops to 15 or 7.5 fps. Put a lamp or window in front of the "
            "face, not behind, and run this again.")
    if 6.5 <= fps <= 8.5 or 9 <= fps <= 11 or 14 <= fps <= 16:
        tips.append(
            "frame rates land on round numbers like 30, 15, 10 and 7.5 when the camera "
            "is choosing a slower mode rather than struggling - so this is a setting "
            "somewhere, not a tired machine.")
    tips.append("close anything else using the camera (Teams, Zoom, Meet, the Camera app).")
    tips.append(
        "we cannot solve this by using a smaller picture: at 640x480 the iris is too few "
        "pixels across to tell where the eye is pointing, so the session would run fast "
        "and mean nothing. If no setting gets this camera to 15 fps at 1280x720, we will "
        "use a different camera or a different machine.")
    return tips

def measure_pipeline_fps(cap, gaze, seconds=4.0, warmup=5):
    """How fast the loop that ACTUALLY DECIDES SELECTIONS can run.

    This is the number that matters, and it is not the camera's frame rate. The camera
    can deliver 22 fps while the machine takes 89 ms to find the face and predict gaze -
    in which case selections are decided at 11 fps, and a 500 ms dwell holds 5 readings
    instead of 15. That happened at a real site: the camera check passed, the session ran,
    and per-trial accuracy came out twenty points lower than on a faster machine.

    measure_fps() above times cap.read() alone. It answers "is the camera healthy".
    This answers "can this machine run the system", which is the question the gate needs.

    Returns (fps, median_ms_per_frame).
    """
    import time as _t
    for _ in range(warmup):
        ok, frame = cap.read()
        if ok:
            gaze.zone_of(frame, _t.perf_counter() * 1000.0)
    times, t0 = [], _t.perf_counter()
    while _t.perf_counter() - t0 < seconds:
        ok, frame = cap.read()
        if not ok:
            continue
        t1 = _t.perf_counter()
        gaze.zone_of(frame, t1 * 1000.0)
        times.append((_t.perf_counter() - t1) * 1000.0)
    if not times:
        return 0.0, float("nan")
    elapsed = _t.perf_counter() - t0
    import statistics
    return len(times) / elapsed, statistics.median(times)
