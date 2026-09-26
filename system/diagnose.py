"""
20-second diagnostic: do the features move when the eyes move, and does the model follow?

    python diagnose.py            # look LEFT, then CENTRE, then RIGHT when prompted

Prints, for each phase, the mean of the features that should carry the horizontal gaze, and
the model's predicted screen x. Writes nothing but a small CSV of the numbers; no images.
"""
from __future__ import annotations

import os
import sys
import time

import cv2
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "analysis", "study1_zone_classification"))
from extract_features import features_from_result  # noqa: E402

WATCH = ["reye_h", "leye_h", "reye_v", "leye_v", "bs_eyeLookOutLeft", "bs_eyeLookInLeft",
         "bs_eyeLookOutRight", "bs_eyeLookInRight", "yaw", "nose_x"]
PHASES = [("LOOK FAR LEFT", 6), ("LOOK AT THE CENTRE", 6), ("LOOK FAR RIGHT", 6)]


def main():
    import joblib
    import mediapipe as mp
    b = joblib.load(os.path.join(HERE, "gaze_model.joblib"))
    feats = b["features"]
    base = mp.tasks.BaseOptions(model_asset_path=os.path.join(HERE, "face_landmarker.task"))
    lm = mp.tasks.vision.FaceLandmarker.create_from_options(
        mp.tasks.vision.FaceLandmarkerOptions(
            base_options=base, running_mode=mp.tasks.vision.RunningMode.VIDEO,
            output_face_blendshapes=True, output_facial_transformation_matrixes=True, num_faces=1))
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if os.name == "nt" else 0)
    if not cap.isOpened():
        raise SystemExit("no camera")

    rows, t0, ts = [], time.time(), 0
    print("\nFollow the prompts. Keep your head still and move only your eyes.\n")
    for name, secs in PHASES:
        print(f"--> {name} for {secs} seconds ...", flush=True)
        end = time.time() + secs
        while time.time() < end:
            ok, frame = cap.read()
            if not ok:
                continue
            h, w = frame.shape[:2]
            ts += 33
            res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,
                                               data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), ts)
            f = features_from_result(res, w, h)
            if not f.get("detected"):
                continue
            f["is_laptop"] = 1
            x = np.array([[f.get(k, np.nan) for k in feats]], float)
            f["pred_x"] = float(b["model_x"].predict(x)[0])
            f["pred_y"] = float(b["model_y"].predict(x)[0])
            f["n_missing_features"] = int(np.isnan(x).sum())
            f["phase"] = name
            rows.append(f)
    cap.release()

    d = pd.DataFrame(rows)
    if d.empty:
        raise SystemExit("no face was detected at all — check the camera and the lighting")
    cols = [c for c in WATCH if c in d.columns] + ["pred_x", "pred_y"]
    out = d.groupby("phase")[cols].mean().reindex([p for p, _ in PHASES]).round(3)
    print("\n" + out.to_string())
    print(f"\nframes: {len(d)} | features missing per frame (of {len(feats)}): "
          f"{d.n_missing_features.mean():.1f}")
    print(f"pred_x overall range: {d.pred_x.min():.3f} to {d.pred_x.max():.3f}")
    for c in ("reye_h", "leye_h", "bs_eyeLookOutLeft"):
        if c in d:
            print(f"{c}: range {d[c].min():.3f} to {d[c].max():.3f}")
    d.to_csv(os.path.join(HERE, "diagnose_raw.csv"), index=False)
    print("\nwrote diagnose_raw.csv — that file is what to attach when reporting a problem")


if __name__ == "__main__":
    main()
