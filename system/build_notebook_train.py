import os

import nbformat as nbf

H = os.path.dirname(os.path.abspath(__file__))
nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))     # noqa: E731
code = lambda s: C.append(nbf.v4.new_code_cell(s))       # noqa: E731

md("""# Export the gaze model for the prototype (about 10 minutes, CPU is fine)

This trains the E1b gaze model on **all 51 EOTT participants** and saves it as
`gaze_model.joblib`, which the prototype loads on your laptop. No GPU needed.

It uses the features already on your Drive from the E1b run
(`MyDrive/gazespeakzero/E1b/features`). Run the cells one at a time, then download the file
at the end and put it in the `prototype/` folder next to `gaze_ui.py`.""")
code("""from google.colab import drive
drive.mount('/content/drive')
import os, glob
FEAT = '/content/drive/MyDrive/gazespeakzero/E1b/features'
print('features folder:', FEAT, '| exists:', os.path.isdir(FEAT))
print('participant files:', len(glob.glob(f'{FEAT}/P_*_frames.csv')))""")
code("""!pip -q install scikit-learn joblib pandas
import pandas as pd, numpy as np, glob
frames = sorted(glob.glob(f'{FEAT}/P_*_frames.csv'))
F = pd.concat([pd.read_csv(f) for f in frames], ignore_index=True)
print(F.shape, '| detected:', round(float((F.detected == 1).mean()), 3))
print('participants:', F.participant.nunique())""")
md("""## Train and save

Two gradient-boosting models, one for the horizontal position and one for the vertical, on
frames with a face and a gaze label — the same setup as E1b, but trained on everybody instead
of held-out folds, because this model is for use, not for measurement.""")
code("""from sklearn.ensemble import HistGradientBoostingRegressor
import joblib, json, sys

# the exact feature list E1/E1b used (e1/analyze.py)
EYE = ['reye_h', 'reye_v', 'reye_vlid', 'reye_open', 'leye_h', 'leye_v', 'leye_vlid', 'leye_open']
BS = ['bs_eyeLookInLeft', 'bs_eyeLookInRight', 'bs_eyeLookOutLeft', 'bs_eyeLookOutRight',
      'bs_eyeLookUpLeft', 'bs_eyeLookUpRight', 'bs_eyeLookDownLeft', 'bs_eyeLookDownRight',
      'bs_eyeBlinkLeft', 'bs_eyeBlinkRight', 'bs_eyeSquintLeft', 'bs_eyeSquintRight']
HEAD = ['R00', 'R01', 'R02', 'R10', 'R11', 'R12', 'R20', 'R21', 'R22', 'tx', 'ty', 'tz',
        'yaw', 'pitch', 'roll', 'nose_x', 'nose_y', 'interocular_norm']
# is_laptop is derived at load time, exactly as E1b does it
if 'is_laptop' not in F.columns:
    if 'setup' in F.columns:
        F['is_laptop'] = (F['setup'].astype(str).str.lower() == 'laptop').astype(int)
    else:
        F['is_laptop'] = 1
        print('no setup column - assuming laptop webcams')
print('is_laptop share:', round(float(F.is_laptop.mean()), 3), '(EOTT is 27 laptop, 24 desktop)')

# E1c (24 Sep): eye features ALONE beat the full set on held-out participants -
# 0.825 vs 0.793, paired 95% CI [+0.003, +0.061] - and head pose alone gets 0.596.
# The exported model uses NO head features: more accurate, and the only version whose
# accuracy can be claimed for people who cannot move their heads.
FEATS = EYE + BS + ['is_laptop']
HEAD_FOR_REFERENCE = HEAD
missing = [c for c in FEATS if c not in F.columns]
assert not missing, f'missing feature columns: {missing}'
print(len(FEATS), 'features')

m = (F.detected == 1) & F.tobii_x.notna() & F.tobii_y.notna()
X = F.loc[m, FEATS].values
models = {}
for tgt in ('tobii_x', 'tobii_y'):
    r = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                      early_stopping=False, random_state=0)
    r.fit(X, F.loc[m, tgt].values)
    models[tgt] = r
    print(tgt, 'trained on', X.shape)

bundle = {'model_x': models['tobii_x'], 'model_y': models['tobii_y'], 'features': FEATS,
          'trained_on': 'EOTT, all participants', 'n_frames': int(m.sum()),
          'note': 'screen coordinates are normalised 0..1; zone = floor(x * zones)'}
joblib.dump(bundle, '/content/gaze_model.joblib')
print('saved /content/gaze_model.joblib')""")
md("""## Sanity check before you download it

Accuracy here is optimistic (these frames were in training) — it only confirms the file works.
The honest numbers are the leave-one-participant-out ones from E1b.""")
code("""import numpy as np
px = bundle['model_x'].predict(X[:5000]); py = bundle['model_y'].predict(X[:5000])
tx = F.loc[m, 'tobii_x'].values[:5000]
z_pred = np.clip((px * 3).astype(int), 0, 2); z_true = np.clip((tx * 3).astype(int), 0, 2)
print('in-sample 1x3 zone agreement:', round(float((z_pred == z_true).mean()), 3),
      '(expect ~0.95; E1b reports 0.84 on unseen people)')""")
code("""from google.colab import files
files.download('/content/gaze_model.joblib')""")
nb["cells"] = C
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "colab": {"provenance": []}}
nbf.write(nb, os.path.join(H, "Train_gaze_model_colab.ipynb"))
print("built", len(C), "cells")
