import nbformat as nbf, os
H = os.path.dirname(os.path.abspath(__file__))
src = lambda p: open(os.path.join(H, p)).read()
nb = nbf.v4.new_notebook(); C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s)); code = lambda s: C.append(nbf.v4.new_code_cell(s))
md("""# GazeSpeakZero — E1b re-analysis (v3: webcam–Tobii clock correction), about 40–70 min

This notebook only re-runs the **analysis** on the features the first run already saved to Google Drive (`MyDrive/gazespeakzero/E1b/features`). It needs no download and no video processing. Run the cells one at a time with Shift + Enter.""")
code("""from google.colab import drive
drive.mount('/content/drive')
WORK = '/content/drive/MyDrive/gazespeakzero/E1b'
import os, glob
print(len(glob.glob(f'{WORK}/features/P_*_frames.csv')), 'participant feature files found (expect 51)')""")
code("!mkdir -p /content/e1 /content/e1b")
code("%%writefile /content/e1/analyze.py\n" + src("../study1_zone_classification/analyze.py"))
code("%%writefile /content/e1b/eott_analyze.py\n" + src("eott_analyze.py"))
md("### Main analysis: one clock correction per setup (Laptop, PC). About 25–35 min.")
code("""!cd /content/e1b && python eott_analyze.py --sync setup --features "{WORK}/features" --out "{WORK}/results_v3/setup\"""")
code("""from IPython.display import Markdown, display
display(Markdown(open(f'{WORK}/results_v3/setup/E1b_REPORT.md').read()))""")
md("### Sensitivity check: each person's own clock correction. About 25–35 min.")
code("""!cd /content/e1b && python eott_analyze.py --sync participant --features "{WORK}/features" --out "{WORK}/results_v3/participant\"""")
code("""import shutil
shutil.make_archive('/content/E1b_results_v3', 'zip', f'{WORK}/results_v3')
from google.colab import files; files.download('/content/E1b_results_v3.zip')""")
nb["cells"] = C
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "colab": {"provenance": []}}
nbf.write(nb, os.path.join(H, "E1b_reanalyze_colab.ipynb")); print("built")
