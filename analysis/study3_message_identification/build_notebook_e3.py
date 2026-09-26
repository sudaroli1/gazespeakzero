import os

import nbformat as nbf

H = os.path.dirname(os.path.abspath(__file__))
src = lambda p: open(os.path.join(H, p)).read()          # noqa: E731
nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))     # noqa: E731
code = lambda s: C.append(nbf.v4.new_code_cell(s))       # noqa: E731

md("""# GazeSpeakZero — E3: from the objects a person picks to the sentence they mean

**Before you start: Runtime → Change runtime type → T4 GPU → Save.**

Run the cells **one at a time** with Shift + Enter. About 1.5 hours in total, most of it unattended. Everything is saved to Google Drive (`MyDrive/gazespeakzero/E3`), so if Colab disconnects, run the cells again and it carries on where it stopped.

What it does: 60 messages a person with severe motor impairment might want to say, each with the objects they would select. Every method has to recover the message from the objects, under four conditions: correct objects, only the first object, one object wrong because the scene model mislabelled it (drawn from E2's real errors), and one object wrong because of a gaze mis-selection.

Methods: a fixed template, a frequency rule, sentence-embedding retrieval, and four small open language models used two ways (ranking known messages, and writing the message themselves).""")
code("""from google.colab import drive
drive.mount('/content/drive')
WORK = '/content/drive/MyDrive/gazespeakzero/E3'
E2 = '/content/drive/MyDrive/gazespeakzero/E2'
import os, torch
os.makedirs(WORK, exist_ok=True)
print(WORK)
print('E2 items found:', os.path.exists(f'{E2}/results_v2/e2_items.csv') or os.path.exists(f'{E2}/results/e2_items.csv'))
print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE - switch the runtime to T4 GPU before continuing')""")
code("""!pip -q install "transformers>=4.51,<5" "sentence-transformers>=3.0" "accelerate>=0.30" pandas tabulate
import transformers, sentence_transformers
print('transformers', transformers.__version__, '| sentence-transformers', sentence_transformers.__version__)""")
code("!mkdir -p /content/e3 /content/e2")
code("%%writefile /content/e2/aac_vocab.py\n" + open(os.path.join(H, "..", "study2_scene_vocabulary", "aac_vocab.py")).read())
code("%%writefile /content/e3/build_intent_bank.py\n" + src("build_intent_bank.py"))
code("%%writefile /content/e3/e3_build_cases.py\n" + src("e3_build_cases.py"))
code("%%writefile /content/e3/e3_run.py\n" + src("e3_run.py"))
code("%%writefile /content/e3/e3_score.py\n" + src("e3_score.py"))
code("%%writefile /content/e3/smoke_test_e3.py\n" + src("smoke_test_e3.py"))
md("## 1. Build the intent bank and the cases (a few seconds)\nCheck: **60 intents**, **240 cases**, and the E2 pool sizes (if E2's items file was not found it falls back to a small built-in pool — note it if that happens, because the fallback pool changes the result).")
code("""%cd /content/e3
!python build_intent_bank.py
import os
ITEMS = f'{E2}/results_v2/e2_items.csv' if os.path.exists(f'{E2}/results_v2/e2_items.csv') else f'{E2}/results/e2_items.csv'
!python e3_build_cases.py --e2-items "{ITEMS}" --out "{WORK}/cases.jsonl\"""")
md("## 2. Self-test (about 1 minute)\nEvery line must say OK, and the last line must say **0 failed**.")
code("!cd /content/e3 && python smoke_test_e3.py")
md("## 3. Baselines (about 2 minutes)")
code("""!cd /content/e3 && python e3_run.py --bank intent_bank.json --cases "{WORK}/cases.jsonl" --out "{WORK}/outputs" --methods template prior embed""")
md("""## 4. Dry run: the smallest model on 8 cases (about 3 minutes, mostly the download)
Check that the generated sentences look like real sentences. **If they are empty or nonsense, stop and read this output before going on.**""")
code("""!cd /content/e3 && python e3_run.py --bank intent_bank.json --cases "{WORK}/cases.jsonl" --out /content/e3_dry --limit 8 --methods lm_rank_qwen1.5b lm_gen_qwen1.5b""")
md("""## 5. The four language models (about 60–80 minutes; resumable)
Each model is downloaded, used for ranking and for writing, then freed. If Colab disconnects, just run this cell again.""")
code("""!cd /content/e3 && python e3_run.py --bank intent_bank.json --cases "{WORK}/cases.jsonl" --out "{WORK}/outputs" --methods lm_rank_qwen1.5b lm_gen_qwen1.5b lm_rank_smol1.7b lm_gen_smol1.7b lm_rank_qwen3b lm_gen_qwen3b lm_rank_phi3.5 lm_gen_phi3.5""")
md("## 6. Score and report (1 minute)")
code("""!cd /content/e3 && python e3_score.py --bank intent_bank.json --cases "{WORK}/cases.jsonl" --outputs "{WORK}/outputs/outputs.jsonl" --out "{WORK}/results\"""")
code("""from IPython.display import Markdown, display
display(Markdown(open(f'{WORK}/results/E3_REPORT.md').read()))""")
md("## 7. Download\nDownload `E3_results.zip`.")
code("""import shutil, os
shutil.rmtree('/content/E3_results', ignore_errors=True); os.makedirs('/content/E3_results')
shutil.copytree(f'{WORK}/results', '/content/E3_results/results', dirs_exist_ok=True)
for f in ['cases.jsonl', 'outputs/outputs.jsonl']:
    shutil.copy(f'{WORK}/{f}', '/content/E3_results/' + os.path.basename(f))
shutil.copy('/content/e3/intent_bank.json', '/content/E3_results/intent_bank.json')
shutil.make_archive('/content/E3_results', 'zip', '/content/E3_results')
from google.colab import files; files.download('/content/E3_results.zip')""")
nb["cells"] = C
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                  "colab": {"provenance": []}, "accelerator": "GPU"}
nbf.write(nb, os.path.join(H, "E3_intent_colab.ipynb"))
print("built", len(C), "cells")
