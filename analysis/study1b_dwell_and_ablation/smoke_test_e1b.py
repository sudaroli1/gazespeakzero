"""Smoke test for E1b without the dataset or the MediaPipe model.

Builds a fake EOTT tree (12 participants, VP8 webm videos whose pixel colour
encodes the true gaze, Tobii JSON-lines log, browser log), replaces the
FaceLandmarker with a fake that reads the colour, runs extraction and analysis,
and checks the outputs."""
import json, os, sys, tempfile, types, subprocess
import numpy as np, av, pandas as pd
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "study1_zone_classification"))
rng = np.random.default_rng(0)
root = tempfile.mkdtemp()
data = os.path.join(root, "EOTT")
FPS, SECS = 30, 24
NOISE_SHARED, NOISE_FRAME = 0.03, 0.08      # per-dwell shared offset, per-frame jitter

def gaze_path(t_s, seed):
    r = np.random.default_rng(seed)
    targets = r.uniform(0.05, 0.95, size=(int(SECS / 1.5) + 2, 2))
    k = (t_s // 1.5).astype(int)
    return targets[k]

chars = [["participant", "a", "b", "setup", "w", "h"]]
for p in range(1, 13):
    pid = f"P_{p}"
    pdir = os.path.join(data, pid); os.makedirs(pdir)
    chars.append([pid, "", "", "Laptop" if p % 2 else "PC", "1440", "900"])
    start = 1500000000000 + p * 10_000_000
    open(os.path.join(pdir, f"{start}_1_-study-dot_test_instructions.webm"), "wb").close()
    log, tob = [{"windowX": 0, "windowY": 0, "windowInnerWidth": 1, "windowInnerHeight": 1,
                 "windowOuterWidth": 1, "windowOuterHeight": 1}], []
    for vi, task in enumerate(["dot_test", "fitts_law"]):
        sess = f"{start}_{vi+2}_/study/{task}"
        fn = sess.replace("/", "-") + ".webm"
        v_epoch = start + vi * 100_000
        # laptops (odd p) log their recording start 300 ms early -> frames look 300 ms "early" vs Tobii
        log.append({"type": "recording start", "sessionString": sess, "epoch": v_epoch - (300 if p % 2 else 0)})
        seed = p * 10 + vi
        with av.open(os.path.join(pdir, fn), "w") as c:
            s = c.add_stream("libvpx", rate=FPS); s.width, s.height, s.pix_fmt = 64, 48, "yuv420p"
            n = FPS * SECS
            stall = (p == 3 and vi == 1)
            tt = np.arange(n) / FPS + np.where(stall & (np.arange(n) >= 300), 2.0, 0.0)   # 2 s camera stall
            g = gaze_path(tt, seed)
            dwell_off = rng.normal(0, NOISE_SHARED, size=(len(g), 2))
            for i in range(n):
                k = int(tt[i] // 1.5)
                obs = np.clip(g[i] + np.random.default_rng(seed * 1000 + k).normal(0, NOISE_SHARED, 2)
                              + rng.normal(0, NOISE_FRAME, 2), 0, 1)
                img = np.zeros((48, 64, 3), np.uint8)
                img[..., 0] = int(obs[0] * 255); img[..., 1] = int(obs[1] * 255); img[..., 2] = 128
                fr = av.VideoFrame.from_ndarray(img, format="rgb24")
                fr.pts = int(round(tt[i] * 1000)); fr.time_base = Fraction(1, 1000)
                for pkt in s.encode(fr): c.mux(pkt)
            for pkt in s.encode(): c.mux(pkt)
        # Tobii at 120 Hz over the video span, gaze = true path
        ts = np.arange(0, SECS + 2.5, 1 / 120)
        gt = gaze_path(ts, seed)
        for t_s, (x, y) in zip(ts, gt):
            valid = int(rng.random() > 0.03)
            tob.append({"true_time": (v_epoch + t_s * 1000) / 1000.0,
                        "right_gaze_point_on_display_area": [x + rng.normal(0, .003), y],
                        "left_gaze_point_on_display_area": [x, y + rng.normal(0, .003)],
                        "right_pupil_validity": valid, "left_pupil_validity": valid})
    json.dump(log, open(os.path.join(pdir, f"{start}.json"), "w"))
    with open(os.path.join(pdir, f"{pid}.txt"), "w") as f:
        for d in tob: f.write(json.dumps(d) + "\n")
import csv
with open(os.path.join(root, "chars.csv"), "w", newline="") as f: csv.writer(f).writerows(chars)

# ---- fake MediaPipe: colour -> iris offset
import extract_features as ef
from mediapipe.tasks.python import vision
class FakeLM:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def detect_for_video(self, image, ts):
        a = image.numpy_view().astype(float)
        gx, gy = a[..., 0].mean() / 255, a[..., 1].mean() / 255
        P = np.tile([0.5, 0.5], (478, 1)).astype(float)
        P[33] = [0.40, 0.40]; P[133] = [0.46, 0.40]; P[159] = [0.43, 0.39]; P[145] = [0.43, 0.41]
        P[362] = [0.54, 0.40]; P[263] = [0.60, 0.40]; P[386] = [0.57, 0.39]; P[374] = [0.57, 0.41]
        off = np.array([(0.5 - gx) * 0.02, (gy - 0.5) * 0.01])
        P[468:473] = np.array([0.43, 0.40]) + off; P[473:478] = np.array([0.57, 0.40]) + off
        lms = [types.SimpleNamespace(x=x, y=y, z=0.0) for x, y in P]
        bs = [types.SimpleNamespace(category_name=k, score=0.5) for k in ef.EYE_BLENDSHAPES]
        M = np.eye(4); M[:3, 3] = [0, 0, -50]
        return types.SimpleNamespace(face_landmarks=[lms], face_blendshapes=[bs], facial_transformation_matrixes=[M])
vision.FaceLandmarker.create_from_options = staticmethod(lambda opts: FakeLM())

import eott_extract as ee
out = os.path.join(root, "feat")
sys.argv = ["x", "--data", data, "--chars", os.path.join(root, "chars.csv"), "--model", "none", "--out", out]
ee.main()
# dry-run path too
sys.argv = ["x", "--data", data, "--chars", os.path.join(root, "chars.csv"), "--model", "none",
            "--out", os.path.join(root, "dry"), "--participants", "P_1", "--max-seconds", "5"]
ee.main()
# --zip mode must give exactly the same features as --data
import zipfile
zp = os.path.join(root, "eott.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
    for dp, _, fs in os.walk(data):
        for fn_ in fs:
            full = os.path.join(dp, fn_)
            z.write(full, os.path.join("Release", os.path.relpath(full, data)))
    z.writestr("__MACOSX/Release/P_1/._junk.json", "x")
sys.argv = ["x", "--zip", zp, "--chars", os.path.join(root, "chars.csv"), "--model", "none",
            "--out", os.path.join(root, "featzip"), "--participants", "P_1", "P_2", "--tmp", os.path.join(root, "tmp1")]
ee.main()
for pid in ("P_1", "P_2"):
    A = pd.read_csv(os.path.join(out, f"{pid}_frames.csv")); B = pd.read_csv(os.path.join(root, "featzip", f"{pid}_frames.csv"))
    pd.testing.assert_frame_equal(A.drop(columns=[]), B)
assert not os.path.exists(os.path.join(root, "tmp1")), "scratch folder must be removed"
print("zip mode identical to folder mode")
dry = pd.read_csv(os.path.join(root, "dry", "P_1_frames.dry.csv"))
assert dry.t_rel_ms.max() <= 5500, dry.t_rel_ms.max()
f1 = pd.read_csv(os.path.join(out, "P_1_frames.csv"))
print(f1[["task", "frame", "pts_raw_ms", "t_rel_ms", "epoch_ms", "tobii_x", "tobii_dt_ms"]].head(4).to_string())
assert f1.tobii_x.notna().mean() > 0.8, f1.tobii_x.notna().mean()
assert len(f1) == 2 * FPS * SECS, len(f1)
f3 = pd.read_csv(os.path.join(out, "P_3_frames.csv")); f3 = f3[f3.task == "fitts_law"]
true_ms = (np.arange(len(f3)) / FPS + np.where(np.arange(len(f3)) >= 300, 2.0, 0)) * 1000
got_ms = f3.t_rel_ms.values - f3.t_rel_ms.values[0]
print("stall timing max error ms:", np.abs(got_ms - true_ms).max())
assert np.abs(got_ms - true_ms).max() < 40, "frame times must follow a camera stall"

r = subprocess.run([sys.executable, os.path.join(HERE, "eott_analyze.py"), "--features", out,
                    "--out", os.path.join(root, "res")], capture_output=True, text=True)
print(r.stdout[-4000:]); print(r.stderr[-3000:])
assert r.returncode == 0
acc = pd.read_csv(os.path.join(root, "res", "e1b_dwell_accuracy.csv"))
sh = pd.read_csv(os.path.join(root, "res", "e1b_shared_error.csv"))
acc = acc[acc.disp_std == 0.03]; sh = sh[sh.disp_std == 0.03]
g = lambda L, grid, m: float(acc[(acc.dwell_ms == L) & (acc.grid == grid) & (acc.method == m)].acc.iloc[0])
lag = pd.read_csv(os.path.join(root, "res", "e1b_lag_check.csv"))
assert lag.best_lag_ms.abs().median() <= 100, lag
cl = pd.read_csv(os.path.join(root, "res", "e1b_clock_lags.csv"))
print(cl.to_string())
med = cl.groupby("setup").lag_ms.median()
assert abs(med["Laptop"] - 300) <= 20 and abs(med["PC"]) <= 20, med
assert (cl[cl.setup == "Laptop"].lag_ms - 300).abs().max() <= 40, "per-participant lags should be close too"
assert g(1000, "3x3", "mean") > g(1000, "3x3", "single") + 0.05, "averaging should help with independent jitter"
assert (sh.shared_frac_icc < 0.6).all(), sh
print("ALL E1b SMOKE ASSERTIONS PASSED")
