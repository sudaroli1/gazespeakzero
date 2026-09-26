"""
Run this FIRST on a new machine. It checks everything the session needs and prints
a clear go / no-go. It touches no files and records nothing.

    python setup_check.py
"""
from __future__ import annotations
import os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ok = True


def check(label, passed, detail=""):
    global ok
    ok = ok and passed
    print(f"  [{'OK  ' if passed else 'FAIL'}] {label}{(' - ' + detail) if detail else ''}")


print("\nGazeSpeakZero - setup check\n" + "-" * 46)
v = sys.version_info
check(f"Python {v.major}.{v.minor}", v.major == 3 and v.minor in (11, 12),
      "needs 3.11 or 3.12; 3.14 has no mediapipe/scikit-learn wheels")

for mod in ("cv2", "mediapipe", "numpy", "pandas", "sklearn", "joblib"):
    try:
        __import__(mod)
        check(f"import {mod}", True)
    except Exception as e:
        check(f"import {mod}", False, str(e)[:60])

# Every file the session actually needs, with where it must sit. gaze_ui.py adds
# ../analysis/study1_zone_classification to sys.path and imports from it, so a folder with only `system/` in it
# cannot run even though it looks complete.
REQUIRED = [
    ("gaze_model.joblib",          os.path.join(HERE, "gaze_model.joblib"),               100_000),
    ("face_landmarker.task",       os.path.join(HERE, "face_landmarker.task"),            100_000),
    ("engine.py",                  os.path.join(HERE, "engine.py"),                           500),
    ("camera.py",                  os.path.join(HERE, "camera.py"),                           500),
    ("analysis/study1_zone_classification/extract_features.py",
     os.path.join(HERE, "..", "analysis", "study1_zone_classification", "extract_features.py"), 500),
]
missing = []
for label, path, min_size in REQUIRED:
    size = os.path.getsize(path) if os.path.exists(path) else 0
    present = size >= min_size
    if not present:
        missing.append(label)
    check(f"{label} present", present, f"{size} bytes" if size else "missing")

# A folder holding only the patch files looks like a normal install until you run
# it. Name that situation instead of leaving someone to puzzle over two missing
# files they were never sent.
looks_like_patch = ("gaze_model.joblib" in missing and "engine.py" in missing)

tips = []
if ok:
    import cv2
    from camera import (diagnose_low_fps, measure_fps, measure_pipeline_fps,
                        open_camera)

    print("  ...testing camera modes, this takes a few seconds", flush=True)
    cap, info = open_camera(0, 1280, 720)
    check("camera opens", info["opened"])
    tips = []
    if info["opened"]:
        w, h = info["width"], info["height"]
        check("camera gives 1280x720 or better", w >= 1280 and h >= 720, f"got {w}x{h}")
        # Asking for MJPG is a request, not a command - several drivers accept the call
        # and ignore it. So the format reported here is what the camera actually sent
        # after trying every way of asking, not what we asked for.
        check("camera sends MJPG (compressed)", info["fourcc"].upper() in ("MJPG", "MJPB"),
              f"format is {info['fourcc']}")
        # Measured over 3 s after a warm-up, because the first frames out of a
        # freshly opened camera are always slow and would fail a healthy machine.
        fps = measure_fps(cap, seconds=3.0)
        check("frame rate >= 15 fps", fps >= 15, f"{fps:.1f} fps")
        if info.get("strategy"):
            # Distinguish a fresh search from a remembered choice - "best of 1 modes
            # tried" is misleading when nothing was searched at all.
            if info.get("searched"):
                print(f"         (best of {len(info.get('tried', []))} camera modes tried: "
                      f"{info['strategy']})")
            else:
                print(f"         (using the remembered camera mode: {info['strategy']}; "
                      f"delete camera_choice.json to search again)")
        if fps < 15:
            tips = diagnose_low_fps(fps, info)

        # The camera rate above is NOT the rate at which selections are decided. On one
        # machine the camera delivered 21.6 fps while the gaze stage took 89 ms a frame,
        # so the real loop ran at 11 fps and a 500 ms dwell held 5 readings instead of 15.
        # That session passed the camera check and lost twenty points of accuracy.
        # So time the whole loop, with the real model, on real frames.
        print("  ...timing the full pipeline on this machine", flush=True)
        try:
            from gaze_ui import Gaze
            _g = Gaze(os.path.join(HERE, "gaze_model.joblib"),
                      os.path.join(HERE, "face_landmarker.task"), zones=2)
            pfps, pms = measure_pipeline_fps(cap, _g, seconds=4.0)
            check("pipeline keeps up (>= 15 fps end to end)", pfps >= 15,
                  f"{pfps:.1f} fps, {pms:.0f} ms/frame")
            print(f"         (a 500 ms dwell holds about {pfps * 0.5:.0f} readings here; "
                  f"below ~8 the selection vote gets coarse)")
            if pfps < 15:
                tips = tips + [
                    f"the camera is fine but this machine needs {pms:.0f} ms to find the face "
                    "and predict gaze, so selections would be decided from too few readings. "
                    "Close other applications and try once more; if it stays this slow the "
                    "study needs a faster machine, and that is not something you did wrong.",
                    "this is a separate problem from the camera - do not spend time on USB "
                    "ports or lighting for it."]
        except Exception as e:                    # never let the check itself be the failure
            print(f"         (could not time the pipeline: {type(e).__name__}: {e})")
        cap.release()

print("-" * 46)
if looks_like_patch:
    print("This folder has the update files but not the full study package -")
    print("the model and the rest of the code are not here. That is a packaging")
    print("mistake at my end, not anything you did wrong.")
    print("Ask Sudaroli for gazespeakzero_full_package.zip, unzip it somewhere")
    print("fresh, and run this check again from inside its prototype folder.")
    print("-" * 46)
elif missing:
    print("Some files the session needs are not in place:")
    for m in missing:
        print("  - " + m)
    print("They should sit beside the others exactly as they came out of the zip.")
    print("If you moved files around, unzip a fresh copy rather than rebuilding it.")
    print("-" * 46)
if tips:
    print("Why the frame rate might be low:")
    for t in tips:
        print("  - " + t)
    print("  Then run:  python camera_probe.py   and send the output.")
    print("-" * 46)
print("READY - go ahead and run the session." if ok else
      "NOT READY - send the lines marked FAIL to Sudaroli before going further.")
