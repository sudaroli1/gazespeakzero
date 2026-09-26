import nbformat as nbf, os
H = os.path.dirname(os.path.abspath(__file__))
src = lambda p: open(os.path.join(H, p)).read()
nb = nbf.v4.new_notebook(); C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s)); code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("""# GazeSpeakZero — E2: how well does each method name the useful objects in an everyday scene?

**Before you start: Runtime → Change runtime type → T4 GPU → Save.** (A GPU is needed for the vision models.)

Run the cells **one at a time** with Shift + Enter. Total time is about 1–1.5 hours, most of it unattended. If the install cell prints a warning about restarting the session, do Runtime → Restart session and run from the top again. Everything is saved to Google Drive (`MyDrive/gazespeakzero/E2`), so if Colab disconnects, run the cells again and it resumes where it stopped.

What it does: 300 everyday indoor photos (bathroom, bedroom, kitchen, living room, dining) from LVIS/COCO. Four methods each propose 12 items per photo, and their items are checked against the photos' object labels:
- a fixed list with no camera (the Look to Speak style);
- CLIP;
- the original paper's BLIP-2 step;
- a small modern vision-language model, Qwen2.5-VL-3B.""")
code("""from google.colab import drive
drive.mount('/content/drive')
WORK = '/content/drive/MyDrive/gazespeakzero/E2'
import os, torch; os.makedirs(WORK, exist_ok=True); print(WORK)
print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE - switch the runtime to T4 GPU before continuing')
!df -h /content | tail -1""")
code("""!pip -q install "transformers==4.51.3" "huggingface_hub<1.0" "tokenizers<0.22" "accelerate>=0.30" requests pandas
import transformers
from transformers import CLIPModel, Blip2ForConditionalGeneration, Qwen2_5_VLForConditionalGeneration
print('transformers', transformers.__version__, '- imports OK')""")
md("## 1. Annotations (about 5 minutes)")
code("""%%bash
cd /content
[ -f lvis_v1_val.json ] || { wget -q --show-progress -O lvis_v1_val.json.zip https://dl.fbaipublicfiles.com/LVIS/lvis_v1_val.json.zip && unzip -q -o lvis_v1_val.json.zip && rm lvis_v1_val.json.zip; }
[ -f instances_val2017.json ] || { wget -q --show-progress -O ann.zip http://images.cocodataset.org/annotations/annotations_trainval2017.zip && unzip -q -o -j ann.zip annotations/instances_train2017.json annotations/instances_val2017.json && rm ann.zip; }
[ -f coco_to_synset.json ] || wget -q -O coco_to_synset.json https://raw.githubusercontent.com/lvis-dataset/lvis-api/master/data/coco_to_synset.json
ls -la lvis_v1_val.json instances_train2017.json instances_val2017.json coco_to_synset.json""")
code("!mkdir -p /content/e2")
code("%%writefile /content/e2/aac_vocab.py\n" + src("aac_vocab.py"))
code("%%writefile /content/e2/e2_build_set.py\n" + src("e2_build_set.py"))
code("%%writefile /content/e2/e2_generate.py\n" + src("e2_generate.py"))
code("%%writefile /content/e2/e2_score.py\n" + src("e2_score.py"))
md("## 2. Choose the 300 scenes and download the photos (about 3–5 minutes)\nCheck the output: the number of scenes per room, and **images downloaded: 300/300** (a few failures are fine).")
code("""!cd /content/e2 && python e2_build_set.py --lvis /content/lvis_v1_val.json --out "{WORK}/set" --per-room 60 --coco-ann /content/instances_train2017.json /content/instances_val2017.json --coco-synset /content/coco_to_synset.json""")
md("## 3. Dry run: every method on 3 scenes (about 10–15 minutes, mostly downloading the models)\nEach method should print a list of real object names for the first scene. **If any method crashes or prints nonsense, stop and read this cell's output before going on.**")
code("""!cd /content/e2 && python e2_generate.py --set "{WORK}/set" --out /content/e2_dry --limit 3 --methods static clip blip2_orig qwen_vl
import json
for l in open('/content/e2_dry/outputs.dry.jsonl'):
    o = json.loads(l)
    print(f"{o['method']:11s} scene {o['image_id']}: {', '.join(o['items'][:8])}   ({o['seconds']:.2f} s)")""")
md("## 4. All 300 scenes (about 30–45 minutes; resumable)")
code("""!cd /content/e2 && python e2_generate.py --set "{WORK}/set" --out "{WORK}/outputs" --methods static clip blip2_orig qwen_vl""")
md("## 5. Score and report (1 minute)")
code("""!cd /content/e2 && python e2_score.py --set "{WORK}/set" --outputs "{WORK}/outputs/outputs.jsonl" --out "{WORK}/results\"""")
code("""from IPython.display import Markdown, display
display(Markdown(open(f'{WORK}/results/E2_REPORT.md').read()))""")
md("## 6. Download the results\nDownload `E2_results.zip`. It contains the report, the per-item tables and the blinded audit sheet (`audit_sheet.csv`).")
code("""import shutil, os
os.makedirs('/content/E2_results', exist_ok=True)
shutil.copytree(f'{WORK}/results', '/content/E2_results/results', dirs_exist_ok=True)
shutil.copy(f'{WORK}/outputs/outputs.jsonl', '/content/E2_results/outputs.jsonl')
shutil.copy(f'{WORK}/set/set.jsonl', '/content/E2_results/set.jsonl')
shutil.make_archive('/content/E2_results', 'zip', '/content/E2_results')
from google.colab import files; files.download('/content/E2_results.zip')""")
nb["cells"] = C
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "colab": {"provenance": []}, "accelerator": "GPU"}
nbf.write(nb, os.path.join(H, "E2_scene_vocab_colab.ipynb")); print("built", len(C), "cells")
