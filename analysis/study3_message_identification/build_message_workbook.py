"""
Blinded workbook for judging the messages the models wrote (E3, `lm_gen_*` and `template`).

    python build_message_workbook.py results/e3_generations.csv results/message_rater1.xlsx [--conditions clean]

Automatic scoring only asks whether the generated message maps back to the reference intent.
It cannot say whether the sentence is one a person would be willing to have spoken aloud. That
is what this sheet asks, with the method hidden and the reference NOT shown (so the rater judges
the message on its own terms, as a listener would).

Two questions per row:
  D: could this be what the person meant, given the room and what they selected? (Y/N)
  E: is it a sentence you would be happy to have spoken aloud on your behalf? (Y/N)

Writes the key to <out folder>/message_key_private/.
"""
import argparse
import json
import os
import random

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

SEED = 0
F = "Arial"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--conditions", nargs="+", default=["clean"])
    ap.add_argument("--cases", default="cases.jsonl", help="used only to show the room")
    a = ap.parse_args()
    g = pd.read_csv(a.src)
    g = g[g.condition.isin(a.conditions)].copy()
    if os.path.exists(a.cases):
        room = {c["case_id"]: c["room"] for c in (json.loads(l) for l in open(a.cases))}
        g["room"] = g.case_id.map(room)
    else:
        g["room"] = ""
    methods = sorted(g.method.unique())
    rs = random.Random(SEED)
    codes = list("ABCDEFGH")[:len(methods)]
    rs.shuffle(codes)
    code_of = dict(zip(methods, codes))
    g["code"] = g.method.map(code_of)
    g["row_uid"] = ["M%04d" % i for i in range(len(g))]
    g = g.sample(frac=1.0, random_state=SEED).reset_index(drop=True)      # hide the method order

    key_dir = os.path.join(os.path.dirname(a.out) or ".", "message_key_private")
    os.makedirs(key_dir, exist_ok=True)
    g[["row_uid", "case_id", "method", "code", "condition", "generated", "reference",
       "auto_correct"]].to_csv(os.path.join(key_dir, "message_key_DO_NOT_OPEN_BEFORE_RATING.csv"), index=False)
    json.dump(code_of, open(os.path.join(key_dir, "message_codes.json"), "w"), indent=1)

    wb = Workbook()
    h = wb.active
    h.title = "How to rate"
    lines = [
        ("E3: are these messages usable? (blinded)", "t"),
        ("", None),
        (f"{len(g)} rows. Each row is a sentence some method produced for a person who selected the "
         "objects listed. Which method wrote it is hidden, and the 'correct' sentence is deliberately "
         "not shown: judge the sentence as a listener would.", None),
        ("", None),
        ("Column D: could this be what the person meant?", "h"),
        ("Y = given the room and the objects they selected, this is a reasonable reading of their message.", None),
        ("N = it does not follow from what they selected, or it says something they did not select.", None),
        ("", None),
        ("Column E: would you be happy to have this spoken aloud on your behalf?", "h"),
        ("Y = a natural, dignified sentence you would accept as your own words.", None),
        ("N = broken English, odd phrasing, childish or demeaning, or it states something as fact that "
         "the person did not say (for example inventing pain, or naming a person).", None),
        ("", None),
        ("Fill both columns for every row. Save often (Ctrl+S). The Progress sheet shows what is left.", None),
        ("Do not open 'message_key_private' until the rating is finished: it reveals the methods.", "r"),
    ]
    r = 1
    for text, kind in lines:
        c = h.cell(row=r, column=1, value=text)
        c.font = Font(name=F, size=14 if kind == "t" else 11, bold=kind in ("t", "h"),
                      color="C00000" if kind == "r" else "000000")
        c.alignment = Alignment(wrap_text=True, vertical="top")
        h.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
        h.row_dimensions[r].height = 22 if kind == "t" else 15 * max(1, -(-len(text) // 105))
        r += 1
    for col, w in zip("ABCD", (22, 22, 22, 34)):
        h.column_dimensions[col].width = w

    s = wb.create_sheet("Rating")
    hdr = ["#", "Room", "They selected", "The message", "D: could this be what they meant? (Y/N)",
           "E: happy to have it spoken aloud? (Y/N)", "Notes (optional)", "row_uid"]
    HF = PatternFill("solid", fgColor="1F3864")
    for j, v in enumerate(hdr, 1):
        c = s.cell(row=1, column=j, value=v)
        c.font, c.fill = Font(name=F, bold=True, color="FFFFFF"), HF
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    s.row_dimensions[1].height = 45
    cases = None
    INPUT = PatternFill("solid", fgColor="FFF2CC")
    BAND = PatternFill("solid", fgColor="EEF3FA")
    for i, row in g.iterrows():
        rr = i + 2
        room = row.get("room", "") or ""
        vals = [i + 1, room, row.objects_shown, row.generated, None, None, None, row.row_uid]
        for j, v in enumerate(vals, 1):
            c = s.cell(row=rr, column=j, value=v)
            c.font = Font(name=F, color="808080" if j == 8 else "000000")
            c.alignment = Alignment(wrap_text=(j == 4), vertical="top")
            if j in (5, 6):
                c.fill = INPUT
                c.alignment = Alignment(horizontal="center")
            elif i % 2:
                c.fill = BAND
    last = len(g) + 1
    dv = DataValidation(type="list", formula1='"Y,N"', allow_blank=True, showErrorMessage=True,
                        errorTitle="Y or N", error="Please choose Y or N.")
    s.add_data_validation(dv)
    dv.add(f"E2:F{last}")
    s.conditional_formatting.add(f"E2:F{last}", FormulaRule(formula=['E2<>""'],
                                                            fill=PatternFill("solid", fgColor="C6EFCE")))
    s.freeze_panes = "E2"
    s.auto_filter.ref = f"A1:H{last}"
    for col, w in zip("ABCDEFGH", (5, 13, 28, 60, 18, 18, 28, 10)):
        s.column_dimensions[col].width = w
    thin = Side(style="thin", color="BFBFBF")
    for cell in s[1]:
        cell.border = Border(bottom=thin)

    p = wb.create_sheet("Progress")
    rows = [("Rows to rate", f"=COUNTA(Rating!$D$2:$D${last})"),
            ("D filled", f'=COUNTIF(Rating!$E$2:$E${last},"Y")+COUNTIF(Rating!$E$2:$E${last},"N")'),
            ("E filled", f'=COUNTIF(Rating!$F$2:$F${last},"Y")+COUNTIF(Rating!$F$2:$F${last},"N")'),
            ("Percent complete", "=IF(B2=0,0,(B3+B4)/(2*B2))"),
            ("", None),
            ("Problems (should be 0)", None),
            ("Rows missing an answer", "=2*B2-B3-B4")]
    p.cell(row=1, column=1, value="Progress").font = Font(name=F, size=14, bold=True)
    for i, (k, f) in enumerate(rows, 2):
        p.cell(row=i, column=1, value=k).font = Font(name=F, bold=(f is None and k != ""))
        if f:
            p.cell(row=i, column=2, value=f).font = Font(name=F)
    p["B5"].number_format = "0%"
    p.column_dimensions["A"].width = 30
    p.column_dimensions["B"].width = 14
    wb.active = 0
    wb.save(a.out)
    print(f"wrote {a.out}: {len(g)} rows, {len(methods)} methods, conditions {a.conditions}")
    print("key:", key_dir)


if __name__ == "__main__":
    main()
