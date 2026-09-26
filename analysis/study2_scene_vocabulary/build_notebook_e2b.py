import nbformat as nbf, os
H = os.path.dirname(os.path.abspath(__file__))
src = lambda p: open(os.path.join(H, p)).read()
nb = nbf.v4.new_notebook(); C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s)); code = lambda s: C.append(nbf.v4.new_code_cell(s))
md("""# GazeSpeakZero — E2 add-on: a fair BLIP-2 baseline (about 20 minutes)

**Before you start: Runtime → Change runtime type → T4 GPU → Save.**

Why: in the main E2 run, the original paper's BLIP-2 step returned only the echoed question for every scene, so it fell back to "object, person, area". Reviewers would say we crippled BLIP-2. This notebook adds two properly used BLIP-2 variants (plain captioning, and the question format BLIP-2 was trained on). They are **added** to the existing results on Google Drive (`MyDrive/gazespeakzero/E2`); nothing already there is re-run. Then everything is re-scored.

Run the cells **one at a time** with Shift + Enter.""")
code("""from google.colab import drive
drive.mount('/content/drive')
WORK = '/content/drive/MyDrive/gazespeakzero/E2'
import os, torch
for p in ['set/set.jsonl', 'set/vocab.json', 'outputs/outputs.jsonl']:
    print(p, 'OK' if os.path.exists(f'{WORK}/{p}') else 'MISSING - stop here')
print('images:', len(os.listdir(f'{WORK}/set/images')))
print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE - switch the runtime to T4 GPU')""")
code("""!pip -q install "transformers==4.51.3" "huggingface_hub<1.0" "tokenizers<0.22" "accelerate>=0.30" pandas
import transformers; from transformers import Blip2ForConditionalGeneration
print('transformers', transformers.__version__, '- imports OK')""")
code("!mkdir -p /content/e2")
code("%%writefile /content/e2/aac_vocab.py\n" + src("aac_vocab.py"))
code("%%writefile /content/e2/e2_generate.py\n" + src("e2_generate.py"))
code("%%writefile /content/e2/e2_score.py\n" + src("e2_score.py"))
md("## 1. Dry run on 3 scenes (about 5 minutes, mostly the model download)\nEach variant should print **real object names** (for example `['kitchen', 'stove', 'sink']`), not an empty list. If both lists are empty, stop and read this output before going on.")
code("""!rm -rf /content/e2_dry && cd /content/e2 && python e2_generate.py --set "{WORK}/set" --out /content/e2_dry --limit 3 --methods blip2_caption blip2_qa""")
md("## 2. All scenes (about 10 minutes; resumable)")
code("""!cd /content/e2 && python e2_generate.py --set "{WORK}/set" --out "{WORK}/outputs" --methods blip2_caption blip2_qa""")
md("## 3. Re-score everything (1 minute)\nThe first line should say **scenes per method** with 283 for all six methods.")
code("""!cd /content/e2 && python e2_score.py --set "{WORK}/set" --outputs "{WORK}/outputs/outputs.jsonl" --out "{WORK}/results_v2\"""")
code("""from IPython.display import Markdown, display
display(Markdown(open(f'{WORK}/results_v2/E2_REPORT.md').read()))""")
md("## 4. Download\nDownload `E2_results_v2.zip`.")
code("""import shutil, os
shutil.rmtree('/content/E2_results_v2', ignore_errors=True); os.makedirs('/content/E2_results_v2')
shutil.copytree(f'{WORK}/results_v2', '/content/E2_results_v2/results', dirs_exist_ok=True)
shutil.copy(f'{WORK}/outputs/outputs.jsonl', '/content/E2_results_v2/outputs.jsonl')
shutil.copy(f'{WORK}/set/vocab.json', '/content/E2_results_v2/vocab.json')
shutil.make_archive('/content/E2_results_v2', 'zip', '/content/E2_results_v2')
from google.colab import files; files.download('/content/E2_results_v2.zip')""")
nb["cells"] = C
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "colab": {"provenance": []}, "accelerator": "GPU"}
nbf.write(nb, os.path.join(H, "E2b_blip2_fair_colab.ipynb")); print("built", len(C), "cells")
