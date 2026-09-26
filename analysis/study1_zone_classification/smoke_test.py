"""Smoke test without the MediaPipe model: fake dataset + mocked landmarker."""
import os, sys, shutil, types, tempfile
import numpy as np, pandas as pd, cv2
from scipy.io import savemat

sys.path.insert(0, os.path.dirname(__file__))
import extract_features as ef

rng = np.random.default_rng(1)
root = tempfile.mkdtemp()
data = os.path.join(root, "MPIIFaceGaze")
N = 60
for s in range(4):
    sid = f"p{s:02d}"
    sd = os.path.join(data, sid)
    os.makedirs(os.path.join(sd, "day01")); os.makedirs(os.path.join(sd, "day02"))
    os.makedirs(os.path.join(sd, "Calibration"))
    savemat(os.path.join(sd, "Calibration", "screenSize.mat"),
            {"width_pixel": 1280, "height_pixel": 800, "width_mm": 330, "height_mm": 207})
    with open(os.path.join(sd, f"{sid}.txt"), "w") as f:
        for i in range(N):
            fn = f"day{1 + i // 30:02d}/{i:04d}.jpg"
            cv2.imwrite(os.path.join(sd, fn), np.full((72, 128, 3), 128, np.uint8))
            gx, gy = rng.uniform(0, 1280), rng.uniform(0, 800)
            vals = [fn, f"{gx:.0f}", f"{gy:.0f}"] + ["500"] * 12 + ["0.1"] * 12 + ["left"]
            f.write(" ".join(vals) + "\n")


class FakeLM:
    """Returns 478 landmarks whose iris offset encodes the gaze target."""
    def __init__(self):
        self.gaze = None
    def detect(self, image):
        if rng.random() < 0.05:
            return types.SimpleNamespace(face_landmarks=[], face_blendshapes=[],
                                         facial_transformation_matrixes=[])
        gx, gy = self.gaze
        P = np.tile([0.5, 0.5], (478, 1)).astype(float)
        P[33] = [0.40, 0.40]; P[133] = [0.46, 0.40]; P[159] = [0.43, 0.39]; P[145] = [0.43, 0.41]
        P[362] = [0.54, 0.40]; P[263] = [0.60, 0.40]; P[386] = [0.57, 0.39]; P[374] = [0.57, 0.41]
        P[1] = [0.5, 0.5]
        off = np.array([(0.5 - gx) * 0.02, (gy - 0.5) * 0.01]) + rng.normal(0, 0.002, 2)
        P[468:473] = np.array([0.43, 0.40]) + off
        P[473:478] = np.array([0.57, 0.40]) + off
        lms = [types.SimpleNamespace(x=x, y=y, z=0.0) for x, y in P]
        bs = [types.SimpleNamespace(category_name=k, score=float(rng.random())) for k in ef.EYE_BLENDSHAPES]
        M = np.eye(4); M[:3, 3] = [0, 0, -50]
        return types.SimpleNamespace(face_landmarks=[lms], face_blendshapes=[bs],
                                     facial_transformation_matrixes=[M])


# run the extraction loop with the fake landmarker
out = os.path.join(root, "features")
os.makedirs(out)
fake = FakeLM()
for s in range(4):
    sd = os.path.join(data, f"p{s:02d}")
    ann = ef.read_annotations(sd)
    scr = ef.read_screen(sd)
    recs = []
    for row in ann.itertuples(index=False):
        fake.gaze = (row.gt_px_x / 1280, row.gt_px_y / 800)
        recs.append(ef.process_image(fake, os.path.join(sd, row.file)))
    df = pd.concat([ann, pd.DataFrame(recs)], axis=1)
    for k, v in scr.items():
        df[k] = v
    df.to_csv(os.path.join(out, f"p{s:02d}.csv"), index=False)
print(pd.read_csv(os.path.join(out, "p00.csv")).iloc[0].to_string()[:1500])

os.system(f"cd {os.path.dirname(os.path.abspath(__file__))} && "
          f"{sys.executable} analyze.py --features {out} --out {root}/results > {root}/log.txt 2>&1; echo exit $?")
print(open(f"{root}/log.txt").read()[-6000:])
print(os.listdir(f"{root}/results"))

acc = pd.read_csv(f"{root}/results/e1_zone_accuracy.csv")
get = lambda g, m: float(acc[(acc.grid == g) & (acc.method == m)].acc_mean_subj.iloc[0])
assert get("1x3", "M2 hgb") > get("1x3", "chance (1/K)") + 0.2, "M2 should beat chance on synthetic data"
assert get("3x3", "M0 original") <= 0.2
assert "M0 generalised" in set(acc[acc.grid == "2x2"].method)
cal = pd.read_csv(f"{root}/results/e1_calibration.csv")
assert set(cal.scheme) == {"random", "first session"}
qa = __import__("json").load(open(f"{root}/results/e1_qa.json"))
assert abs(qa["median_R_scale"] - 1) < 1e-6
print("ALL SMOKE ASSERTIONS PASSED")
