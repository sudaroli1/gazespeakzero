"""
E3 smoke test: runs without a GPU, without downloading any model.

    python smoke_test_e3.py

Checks the bank, the case builder (determinism and what each condition changes), the two
cheap methods, an oracle and an anti-oracle through the scorer, resume after a half-written
line, and that the report is written.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
ok = fail = 0


def check(cond, msg):
    global ok, fail
    print(("OK   " if cond else "FAIL ") + msg)
    ok, fail = ok + bool(cond), fail + (not cond)


def run(*args):
    r = subprocess.run([PY] + list(args), capture_output=True, text=True, cwd=HERE)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
    return r


tmp = tempfile.mkdtemp()
try:
    # ---- bank
    r = run("build_intent_bank.py")
    check(r.returncode == 0, "intent bank builds and every object is in the AAC vocabulary")
    bank = json.load(open(os.path.join(HERE, "intent_bank.json")))
    check(len(bank) == 60, f"60 intents ({len(bank)})")
    check(len({b["utterance"] for b in bank}) == 60, "no duplicate utterances")
    check(all(1 <= len(b["objects"]) <= 3 for b in bank), "1-3 objects per intent")
    check(all(len(b["paraphrases"]) == 2 for b in bank), "two paraphrases per intent")

    # ---- cases
    c1, c2 = os.path.join(tmp, "c1.jsonl"), os.path.join(tmp, "c2.jsonl")
    run("e3_build_cases.py", "--out", c1)
    run("e3_build_cases.py", "--out", c2)
    check(open(c1).read() == open(c2).read(), "case building is deterministic")
    cases = [json.loads(l) for l in open(c1)]
    check(len(cases) == 240, f"240 cases ({len(cases)})")
    byc = {}
    for c in cases:
        byc.setdefault(c["condition"], []).append(c)
    check(all(len(c["objects_shown"]) == 1 for c in byc["partial"]), "partial shows one object")
    check(all(c["objects_shown"] == c["objects_true"] for c in byc["clean"]), "clean is unchanged")
    for cond in ("wrong_label", "wrong_pick"):
        changed = [c for c in byc[cond] if c["objects_shown"] != c["objects_true"]]
        check(len(changed) == 60, f"{cond} changes every case ({len(changed)}/60)")
        check(all(len(c["objects_shown"]) == len(c["objects_true"]) for c in byc[cond]),
              f"{cond} keeps the number of selections")
        multi = [c for c in byc[cond] if len(c["objects_true"]) > 1]
        check(all(c["objects_shown"][0] == c["objects_true"][0] for c in multi),
              f"{cond} keeps the first selection when there are several")

    # ---- cheap methods
    out = os.path.join(tmp, "out")
    r = run("e3_run.py", "--cases", c1, "--out", out, "--methods", "template", "prior")
    check(r.returncode == 0, "template and prior run")
    lines = open(os.path.join(out, "outputs.jsonl")).read().splitlines()
    check(len(lines) == 480, f"one line per method and case ({len(lines)})")

    # resume after a half-written last line
    with open(os.path.join(out, "outputs.jsonl"), "a") as f:
        f.write('{"method": "prior", "case_id": "I01:cle')
    r = run("e3_run.py", "--cases", c1, "--out", out, "--methods", "template", "prior")
    lines2 = open(os.path.join(out, "outputs.jsonl")).read().splitlines()
    check(r.returncode == 0 and len(lines2) == 480, f"resume drops the broken line and re-runs nothing ({len(lines2)})")

    # dry run writes a separate file
    r = run("e3_run.py", "--cases", c1, "--out", out, "--methods", "template", "--limit", "8")
    check(os.path.exists(os.path.join(out, "outputs.dry.jsonl")) and len(lines2) == 480,
          "a dry run cannot overwrite the full output")

    # ---- scorer: oracle and anti-oracle
    ids = [b["id"] for b in bank]
    orc = os.path.join(tmp, "oracle.jsonl")
    with open(orc, "w") as f:
        for c in cases:
            gold = c["intent_id"]
            others = [i for i in ids if i != gold]
            f.write(json.dumps({"method": "oracle", "case_id": c["case_id"], "seconds": 0,
                                "ranked": [gold] + others[:9]}) + "\n")
            f.write(json.dumps({"method": "anti", "case_id": c["case_id"], "seconds": 0,
                                "ranked": others[:10]}) + "\n")
            f.write(json.dumps({"method": "third", "case_id": c["case_id"], "seconds": 0,
                                "ranked": others[:2] + [gold] + others[2:9]}) + "\n")
            f.write(json.dumps({"method": "gen_gold", "case_id": c["case_id"], "seconds": 0,
                                "text": [b for b in bank if b["id"] == gold][0]["utterance"]}) + "\n")
    res = os.path.join(tmp, "res")
    r = run("e3_score.py", "--cases", c1, "--outputs", orc, "--out", res)
    check(r.returncode == 0, "scorer runs")
    import pandas as pd
    s = pd.read_csv(os.path.join(res, "e3_summary.csv")).set_index("method")
    check(s.loc["oracle", "top1"] == 1.0 and s.loc["oracle", "top3"] == 1.0, "oracle scores 1.0")
    check(s.loc["anti", "top1"] == 0.0 and s.loc["anti", "top3"] == 0.0, "anti-oracle scores 0.0")
    check(s.loc["third", "top1"] == 0.0 and s.loc["third", "top3"] == 1.0, "gold at rank 3 gives top1 0, top3 1")
    check(s.loc["gen_gold", "top1"] > 0.9, f"a generation equal to the reference maps back to it "
                                           f"({s.loc['gen_gold', 'top1']:.2f}, token fallback)")
    gen = pd.read_csv(os.path.join(res, "e3_generations.csv"))
    check(len(gen) == 240 and "reference" in gen.columns, "generations sheet written for the human check")
    check(os.path.exists(os.path.join(res, "E3_REPORT.md")), "report written")

    # unequal coverage: only the common cases are scored
    part = os.path.join(tmp, "part.jsonl")
    with open(part, "w") as f:
        for i, l in enumerate(open(orc)):
            o = json.loads(l)
            if o["method"] == "anti" and i % 3 == 0:
                continue
            f.write(l)
    r = run("e3_score.py", "--cases", c1, "--outputs", part, "--out", os.path.join(tmp, "res2"))
    s2 = pd.read_csv(os.path.join(tmp, "res2", "e3_summary.csv"))
    check(s2.cases.nunique() == 1, f"every method scored on the same cases ({sorted(set(s2.cases))})")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
