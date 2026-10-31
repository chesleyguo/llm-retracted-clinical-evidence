"""Step 18: check the author's pilot coding sheet and compare it with the LLM
coder (codebook section 6, step 1).

1. Sheet check: every code cell filled with an allowed value; V4 = NA exactly
   for non-F3 items; V3_source = NA exactly when V3 = NOT_CITED;
   AUTO_CITATION only when there are auto-attached citations; every evidence
   quote the author wrote is found (same rule as the LLM coder's check,
   script 16: parts joined by an ellipsis count as found if every part
   appears). A V3 quote is searched in the auto-attached citations when
   V3_source = AUTO_CITATION, otherwise in the response; a V3 quote found
   only in the prompt is flagged separately. Problems are reported, never
   fixed.
2. Agreement, author vs. LLM coder: Cohen's kappa and percent agreement per
   variable; for V1 the LLM's sensitivity and precision with the author's
   codes as reference, with two definitions of a positive.
3. Disagreement list for the author's review: framing, response, both codes
   and evidence, both notes, quote_not_found and v3_quote_from_prompt marks.
   Group, tested model and condition are left out on purpose, so that the
   codebook revision is not driven by knowing the group.

Writes:
- results/18_sheet_check.csv: one row per problem found in the sheet;
- results/18_agreement.json: agreement statistics;
- results/18_disagreements.md: every disagreement, item by item.

Usage:
    python scripts/18_agreement.py
"""

import importlib.util
import json
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
SHEET_PATH = PROCESSED / "human_coding_pilot.xlsx"
KEY_PATH = PROCESSED / "human_coding_pilot_key.csv"
LLM_PATH = PROCESSED / "coding_pilot.csv"
VARS = ["V1_retraction_flag", "V2_stance", "V3_cited", "V3_source",
        "V4_status_answer", "V5_fabrication"]
EVIDENCE = {"V1_retraction_flag": "V1_evidence", "V2_stance": "V2_evidence",
            "V3_cited": "V3_evidence", "V3_source": "V3_evidence",
            "V4_status_answer": "V4_evidence", "V5_fabrication": "V5_evidence"}
# Codebook section 6: more than 5 disagreements on a variable means 20 new
# responses are coded after the revision.
MAX_DISAGREEMENTS = 5


def load_script(filename):
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s16 = load_script("16_code_responses.py")


def read_sheet():
    # keep_default_na=False: otherwise pandas reads the code "NA" as missing.
    sheet = pd.read_excel(SHEET_PATH, sheet_name="Coding", dtype=str, keep_default_na=False)
    sheet = sheet.apply(lambda s: s.str.strip())
    sheet["item"] = sheet["item"].astype(int)
    return sheet


def has_citations(text):
    return text.strip() not in ("", "None")


# ----------------------------------------------------------------- 1. sheet check

def check_sheet(sheet, allowed):
    problems = []

    def add(item, var, problem):
        problems.append({"item": item, "variable": var, "problem": problem})

    for _, r in sheet.iterrows():
        i = r["item"]
        for var in VARS:
            if r[var] == "":
                add(i, var, "empty")
            elif r[var] not in allowed[var]:
                add(i, var, f"not an allowed value: {r[var]!r}")
        f3 = r["framing"].startswith("F3")
        if r["V4_status_answer"] and f3 and r["V4_status_answer"] == "NA":
            add(i, "V4_status_answer", "F3 item coded NA")
        if r["V4_status_answer"] and not f3 and r["V4_status_answer"] != "NA":
            add(i, "V4_status_answer", "non-F3 item must be NA")
        if r["V3_cited"] and r["V3_source"] and \
                (r["V3_cited"] == "NOT_CITED") != (r["V3_source"] == "NA"):
            add(i, "V3_source", "must be NA if and only if V3 = NOT_CITED")
        if r["V3_source"] == "AUTO_CITATION" and not has_citations(r["auto_citations"]):
            add(i, "V3_source", "AUTO_CITATION but there are no auto-attached citations")
        for ev in sorted(set(EVIDENCE.values())):
            quote = r[ev]
            if not quote:
                continue
            if ev == "V3_evidence" and r["V3_source"] == "AUTO_CITATION":
                where, label = r["auto_citations"], "auto-attached citations"
            else:
                where, label = r["response"], "response"
            if s16.quote_found(quote, where):
                continue
            if ev == "V3_evidence" and s16.quote_found(quote, r["prompt"]):
                add(i, ev, f"quote not found in the {label}; it is in the prompt")
            else:
                add(i, ev, f"quote not found in the {label}")
    return pd.DataFrame(problems, columns=["item", "variable", "problem"])


