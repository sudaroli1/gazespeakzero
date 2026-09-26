"""
E1, step 1: run MediaPipe FaceLandmarker on every MPIIFaceGaze image and save
per-frame features to one CSV per subject.

Usage
-----
python extract_features.py --data MPIIFaceGaze --model face_landmarker.task \
    --out features [--max-per-subject 50] [--subjects p00 p01]

Resumable: a subject whose CSV already holds every annotated frame is skipped.
A dry run (--max-per-subject) writes pNN.dry.csv, which analyze.py ignores.

Nothing here is tuned on the data. The features are the raw quantities that
the estimators in analyze.py consume.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time

import cv2
import numpy as np
import pandas as pd
from scipy.io import loadmat

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

# MediaPipe 478-point topology. "R" = the subject's right eye (image left).
R_OUT, R_IN, R_UP, R_LO = 33, 133, 159, 145
L_OUT, L_IN, L_UP, L_LO = 263, 362, 386, 374
R_IRIS, L_IRIS = 468, 473          # iris centres
NOSE_TIP = 1
ORIG_IRIS = slice(468, 478)        # exactly what the original repo averages

EYE_BLENDSHAPES = [
    "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight",
    "eyeLookUpLeft", "eyeLookUpRight", "eyeLookDownLeft", "eyeLookDownRight",
    "eyeBlinkLeft", "eyeBlinkRight", "eyeSquintLeft", "eyeSquintRight",
]


def read_annotations(subject_dir: str) -> pd.DataFrame:
    sid = os.path.basename(subject_dir.rstrip("/\\"))
    txt = os.path.join(subject_dir, f"{sid}.txt")
    rows = []
    with open(txt) as f:
        lines = [ln for ln in f if ln.strip()]
    for ln in lines:
        parts = ln.split()
        if len(parts) != 28:
            raise SystemExit(f"{txt}: expected 28 fields per line, got {len(parts)}: {ln[:80]!r}")
        rows.append(parts)
    cols = (["file", "gt_px_x", "gt_px_y"]
            + [f"ann_lm{i}_{a}" for i in range(6) for a in "xy"]
            + [f"ann_hr{i}" for i in range(3)] + [f"ann_ht{i}" for i in range(3)]
            + [f"ann_fc{i}" for i in range(3)] + [f"ann_gt{i}" for i in range(3)]
            + ["ann_eval_eye"])
    df = pd.DataFrame(rows, columns=cols)
    for c in cols:
        if c not in ("file", "ann_eval_eye"):
            df[c] = df[c].astype(float)
    df.insert(0, "subject", sid)
    return df


def read_screen(subject_dir: str) -> dict:
    m = loadmat(os.path.join(subject_dir, "Calibration", "screenSize.mat"))
    keys = {k.lower(): k for k in m if not k.startswith("__")}

    def g(dim, unit):
        hit = [v for k, v in keys.items() if dim in k and unit in k]
        if len(hit) != 1:
            raise SystemExit(f"screenSize.mat: cannot find {dim}/{unit} among {list(keys.values())}")
        return float(np.squeeze(m[hit[0]]))
    return {"screen_w_px": g("width", "pix"), "screen_h_px": g("height", "pix"),
            "screen_w_mm": g("width", "mm"), "screen_h_mm": g("height", "mm")}


def eye_features(P: np.ndarray, out_i, in_i, up_i, lo_i, iris_i, tag: str) -> dict:
    """Iris position inside the eye opening, in pixel space (aspect-correct)."""
    a, b, iris = P[out_i], P[in_i], P[iris_i]
    axis = b - a
    w = np.linalg.norm(axis) + 1e-9
    u = axis / w
    n = np.array([-u[1], u[0]])
    if n[1] < 0:            # make +v point down the image for both eyes
        n = -n
    d = iris - a
    up, lo = P[up_i], P[lo_i]
    open_h = np.linalg.norm(lo - up) + 1e-9
    denom = (lo - up) @ n
    vlid = float(np.clip(((iris - up) @ n) / denom, -1.0, 2.0)) if open_h / w >= 0.05 and abs(denom) > 1e-6 else float("nan")
    return {
        f"{tag}_h": float(d @ u / w),                 # 0 = outer corner, 1 = inner (mirrored between eyes by design)
        f"{tag}_v": float(d @ n / w),                 # offset below the corner line, same sign for both eyes
        f"{tag}_vlid": vlid,                          # 0 = upper lid, 1 = lower lid; NaN when the eye is nearly shut
        f"{tag}_open": float(open_h / w),
        f"{tag}_width_px": float(w),
    }


def rotation_features(M: np.ndarray) -> dict:
    A = M[:3, :3]
    t = M[:3, 3]
    U, S, Vt = np.linalg.svd(A)          # strip any scale: nearest rotation
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U[:, -1] *= -1
        R = U @ Vt
    # Euler angles (degrees) for R = Rz(roll) @ Ry(yaw) @ Rx(pitch)
    sy = np.clip(-R[2, 0], -1.0, 1.0)
    yaw = np.degrees(np.arcsin(sy))
    pitch = np.degrees(np.arctan2(R[2, 1], R[2, 2]))
    roll = np.degrees(np.arctan2(R[1, 0], R[0, 0]))
    f = {f"R{i}{j}": float(R[i, j]) for i in range(3) for j in range(3)}
    f.update({"tx": float(t[0]), "ty": float(t[1]), "tz": float(t[2]), "R_scale": float(S.mean()),
              "yaw": float(yaw), "pitch": float(pitch), "roll": float(roll)})
    return f


def process_image(landmarker, path: str) -> dict:
    bgr = cv2.imread(path)
    if bgr is None:
        return {"detected": 0, "read_error": 1}
    H, W = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    t0 = time.perf_counter()
    res = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    dt = (time.perf_counter() - t0) * 1000
    out = {"img_w": W, "img_h": H, "landmark_ms": dt, "read_error": 0}
    out.update(features_from_result(res, W, H))
    return out


def features_from_result(res, W: int, H: int) -> dict:
    """Per-frame features from a FaceLandmarker result (shared by E1 and E1b)."""
    out = {}
    if not res.face_landmarks:
        out["detected"] = 0
        return out
    lms = res.face_landmarks[0]
    out["detected"] = 1
    out["n_landmarks"] = len(lms)
    xy = np.array([[p.x, p.y] for p in lms])           # normalised
    P = xy * np.array([W, H])                           # pixels

    # --- M0: the original repo, verbatim arithmetic ---
    iris = xy[ORIG_IRIS]
    out["m0_px"] = float(iris[:, 0].mean())
    out["m0_py"] = float(iris[:, 1].mean())
    out["m0_cx"] = out["m0_px"] - float(xy[NOSE_TIP, 0]) + 0.5
    out["m0_cy"] = out["m0_py"] - float(xy[NOSE_TIP, 1]) + 0.5

    out.update(eye_features(P, R_OUT, R_IN, R_UP, R_LO, R_IRIS, "reye"))
    out.update(eye_features(P, L_OUT, L_IN, L_UP, L_LO, L_IRIS, "leye"))
    out["nose_x"] = float(xy[NOSE_TIP, 0])
    out["nose_y"] = float(xy[NOSE_TIP, 1])
    out["interocular_norm"] = float(np.linalg.norm(P[R_IRIS] - P[L_IRIS]) / W)
    for k, idx in (("mp_rout", R_OUT), ("mp_rin", R_IN), ("mp_lout", L_OUT), ("mp_lin", L_IN)):
        out[f"{k}_x"], out[f"{k}_y"] = float(P[idx, 0]), float(P[idx, 1])

    if res.face_blendshapes:
        bs = {c.category_name: c.score for c in res.face_blendshapes[0]}
        for k in EYE_BLENDSHAPES:
            out[f"bs_{k}"] = float(bs.get(k, np.nan))
    if res.facial_transformation_matrixes:
        out.update(rotation_features(np.asarray(res.facial_transformation_matrixes[0])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="path to the unzipped MPIIFaceGaze folder")
    ap.add_argument("--model", required=True, help="face_landmarker.task")
    ap.add_argument("--out", default="features")
    ap.add_argument("--subjects", nargs="*", default=None)
    ap.add_argument("--max-per-subject", type=int, default=None,
                    help="dry run: first N images of each subject")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    subj_dirs = sorted(d for d in glob.glob(os.path.join(args.data, "p[0-9][0-9]")) if os.path.isdir(d))
    if args.subjects:
        subj_dirs = [d for d in subj_dirs if os.path.basename(d) in args.subjects]
    if not subj_dirs:
        sys.exit(f"No pNN folders found under {args.data}")

    opts = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=args.model),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
    )
    with vision.FaceLandmarker.create_from_options(opts) as lm:
        for sd in subj_dirs:
            sid = os.path.basename(sd)
            dry = args.max_per_subject is not None
            dest = os.path.join(args.out, f"{sid}.dry.csv" if dry else f"{sid}.csv")
            ann = read_annotations(sd)
            if not dry and os.path.exists(dest):
                n_have = len(pd.read_csv(dest, usecols=["file"]))
                if n_have == len(ann):
                    print(f"{sid}: complete ({n_have} frames), skipping")
                    continue
                print(f"{sid}: incomplete ({n_have}/{len(ann)}), redoing")
            if dry:
                ann = ann.iloc[:args.max_per_subject]
            scr = read_screen(sd)
            recs = []
            t0 = time.time()
            for i, row in enumerate(ann.itertuples(index=False)):
                r = process_image(lm, os.path.join(sd, row.file))
                recs.append(r)
                if (i + 1) % 500 == 0:
                    print(f"  {sid} {i+1}/{len(ann)}  {time.time()-t0:.0f}s", flush=True)
            feat = pd.DataFrame(recs)
            df = pd.concat([ann.reset_index(drop=True), feat], axis=1)
            for k, v in scr.items():
                df[k] = v
            df.to_csv(dest + ".tmp", index=False)
            os.replace(dest + ".tmp", dest)
            print(f"{sid}: {len(df)} frames, detected {df['detected'].mean():.3f}, "
                  f"unreadable {int(df['read_error'].sum())}, {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
