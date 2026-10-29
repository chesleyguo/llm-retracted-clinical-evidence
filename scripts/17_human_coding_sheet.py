"""Step 17: human coding sheet for the pilot round (codebook section 6, step 1).

Draws 30 responses from the design cells of the pilot, stratified by tested
model x framing x condition (15 cells, 2 per cell; seed 2026), without looking
at the LLM coder's codes. The sheet shows the coder exactly what the LLM coder
sees (paper, claim, framing, prompt, response, auto-attached citations) and
nothing else: no group, tested model, condition or LLM codes. Rows are in
random order.

V6 is not on the sheet: it needs the Retraction Watch record, which would
reveal the group.

Writes:
- data/processed/human_coding_pilot.xlsx: sheet "Coding" with a drop-down list
  of the allowed codes for each code column; sheet "Codebook" with a quick
  reference to codebook sections 2-3 (read from docs/codebook.md);
- data/processed/human_coding_pilot_key.csv: item number -> response, for
  comparing with the LLM codes later.

Usage:
    python scripts/17_human_coding_sheet.py
"""

import importlib.util
import json
import random
import re
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
SHEET_PATH = PROCESSED / "human_coding_pilot.xlsx"
KEY_PATH = PROCESSED / "human_coding_pilot_key.csv"
SEED = 2026
PER_CELL = 2
EXCEL_CELL_MAX = 32767


def load_script(filename):
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s16 = load_script("16_code_responses.py")


def draw(responses):
    """2 responses per model x framing x condition cell, then shuffled."""
    rng = random.Random(SEED)
    cells = {}
    for r in responses:
        cells.setdefault((r["model_requested"], r["framing"], r["condition"]), []).append(r)
    picked = []
    for cell in sorted(cells):
        pool = sorted(cells[cell], key=lambda r: r["call_id"])
        picked += rng.sample(pool, PER_CELL)
    rng.shuffle(picked)
    print(f"  {len(cells)} cells x {PER_CELL} = {len(picked)} responses (seed {SEED})")
    return picked


def plain(text):
    """Markdown emphasis removed for display in Excel."""
    return text.replace("**", "")


def fit(text):
    if len(text) <= EXCEL_CELL_MAX:
        return text
    return text[:EXCEL_CELL_MAX - 40] + "\n[truncated: too long for one cell]"


def quick_reference(sections):
    """Rows for the Codebook sheet: general rules, then each variable's codes,
    definitions, examples and decision rules (V6 left out, see docstring)."""
    rows = [["GENERAL RULES", "", "", "", "", ""]]
    general = re.search(r"## 2\. .*?\n(.*?)\n## 3\. ", sections, re.S).group(1)
    for line in general.strip().splitlines():
        if re.match(r"\d+\. ", line):
            rows.append(["", "", "", plain(line), "", ""])
    for block in re.split(r"\n(?=### )", sections)[1:]:
        heading = block.splitlines()[0].replace("### ", "")
        if heading.startswith("V6"):
            continue
        question = next((l for l in block.splitlines()[1:] if l.strip() and not l.startswith("|")), "")
        codes = re.findall(r"^\| ([A-Z_]+) \| (.*?) \|$", block, re.M)
        examples = {}
        for ex, code in re.findall(r'^- (.*?) → ([A-Z_]+)$', block, re.M):
            examples.setdefault(code, []).append(ex)
        rules = re.search(r"Decision rules?:?\s*\n?(.*?)(?=\nExamples:|\Z)", block, re.S)
        rules = plain(rules.group(1).strip()) if rules else ""
        for i, (code, definition) in enumerate(codes):
            rows.append([heading if i == 0 else "", plain(question) if i == 0 else "", code,
                         plain(definition), "\n".join(examples.get(code, [])),
                         rules if i == 0 else ""])
    return rows


def main():
    template, sections, output_format, _ = s16.codebook_parts()
    allowed = s16.allowed_values(output_format)
    papers = s16.load_papers()
    responses, _ = s16.load_responses("pilot")
    picked = draw(responses)

    code_cols = []
    for var in json.loads(output_format):
        if var in ("response_id", "note"):
            continue
        code_cols.append(var)
    code_cols.append("note")
    info_cols = ["item", "title", "authors", "year", "journal", "abstract", "claim",
                 "framing", "prompt", "response", "auto_citations"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Coding"
    ws.append(info_cols + code_cols)
    key_rows = []
    for i, r in enumerate(picked, 1):
        p = papers[r["pmid"]]
        ws.append([i, p["title"], p["authors"], p["year"], p["journal"], fit(p["abstract"]),
                   p["claim"], s16.FRAMING_LABELS[r["framing"]], fit(r["prompt"]),
                   fit(r["response_text"]), fit(s16.format_citations(r))] + [""] * len(code_cols))
        key_rows.append({"item": i, "response_id": r["call_id"], "pmid": r["pmid"],
                         "pair_pmid": r["pair_pmid"], "group": r["group"],
                         "tested_model": r["model_requested"], "framing": r["framing"],
                         "condition": r["condition"], "seed": SEED})

    widths = {"item": 6, "title": 30, "authors": 20, "year": 7, "journal": 20, "abstract": 60,
              "claim": 35, "framing": 14, "prompt": 40, "response": 80, "auto_citations": 40}
    n = len(picked)
    for j, col in enumerate(info_cols + code_cols, 1):
        letter = ws.cell(row=1, column=j).column_letter
        ws.column_dimensions[letter].width = widths.get(col, 30 if col.endswith(("evidence", "note")) else 22)
        if col in allowed:
            dv = DataValidation(type="list", formula1='"' + ",".join(sorted(allowed[col])) + '"',
                                allow_blank=True, showErrorMessage=True,
                                errorTitle="Not an allowed code",
                                error="Choose one of: " + ", ".join(sorted(allowed[col])))
            ws.add_data_validation(dv)
            dv.add(f"{letter}2:{letter}{n + 1}")
    entry = PatternFill("solid", fgColor="FFF2CC")   # columns the coder fills
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if cell.row > 1 and ws.cell(row=1, column=cell.column).value in code_cols:
                cell.fill = entry
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "B2"

    ref = wb.create_sheet("Codebook")
    ref.append(["Variable", "Question", "Code", "Definition", "Example", "Decision rules"])
    for row in quick_reference(sections):
        ref.append(row)
    for letter, w in zip("ABCDEF", [24, 40, 22, 60, 50, 70]):
        ref.column_dimensions[letter].width = w
    for row in ref.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    for cell in ref[1]:
        cell.font = Font(bold=True)
    ref.freeze_panes = "A2"

    wb.save(SHEET_PATH)
    pd.DataFrame(key_rows).to_csv(KEY_PATH, index=False)
    print(f"Wrote {SHEET_PATH.relative_to(ROOT)} ({n} responses) and {KEY_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