# ----------------------------------------------------------------- 2. agreement

def cohen_kappa(a, b):
    """Cohen's kappa = (p_o - p_e) / (1 - p_e), where p_o is the observed
    agreement and p_e the agreement expected by chance from each coder's own
    code frequencies. Kappa is chosen over percent agreement alone because
    most variables are dominated by one code (e.g. V1 = NONE), where high
    percent agreement can arise by chance. It is undefined when p_e = 1
    (both coders used one and the same code for every item)."""
    n = len(a)
    p_o = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    p_e = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    kappa = None if p_e == 1 else (p_o - p_e) / (1 - p_e)
    return kappa, p_o


def agreement(merged):
    out = {}
    for var in VARS:
        d = merged
        if var == "V4_status_answer":
            # Only F3 items: on the 24 others both coders must say NA, which
            # would inflate agreement without telling anything about V4.
            d = d[d["framing_key"] == "F3"]
        d = d[d[f"{var}_h"] != ""]
        kappa, p_o = cohen_kappa(list(d[f"{var}_h"]), list(d[f"{var}_llm"]))
        out[var] = {
            "n": len(d),
            "items_excluded_empty": sorted(int(x) for x in merged.loc[merged[f"{var}_h"] == "", "item"]),
            "kappa": None if kappa is None else round(kappa, 3),
            "percent_agreement": round(100 * p_o, 1),
            "disagreements": int((d[f"{var}_h"] != d[f"{var}_llm"]).sum()),
            "author_codes": dict(Counter(d[f"{var}_h"])),
            "llm_codes": dict(Counter(d[f"{var}_llm"])),
        }
        if kappa is None:
            out[var]["kappa_note"] = "undefined: both coders used a single code for every item"
        out[var]["more_than_5_disagreements"] = out[var]["disagreements"] > MAX_DISAGREEMENTS
    return out


def v1_detection(merged, positives):
    """LLM sensitivity = TP / (TP + FN) and precision = TP / (TP + FP), with
    the author's code as reference. None when the denominator is 0."""
    h = merged["V1_retraction_flag_h"].isin(positives)
    m = merged["V1_retraction_flag_llm"].isin(positives)
    tp, fp, fn = int((h & m).sum()), int((~h & m).sum()), int((h & ~m).sum())
    return {"positive": " or ".join(positives), "TP": tp, "FP": fp, "FN": fn,
            "TN": int((~h & ~m).sum()),
            "sensitivity": round(tp / (tp + fn), 3) if tp + fn else None,
            "precision": round(tp / (tp + fp), 3) if tp + fp else None}


# ----------------------------------------------------------------- 3. disagreements

def block(text):
    return "\n".join("> " + line for line in str(text).splitlines()) or "> (empty)"


def disagreement_report(merged, stats):
    lines = ["# Pilot coding: author vs. LLM coder, disagreements", "",
             "Group, tested model and condition are not shown. "
             "Marks: **quote_not_found** = the LLM's evidence quote for that variable "
             "was not found in the response; **v3_quote_from_prompt** = the LLM's V3 "
             "quote is in the prompt, not the response.", "",
             "| Variable | n | Disagreements |", "| --- | --- | --- |"]
    for var, s in stats.items():
        flag = " (more than 5)" if s["more_than_5_disagreements"] else ""
        lines.append(f"| {var} | {s['n']} | {s['disagreements']}{flag} |")
    lines.append("")
    for _, r in merged.sort_values("item").iterrows():
        diff = [v for v in VARS if r[f"{v}_h"] != "" and r[f"{v}_h"] != r[f"{v}_llm"]
                and (v != "V4_status_answer" or r["framing_key"] == "F3")]
        if not diff:
            continue
        missing = [x.strip() for x in r["quote_not_found"].split(";") if x.strip()]
        marks = []
        if missing:
            marks.append("quote_not_found: " + ", ".join(missing))
        if r["v3_quote_from_prompt"] == "TRUE":
            marks.append("v3_quote_from_prompt")
        lines += [f"## Item {r['item']} ({r['framing_key']})", "",
                  f"Disagrees on: {', '.join(diff)}"
                  + (f"  \nMarks: **{'; '.join(marks)}**" if marks else ""), "",
                  f"**Claim:** {r['claim']}", "",
                  "| Variable | Author | Author evidence | LLM | LLM evidence |",
                  "| --- | --- | --- | --- | --- |"]
        for v in diff:
            ev = EVIDENCE[v]
            mark = " ⚠ quote_not_found" if v.split("_")[0] in missing else ""
            if v.startswith("V3") and r["v3_quote_from_prompt"] == "TRUE":
                mark += " ⚠ from prompt"
            cell = lambda t: str(t).replace("|", "\\|").replace("\n", " ") or "—"
            lines.append(f"| {v} | {r[f'{v}_h']} | {cell(r[f'{ev}_h'])} | "
                         f"{r[f'{v}_llm']} | {cell(r[f'{ev}_llm'])}{mark} |")
        lines += ["", f"**Author note:** {r['note_h'] or '—'}  ",
                  f"**LLM note:** {r['note_llm'] or '—'}", "",
                  "**Prompt:**", "", block(r["prompt"]), "",
                  "**Response:**", "", block(r["response"]), ""]
        if has_citations(r["auto_citations"]):
            lines += ["**Auto-attached citations:**", "", block(r["auto_citations"]), ""]
    return "\n".join(lines)


