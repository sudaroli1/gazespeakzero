import nbformat as nbf, os
H = os.path.dirname(os.path.abspath(__file__))
src = lambda p: open(os.path.join(H, p)).read()
nb = nbf.v4.new_notebook(); C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s)); code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("""# GazeSpeakZero — E1b: does a 0.5–1 s dwell remove webcam gaze jitter?

Data: **Eye of the Typer (EOTT)**, Papoutsaki et al., ETRA 2018, Brown HCI group. 51 people, laptop and desktop webcams, with a Tobii Pro X3-120 eye tracker recording where they really looked. It is a free direct download under GPLv3, with no registration.

Run the cells **one at a time** (Shift + Enter), not Run all. CPU is enough. The download cell prints progress every 20 seconds. **Check the dry-run output before letting the long extraction run.** Everything is saved to Google Drive, so if Colab disconnects, run all again and it resumes.""")
code("""from google.colab import drive
drive.mount('/content/drive')
WORK = '/content/drive/MyDrive/gazespeakzero/E1b'
import os; os.makedirs(WORK, exist_ok=True); print(WORK)
!df -h /content | tail -1""")
code("""!pip -q install "mediapipe>=0.10.14" av scikit-learn pandas scipy
import mediapipe as mp, av; print('mediapipe', mp.__version__, '| av', av.__version__)""")
md("## 1. Download EOTT (resumable). The zip is never fully unpacked.")
code("""# Download with visible progress, time-outs and resume (safe to re-run)
import os, time, shutil, requests
URL = 'https://webgazer.cs.brown.edu/data/WebGazerETRA2018Dataset_Release20180420.zip'
OUT = '/content/eott.zip'
print('contacting server ...', flush=True)
h = requests.head(URL, timeout=30, allow_redirects=True)
size = int(h.headers.get('content-length', 0))
free = shutil.disk_usage('/content').free
print(f'server status {h.status_code} | file size {size/1e9:.1f} GB | free disk {free/1e9:.1f} GB', flush=True)
assert h.status_code == 200, 'server did not answer normally - stop and note the status code'
assert size == 0 or size < free - 5e9, 'NOT ENOUGH DISK - stop; note both numbers'
have = os.path.getsize(OUT) if os.path.exists(OUT) else 0
if size and have >= size:
    print('already downloaded')
else:
    hdr = {'Range': f'bytes={have}-'} if have else {}
    t0, last, got = time.time(), 0, have
    with requests.get(URL, headers=hdr, stream=True, timeout=(30, 120)) as r, open(OUT, 'ab' if have else 'wb') as f:
        r.raise_for_status()
        for chunk in r.iter_content(8 * 1024 * 1024):
            f.write(chunk); got += len(chunk)
            if time.time() - last > 20:
                last = time.time(); rate = (got - have) / max(last - t0, 1)
                eta = (size - got) / rate / 60 if size and rate else float('nan')
                print(f'{got/1e9:6.2f} / {size/1e9:.2f} GB   {rate/1e6:5.1f} MB/s   about {eta:4.0f} min left', flush=True)
print('done:', os.path.getsize(OUT) / 1e9, 'GB')""")
md("## 1b. Look inside the zip (no unpacking; nothing is written to disk)")
code("""# Free the disk from any earlier attempt that unpacked the whole dataset
!rm -rf /content/eott
import zipfile, shutil, re, collections
zf = zipfile.ZipFile('/content/eott.zip')
names = [i for i in zf.infolist() if not i.is_dir()]
parts = collections.Counter(next((q for q in i.filename.split('/')[:-1] if re.fullmatch(r'P_\\d+', q)), None) for i in names)
parts.pop(None, None)
need = [i for i in names if re.search(r'-study-(dot_test|dot_test_final|fitts_law)\\.webm$', i.filename)]
print('files in zip:', len(names), '| participants:', len(parts))
print('task videos E1b uses:', len(need), '|', round(sum(i.file_size for i in need)/1e9, 2), 'GB in total')
per = collections.Counter()
for i in need:
    per[next(q for q in i.filename.split('/')[:-1] if re.fullmatch(r'P_\\d+', q))] += i.file_size
print('largest participant to unpack at one time:', round(max(per.values())/1e6), 'MB')
print('free disk now:', round(shutil.disk_usage('/content').free/1e9, 1), 'GB')
zf.close()
!wget -q -O /content/participant_characteristics.csv https://raw.githubusercontent.com/brownhci/WebGazer/master/www/data/src/participant_characteristics.csv
!echo "characteristics rows: $(grep -c '^P_' /content/participant_characteristics.csv)"
""")
code("""!mkdir -p /content/e1 /content/e1b
![ -f /content/face_landmarker.task ] || wget -q -O /content/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task""")
code("%%writefile /content/e1/extract_features.py\n" + src("../study1_zone_classification/extract_features.py"))
code("%%writefile /content/e1/analyze.py\n" + src("../study1_zone_classification/analyze.py"))
code("%%writefile /content/e1b/eott_extract.py\n" + src("eott_extract.py"))
code("%%writefile /content/e1b/eott_analyze.py\n" + src("eott_analyze.py"))
md("## 2. Dry run: first 40 s of each task for one participant\nEvery line must start with **OK** or **INFO**. If any says **FAIL**, stop and read this cell's output before going on.")
code("""P1 = sorted(parts, key=lambda p: int(p.split('_')[1]))[0]; print('dry run on', P1)
!cd /content/e1b && python eott_extract.py --zip /content/eott.zip --chars /content/participant_characteristics.csv --model /content/face_landmarker.task --out /content/e1b_dry --participants $P1 --max-seconds 40
import pandas as pd, numpy as np
d = pd.read_csv(f'/content/e1b_dry/{P1}_frames.dry.csv')
lab = d.dropna(subset=['tobii_x'])
# timing check, per video: the iris feature should track Tobii x best at a lag near 0
tb = pd.read_csv(f'/content/e1b_dry/{P1}_tobii.dry.csv').dropna(subset=['tx']).sort_values('t_ms')
best = None
if 'reye_h' in d and d.reye_h.notna().sum() > 50:
    res = {}
    for v, dv in d.dropna(subset=['reye_h']).sort_values('epoch_ms').groupby('video'):
        tv = tb[tb.video == v]
        if len(tv) < 50 or len(dv) < 50: continue
        for lag in range(-1000, 1001, 33):
            j = np.interp(dv.epoch_ms.values + lag, tv.t_ms.values, tv.tx.values)
            res.setdefault(lag, []).append(np.corrcoef(dv.reye_h.values, j)[0, 1])
    if res:
        best = max(((lag, float(np.nanmean(r))) for lag, r in res.items()), key=lambda z: abs(z[1]))
checks = {
  'tasks found': ', '.join(sorted(d.task.unique())),
  'frames': str(len(d)),
  'frame size': f"{int(d.img_w.iloc[0])}x{int(d.img_h.iloc[0])}",
  'setup': d.setup.iloc[0],
  'best lag (ms) and correlation, iris vs Tobii x': str(best),
  'face detected in >= 85% of frames': d.detected.mean() >= 0.85,
  'Tobii label on >= 60% of frames': d.tobii_x.notna().mean() >= 0.60,
  'Tobii gaze inside the screen (median x, y in 0-1)': lab.tobii_x.between(0,1).mean() > 0.9 and lab.tobii_y.between(0,1).mean() > 0.9,
  'frame clock and Tobii clock agree within 0.5 s (best lag near 0)': best is not None and abs(best[0]) <= 500 and abs(best[1]) >= 0.10,
}
for k, v in checks.items():
    if isinstance(v, str): print('INFO ', k, ':', v)
    else: print(('OK   ' if bool(v) else 'FAIL ') + k)
print('face detected', round(d.detected.mean(), 3), '| Tobii-labelled', round(d.tobii_x.notna().mean(), 3))""")
md("## 3. Full extraction, all participants (long: roughly 1–3 h; resumable; saved to Drive). Participants are unpacked one at a time and deleted, so the disk never fills.")
code("""!cd /content/e1b && python eott_extract.py --zip /content/eott.zip --chars /content/participant_characteristics.csv --model /content/face_landmarker.task --out "{WORK}/features\"""")
md("## 4. Analysis (~10–20 min)")
code("""!cd /content/e1b && python eott_analyze.py --features "{WORK}/features" --out "{WORK}/results\"""")
code("""from IPython.display import Markdown, display
display(Markdown(open(f'{WORK}/results/E1b_REPORT.md').read()))""")
md("## 5. Download the results (small; the features stay on your Drive)")
code("""import shutil
shutil.make_archive('/content/E1b_results', 'zip', f'{WORK}/results')
from google.colab import files; files.download('/content/E1b_results.zip')""")
nb["cells"] = C
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "colab": {"provenance": []}}
nbf.write(nb, os.path.join(H, "E1b_dwell_colab.ipynb"))
print("built", len(C), "cells")
