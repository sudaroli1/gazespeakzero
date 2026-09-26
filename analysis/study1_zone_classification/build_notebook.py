import nbformat as nbf
ex = open("extract_features.py").read(); an = open("analyze.py").read()
nb = nbf.v4.new_notebook(); C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s)); code = lambda s: C.append(nbf.v4.new_code_cell(s))
md("""# GazeSpeakZero — E1: calibration-free gaze-zone accuracy (MPIIFaceGaze)

Run top to bottom on Colab (**Runtime → Run all**). A GPU isn't needed; the standard CPU runtime is enough.

Time: about 5 min setup + 20–40 min extraction + ~5 min analysis. Features and results are saved to your Google Drive, so if Colab disconnects, run all again and it resumes where it stopped.

Dataset: MPIIFaceGaze (Zhang et al., CVPR-W 2017 / TPAMI 2019), CC BY-NC-SA 4.0, research use only. Cite it in the paper.""")
code("""from google.colab import drive
drive.mount('/content/drive')
WORK = '/content/drive/MyDrive/gazespeakzero/E1'
import os; os.makedirs(WORK, exist_ok=True); print(WORK)""")
code("""!pip -q install "mediapipe>=0.10.14" opencv-python-headless scikit-learn pandas scipy matplotlib
import mediapipe as mp; print('mediapipe', mp.__version__)""")
code("""%%bash
cd /content
if [ ! -d MPIIFaceGaze ]; then
  wget -q --show-progress -O MPIIFaceGaze.zip https://collaborative-ai.org/files/datasets/MPIIFaceGaze.zip
  unzip -q MPIIFaceGaze.zip && rm MPIIFaceGaze.zip
fi
[ -f face_landmarker.task ] || wget -q -O face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
ls MPIIFaceGaze | head -20; ls MPIIFaceGaze/p00 | head; head -2 MPIIFaceGaze/p00/p00.txt; ls -la face_landmarker.task""")
code("%%writefile /content/extract_features.py\n" + ex)
code("%%writefile /content/analyze.py\n" + an)
md("## 1. Dry run on 40 images of p00\nEvery line must start with **OK** or **INFO**. If any line says **FAIL**, stop and read the output of this cell before going on.")
code("""!cd /content && python extract_features.py --data MPIIFaceGaze --model face_landmarker.task --out dryrun --subjects p00 --max-per-subject 40
import pandas as pd, numpy as np
d = pd.read_csv('/content/dryrun/p00.dry.csv')
det = d[d.detected==1]
io = det.interocular_norm*det.img_w
corner = np.stack([det[[f'{k}_x',f'{k}_y']].values for k in ('mp_rout','mp_rin','mp_lout','mp_lin')],1)
ann = np.stack([det[[f'ann_lm{i}_x',f'ann_lm{i}_y']].values for i in range(4)],1)
err = (np.linalg.norm(ann[:,:,None]-corner[:,None],axis=-1).min(2).mean(1)/io)
checks = {
 'image size': f"{int(d.img_w.iloc[0])}x{int(d.img_h.iloc[0])}",
 'screen': f"{d.screen_w_px.iloc[0]:.0f}x{d.screen_h_px.iloc[0]:.0f} px, {d.screen_w_mm.iloc[0]:.0f}x{d.screen_h_mm.iloc[0]:.0f} mm",
 'median ms per frame': f"{d.landmark_ms.median():.1f}",
 'median eye-corner error (x interocular)': f"{np.median(err):.3f}",
 'all images readable': d.read_error.sum() == 0,
 'face detected in >= 90% of frames': d.detected.mean() >= 0.9,
 '478 landmarks': (det.n_landmarks==478).all(),
 'blendshapes present': det.filter(like='bs_').notna().all().all(),
 'head pose present, rotation unscaled': det['yaw'].notna().all(),
 'MediaPipe eye corners match the dataset annotation (median < 0.15)': np.median(err) < 0.15,
 'iris lies between the eye corners (median reye_h in 0.2-0.8)': 0.2 < det.reye_h.median() < 0.8,
 'gaze targets inside the screen': ((d.gt_px_x>=0)&(d.gt_px_x<d.screen_w_px)&(d.gt_px_y>=0)&(d.gt_px_y<d.screen_h_px)).all(),
}
for k,v in checks.items():
    if isinstance(v,str): print('INFO ', k, ':', v)
    else: print(('OK   ' if bool(v) else 'FAIL ') + k)
print('R_scale median', round(float(det.R_scale.median()),4))""")
md("## 2. Full extraction, all 15 subjects (resumable; features go to Drive)")
code("""!cd /content && python extract_features.py --data MPIIFaceGaze --model face_landmarker.task --out "{WORK}/features\"""")
md("## 3. Analysis")
code("""!cd /content && python analyze.py --features "{WORK}/features" --out "{WORK}/results\"""")
code("""from IPython.display import Markdown, Image, display
display(Markdown(open(f'{WORK}/results/E1_REPORT.md').read()))
for g in ('1x3','2x2','3x3'):
    for m in ('M0','M2_hgb'):
        display(Image(f'{WORK}/results/confusion_{m}_{g}.png', width=420))""")
md("## 4. Download the results\nDownload `E1_results.zip`. Its contents belong in this study's `results/` folder.")
code("""import shutil
shutil.make_archive('/content/E1_results', 'zip', WORK)
from google.colab import files; files.download('/content/E1_results.zip')""")
nb["cells"] = C
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "colab": {"provenance": []}}
nbf.write(nb, "E1_gaze_zone_colab.ipynb")
print("built", len(C), "cells")
