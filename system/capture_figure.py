"""
Capture the illustrative images for the paper's qualitative figure.

    python capture_figure.py --name author

THIS TOOL WRITES IMAGES TO DISK. The study software (gaze_ui.py) never does, by
design, and this file is deliberately separate from it so that the guarantee in
the protocol stays true: no camera frame is written during any study session.
Use it only on yourself, outside a session, and only for the figure.

It captures the same face at 640x480 and at 1280x720, runs the same landmarker
the system uses, and writes:

  fig_raw_<name>_frame720.png   the 720p frame with the eye landmarks drawn
  fig_raw_<name>_eye480.png     the right-eye crop as seen at 640x480
  fig_raw_<name>_eye720.png     the same eye at 1280x720
  fig_raw_<name>_measures.json  eye width in pixels at each resolution

The two eye crops are written at their true pixel size AND upscaled to a common
display size with nearest-neighbour, so the difference in available detail is
visible rather than argued.
"""
from __future__ import annotations
import argparse, json, os, sys, time
import cv2, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "analysis", "study1_zone_classification"))
from extract_features import features_from_result  # noqa: E402

# Written outside the repository by default: these are photographs of a face,
# and the published repository contains no image of any person. The directory
# is in .gitignore as a second line of defence.
OUT = os.path.join(HERE, "..", "captures")
from extract_features import R_OUT, R_IN    # the same landmarks the features use (33, 133)


def grab(cap, lm, w, h, settle=1.2):
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    got_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    got_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    t_end = time.time() + settle
    frame = None
    while time.time() < t_end:                # let exposure settle
        ok, f = cap.read()
        if ok:
            frame = f
    if frame is None:
        raise SystemExit(f"no frame at {w}x{h}")
    res = lm.detect_for_video(
        __import__("mediapipe").Image(
            image_format=__import__("mediapipe").ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)),
        int(time.time() * 1000) % 100000)
    return frame, res, (got_w, got_h)


def eye_box(res, W, H, pad=0.45):
    pts = res.face_landmarks[0]
    xo, yo = pts[R_OUT].x * W, pts[R_OUT].y * H
    xi, yi = pts[R_IN].x * W, pts[R_IN].y * H
    cx, cy = (xo + xi) / 2, (yo + yi) / 2
    wpx = abs(xi - xo)
    half_w = wpx * (1 + pad) / 2
    half_h = half_w * 0.62
    return (int(cx - half_w), int(cy - half_h), int(cx + half_w), int(cy + half_h)), wpx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="author")
    ap.add_argument("--camera", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    print(__doc__.split("It captures")[0])
    input("This will save photographs of you to disk. Press Enter to consent and continue, "
          "or Ctrl+C to stop. ")

    import mediapipe as mp
    lm = mp.tasks.vision.FaceLandmarker.create_from_options(
        mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=os.path.join(HERE, "face_landmarker.task")),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True, num_faces=1))
    cap = cv2.VideoCapture(a.camera, cv2.CAP_DSHOW if os.name == "nt" else 0)
    if not cap.isOpened():
        raise SystemExit("no camera")

    print("\nLIGHTING: face the light. A window or lamp BEHIND you puts your eyes in")
    print("shadow and the iris loses contrast, which is what this figure needs to show.")
    print("Turn the screen brightness up too - it lights your face.\n")
    input("Press Enter when the light is in front of you. ")
    print("Look at the centre of the screen and hold still ...")
    out, crops = {}, {}
    for w, h, tag in ((1280, 720, "720"), (640, 480, "480")):
        frame, res, got = grab(cap, lm, w, h)
        if not res.face_landmarks:
            raise SystemExit(f"no face found at {w}x{h} - check the lighting")
        H, W = frame.shape[:2]
        (x0, y0, x1, y1), wpx = eye_box(res, W, H)
        crop = frame[max(0, y0):min(H, y1), max(0, x0):min(W, x1)]
        if crop.size == 0 or wpx < 4:
            raise SystemExit(f"eye crop empty at {w}x{h} (width {wpx:.1f} px) - "
                             "move closer, improve the lighting, and try again")
        crops[tag] = crop.copy()
        out[tag] = {"requested": [w, h], "granted": list(got), "eye_width_px": round(float(wpx), 1)}
        print(f"  {got[0]}x{got[1]}: right-eye width {wpx:.1f} px")
        if tag == "720":
            ann = frame.copy()
            for i in (R_OUT, R_IN):
                p = res.face_landmarks[0][i]
                cv2.circle(ann, (int(p.x * W), int(p.y * H)), 3, (40, 120, 214), -1)
            cv2.rectangle(ann, (x0, y0), (x1, y1), (40, 120, 214), 2)
            cv2.imwrite(os.path.join(OUT, f"fig_raw_{a.name}_frame720.png"), ann)
            # a face-only crop: the full frame shows the room, which the figure does not need
            xs = [q.x * W for q in res.face_landmarks[0]]
            ys = [q.y * H for q in res.face_landmarks[0]]
            fx0, fx1 = int(min(xs)), int(max(xs))
            fy0, fy1 = int(min(ys)), int(max(ys))
            mx, my = int(0.28 * (fx1 - fx0)), int(0.34 * (fy1 - fy0))
            face = ann[max(0, fy0 - my):min(H, fy1 + my), max(0, fx0 - mx):min(W, fx1 + mx)]
            if face.size:
                cv2.imwrite(os.path.join(OUT, f"fig_raw_{a.name}_face720.png"), face)
    cap.release()

    # ---- one identical tone mapping for BOTH crops, derived from the 720p crop -------
    # A figure comparing detail must not compare two different contrast stretches. The
    # percentiles come from the 720p crop and are applied unchanged to both, and the
    # parameters are recorded below so the caption can disclose them.
    ref = crops["720"]
    lo_p = float(np.percentile(ref, 1.0))
    hi_p = float(np.percentile(ref, 99.0))
    span = max(1.0, hi_p - lo_p)

    def stretch(img):
        out_ = (img.astype(np.float32) - lo_p) * (255.0 / span)
        return np.clip(out_, 0, 255).astype(np.uint8)

    out["tone_mapping"] = {"note": "identical linear stretch applied to both crops",
                           "black_point": round(lo_p, 1), "white_point": round(hi_p, 1)}

    disp_w = 420
    for tag, img in crops.items():
        cv2.imwrite(os.path.join(OUT, f"fig_raw_{a.name}_eye{tag}_true.png"), img)
        adj = stretch(img)
        sh, sw = adj.shape[:2]
        scale = disp_w / sw
        big = cv2.resize(adj, (disp_w, int(sh * scale)), interpolation=cv2.INTER_NEAREST)
        # draw the source-pixel grid so the reader can count what the landmarker had
        grid = big.copy()
        for gx in range(sw + 1):
            x = int(round(gx * scale))
            cv2.line(grid, (x, 0), (x, grid.shape[0]), (255, 255, 255), 1)
        for gy in range(sh + 1):
            y = int(round(gy * scale))
            cv2.line(grid, (0, y), (grid.shape[1], y), (255, 255, 255), 1)
        big = cv2.addWeighted(big, 0.82, grid, 0.18, 0)
        cv2.imwrite(os.path.join(OUT, f"fig_raw_{a.name}_eye{tag}.png"), big)
        print(f"  {tag}: crop {sw}x{sh} source pixels")
    json.dump(out, open(os.path.join(OUT, f"fig_raw_{a.name}_measures.json"), "w"), indent=1)
    print(f"\nwrote 5 images + measures to {os.path.abspath(OUT)}")
    print("Review them before sending. Delete any you are not happy to publish.")


if __name__ == "__main__":
    main()
