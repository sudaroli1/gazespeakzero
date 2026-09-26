import os

import nbformat as nbf

H = os.path.dirname(os.path.abspath(__file__))
src = lambda p: open(os.path.join(H, p)).read()          # noqa: E731
nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))     # noqa: E731
code = lambda s: C.append(nbf.v4.new_code_cell(s))       # noqa: E731

md("""# GazeSpeakZero — E3b: give the language models a fair chance (about 40 minutes)

**Before you start: Runtime → Change runtime type → T4 GPU → Save.**

In E3 the language models lost to a plain lookup table. Two of the reasons may be ours, not theirs, so this notebook adds the two standard ways of using a small model for this job, on the same 240 cases:

- **`lm_pmi_*`** — the same likelihood ranking, but each candidate message's score is corrected by how much the model likes that sentence anyway (PMI calibration, Holtzman et al. 2021). Without the correction, ranking rewards fluent sentences rather than fitting ones.
- **`lm_choice_*`** — the model is shown all 60 candidate messages and asked which three the person meant. This is how a device would really use it.

Everything is added to the results already on Drive; nothing that ran before is re-run.""")
code("""from google.colab import drive
drive.mount('/content/drive')
WORK = '/content/drive/MyDrive/gazespeakzero/E3'
import os, torch
for p in ['cases.jsonl', 'outputs/outputs.jsonl']:
    print(p, 'OK' if os.path.exists(f'{WORK}/{p}') else 'MISSING - stop here')
print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE - switch the runtime to T4 GPU')""")
code("""!pip -q install "transformers>=4.51,<5" "sentence-transformers>=3.0" "accelerate>=0.30" pandas tabulate
import transformers, sentence_transformers
print('transformers', transformers.__version__, '| sentence-transformers', sentence_transformers.__version__)""")
code("!mkdir -p /content/e3 /content/e2")
code("%%writefile /content/e2/aac_vocab.py\n" + open(os.path.join(H, "..", "study2_scene_vocabulary", "aac_vocab.py")).read())
code("%%writefile /content/e3/build_intent_bank.py\n" + src("build_intent_bank.py"))
code("%%writefile /content/e3/e3_run.py\n" + src("e3_run.py"))
code("%%writefile /content/e3/e3_score.py\n" + src("e3_score.py"))
code("%cd /content/e3\n!python build_intent_bank.py")
md("## 1. Dry run: both new methods, smallest model, 8 cases (about 3 minutes)\nThe `choice` lines must show numbers, for example `'1, 2, 14' -> ['I01', 'I02', 'I14']`. **If every answer has no usable number, stop and read this output before going on.**")
code("""!cd /content/e3 && python e3_run.py --bank intent_bank.json --cases "{WORK}/cases.jsonl" --out /content/e3b_dry --limit 8 --methods lm_pmi_qwen1.5b lm_choice_qwen1.5b""")
md("## 2. All four models, both methods (about 40 minutes; resumable)")
code("""!cd /content/e3 && python e3_run.py --bank intent_bank.json --cases "{WORK}/cases.jsonl" --out "{WORK}/outputs" --methods lm_pmi_qwen1.5b lm_choice_qwen1.5b lm_pmi_smol1.7b lm_choice_smol1.7b lm_pmi_qwen3b lm_choice_qwen3b lm_pmi_phi3.5 lm_choice_phi3.5""")
md("## 3. Score everything again (1 minute)\nThe first line should list every method with 240 cases.")
code("""!cd /content/e3 && python e3_score.py --bank intent_bank.json --cases "{WORK}/cases.jsonl" --outputs "{WORK}/outputs/outputs.jsonl" --out "{WORK}/results_v2\"""")
code("""from IPython.display import Markdown, display
display(Markdown(open(f'{WORK}/results_v2/E3_REPORT.md').read()))""")
md("## 4. Download\nDownload `E3b_results.zip`.")
code("""import shutil, os
shutil.rmtree('/content/E3b_results', ignore_errors=True); os.makedirs('/content/E3b_results')
shutil.copytree(f'{WORK}/results_v2', '/content/E3b_results/results', dirs_exist_ok=True)
shutil.copy(f'{WORK}/outputs/outputs.jsonl', '/content/E3b_results/outputs.jsonl')
shutil.copy(f'{WORK}/cases.jsonl', '/content/E3b_results/cases.jsonl')
shutil.make_archive('/content/E3b_results', 'zip', '/content/E3b_results')
from google.colab import files; files.download('/content/E3b_results.zip')""")
nb["cells"] = C
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                  "colab": {"provenance": []}, "accelerator": "GPU"}
nbf.write(nb, os.path.join(H, "E3b_fair_lm_colab.ipynb"))
print("built", len(C), "cells")