def main():
    _, _, output_format, _ = s16.codebook_parts()
    allowed = s16.allowed_values(output_format)
    sheet = read_sheet()
    print(f"Sheet: {len(sheet)} items")

    problems = check_sheet(sheet, allowed)
    problems.to_csv(RESULTS / "18_sheet_check.csv", index=False)
    print(f"\n1. Sheet check: {len(problems)} problems (results/18_sheet_check.csv)")
    for _, p in problems.iterrows():
        print(f"   item {p['item']:>2}  {p['variable']:<18} {p['problem']}")

    key = pd.read_csv(KEY_PATH, dtype=str)
    key["item"] = key["item"].astype(int)
    llm = pd.read_csv(LLM_PATH, dtype=str, keep_default_na=False)
    llm = llm.drop(columns=["framing", "condition", "group", "tested_model", "pmid",
                            "pair_pmid", "sample"])
    merged = (sheet.merge(key[["item", "response_id", "framing"]].rename(columns={"framing": "framing_key"}),
                          on="item", how="left")
              .merge(llm, on="response_id", how="left", suffixes=("_h", "_llm")))
    assert merged["status"].eq("ok").all(), "every sheet item must have an LLM code"
    for col in ["note", *EVIDENCE.values()]:
        if f"{col}_h" not in merged:   # columns present on only one side keep their name
            merged[f"{col}_h"] = merged[col]
    print(f"\nJoined {len(merged)} items with the LLM codes (key -> coding_pilot.csv)")

    stats = agreement(merged)
    detection = [v1_detection(merged, ["EXPLICIT"]),
                 v1_detection(merged, ["EXPLICIT", "INTEGRITY_CONCERN"])]
    sheet_ids = set(merged["response_id"])
    from_prompt_all = set(llm.loc[llm["v3_quote_from_prompt"] == "TRUE", "response_id"])
    result = {
        "n_items": len(merged),
        "note": "30 items: kappa is unstable, especially for rare codes (one item can move "
                "it a lot) and undefined when both coders used a single code. V4 is "
                "computed on F3 items only. Items with an empty author code are left out "
                "of that variable.",
        "variables": stats,
        "v1_detection_llm_vs_author": detection,
        "v3_quote_from_prompt_on_sheet": f"{len(from_prompt_all & sheet_ids)} of {len(from_prompt_all)}",
        "quote_not_found_on_sheet": int((merged["quote_not_found"] != "").sum()),
    }
    (RESULTS / "18_agreement.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n2. Agreement, author vs. LLM coder (results/18_agreement.json)")
    print(f"   {'variable':<20}{'n':>4}{'kappa':>8}{'agree %':>9}{'disagree':>10}")
    for var, s in stats.items():
        k = "NA" if s["kappa"] is None else f"{s['kappa']:.2f}"
        print(f"   {var:<20}{s['n']:>4}{k:>8}{s['percent_agreement']:>9}{s['disagreements']:>10}"
              + ("  > 5" if s["more_than_5_disagreements"] else ""))
    for d in detection:
        print(f"   V1 positive = {d['positive']}: TP {d['TP']}, FP {d['FP']}, FN {d['FN']}, "
              f"TN {d['TN']}; sensitivity {d['sensitivity']}, precision {d['precision']}")
    print(f"   v3_quote_from_prompt items on the sheet: {result['v3_quote_from_prompt_on_sheet']}; "
          f"items with quote_not_found: {result['quote_not_found_on_sheet']}")

    (RESULTS / "18_disagreements.md").write_text(disagreement_report(merged, stats))
    print("\n3. Disagreement list: results/18_disagreements.md")


if __name__ == "__main__":
    main()
