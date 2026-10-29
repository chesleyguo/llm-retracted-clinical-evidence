"""Step 12: build the claims review table.

Collects the step-11 answers (current prompt files only) from
outputs/llm_calls/claims.jsonl, fills the fixed F2 and F3 templates
(prompts/f2_paper_question.txt, prompts/f3_status_question.txt) from PubMed
metadata, runs simple checks, and adds one row per paper to
data/processed/claims_review.csv for the author to review.

Rows already in the table are never changed, so the author's entries in
approved / edited_claim / edited_question are kept; only papers not yet in the
table are added. Checks are flags for the reviewer, not exclusions.

Template fields, the same rules for both groups:
- title: PubMed ArticleTitle, with retraction labels such as "RETRACTED:"
  removed (they would reveal the group), square brackets around a translated
  title (non-English article) removed, and the final period removed;
- first_author: surname of the first PubMed author;
- journal: PubMed journal title without parenthetical notes, a parallel title
  after "=", or a subtitle after a colon, converted to title case;
- year: PubMed journal-issue year.

Usage:
    python scripts/12_build_claims_review.py pilot     # or: main, all
"""

import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
PROMPTS = ROOT / "prompts"
REVIEW_PATH = PROCESSED / "claims_review.csv"
XML_DIRS = [ROOT / "data" / "raw" / "pubmed", ROOT / "data" / "raw" / "pubmed_controls" / "efetch"]

COLUMNS = ["sample", "pair_pmid", "group", "pmid", "in_sample", "support_sentence", "claim",
           "population", "intervention", "comparison", "outcome", "direction",
           "f1_question", "f2_prompt", "f3_prompt", "claim_hedged", "verify_flags", "check_flags",
           "approved", "edited_claim", "edited_question", "abstract",
           "edited_direction", "review_note"]
# Columns the author fills in; the script never changes them once written.
AUTHOR_COLUMNS = ["approved", "edited_claim", "edited_question", "edited_direction",
                  "review_note"]
FINAL_PATH = PROCESSED / "claims_final.csv"
DIRECTIONS = {"HIGHER", "LOWER", "NO_DIFFERENCE"}

RETRACTION_LABEL = re.compile(
    r"^\s*(retracted|withdrawn)(\s+article)?\s*:\s*|\s*[\[(](retracted|retracted article|withdrawn)[\])]",
    re.IGNORECASE)
LEADING_WORDS = re.compile(r"\b(proven|really|still|known to|is it true)\b", re.IGNORECASE)
# Verbs that point to a direction; the F1 prompt forbids them.
DIRECTION_WORDS = re.compile(
    r"\b(reduc\w*|lower\w*|decreas\w*|increas\w*|rais\w*|improv\w*|worsen\w*|"
    r"prevent\w*|help\w*|benefit\w*|protect\w*)\b", re.IGNORECASE)
# Words kept lower case inside a title-cased journal name.
SMALL_WORDS = {"a", "an", "and", "as", "at", "de", "des", "du", "et", "for", "in", "la", "le",
               "of", "on", "or", "the", "to", "und", "with"}
STUDY_WORDS = re.compile(r"\b(study|studies|trial|trials|research|paper|researchers|journal)\b",
                         re.IGNORECASE)


def load_script(filename):
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s11 = load_script("11_generate_claims.py")


def metadata(pmids):
    """Template fields for each PMID from the cached PubMed XML."""
    out = {}
    for d in XML_DIRS:
        for path in sorted(d.glob("*.xml")):
            for a in ET.parse(path).getroot().iter("PubmedArticle"):
                pmid = a.findtext("MedlineCitation/PMID")
                if pmid not in pmids or pmid in out:
                    continue
                art = a.find("MedlineCitation/Article")
                title = "".join(art.find("ArticleTitle").itertext()).strip()
                first = art.find("AuthorList/Author")
                surname = ""
                if first is not None:
                    surname = first.findtext("LastName") or first.findtext("CollectiveName") or ""
                pub_date = art.find("Journal/JournalIssue/PubDate")
                year = (pub_date.findtext("Year") or (pub_date.findtext("MedlineDate") or "")[:4])
                out[pmid] = {"raw_title": title, "first_author": surname,
                             "raw_journal": art.findtext("Journal/Title", ""), "year": year,
                             "languages": [x.text for x in art.findall("Language")]}
    return out


def clean_title(title):
    cleaned = RETRACTION_LABEL.sub("", title).strip()
    label_removed = cleaned != title.strip()
    cleaned = cleaned.rstrip(".").strip()
    # PubMed puts the English translation of a non-English title in brackets.
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1].rstrip(".").strip()
    return cleaned, label_removed


def title_case(name):
    words = name.split()
    out = []
    for i, w in enumerate(words):
        if any(ch.isupper() for ch in w[1:]):        # keep acronyms such as BMC, PLoS
            out.append(w)
        elif 0 < i < len(words) - 1 and len(w) > 1 and w.lower() in SMALL_WORDS:
            out.append(w.lower())
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def clean_journal(journal):
    journal = re.sub(r"\s*\([^)]*\)", "", journal)   # e.g. "(Bethesda, Md. : 1985)"
    journal = journal.split(" = ")[0]                 # drop a parallel title
    journal = journal.split(":")[0].strip()           # drop subtitle after a colon
    return title_case(journal)


def latest_answers(papers):
    """Current-prompt answers for each paper, following step 11's done keys."""
    done = s11.already_done()
    extract_p = s11.load_prompt("extract_claim.txt")
    f1_p = s11.load_prompt("generate_f1.txt")
    verify_p = s11.load_prompt("verify_claim.txt")
    answers = {}
    for p in papers:
        ext = done.get(s11.done_key(p["pmid"], "extract_claim", extract_p, {"abstract": p["abstract"]}))
        f1 = verified = None
        if ext:
            pico = {f: ext[f] for f in ("population", "intervention", "comparison", "outcome")}
            f1 = done.get(s11.done_key(p["pmid"], "generate_f1", f1_p, pico))
            verified = done.get(s11.done_key(p["pmid"], "verify_claim", verify_p,
                                             s11.verify_values(ext, p)))
        answers[p["pmid"]] = (ext, f1, verified)
    return answers


def abstract_sources():
    """Full PubMed abstracts: retracted trials from pubmed_metadata.csv,
    controls from the PubMed records fetched when they were matched."""
    out = {}
    meta = pd.read_csv(PROCESSED / "pubmed_metadata.csv", dtype=str, keep_default_na=False)
    out.update(zip(meta["pmid"], meta["pm_abstract"]))
    for sample in ("pilot", "main"):
        c = pd.read_csv(PROCESSED / f"controls_{sample}.csv", dtype=str, keep_default_na=False)
        out.update(zip(c["control_pmid"], c["control_abstract"]))
    return out


def current_pmids():
    """PMIDs of the retracted trials and controls now in the samples."""
    out = set()
    for sample in ("pilot", "main"):
        out |= set(pd.read_csv(PROCESSED / f"sample_{sample}.csv", dtype=str)["pmid"])
        c = pd.read_csv(PROCESSED / f"controls_{sample}.csv", dtype=str, keep_default_na=False)
        out |= set(c["control_pmid"]) - {""}
    return out


def fill_script_columns(table):
    """Update script-owned columns. in_sample is recomputed on every run
    (papers replaced in step 10 become FALSE; their rows stay as a record);
    abstract is filled where empty. Author columns are never touched."""
    current = current_pmids()
    in_sample = table["pmid"].isin(current).map({True: "TRUE", False: "FALSE"})
    if "in_sample" in table:
        table["in_sample"] = in_sample
    else:
        table.insert(table.columns.get_loc("pmid") + 1, "in_sample", in_sample)
    if "abstract" not in table:
        table["abstract"] = ""
    missing = table["abstract"] == ""
    if missing.any():
        sources = abstract_sources()
        table.loc[missing, "abstract"] = table.loc[missing, "pmid"].map(sources).fillna("")
    return table


def final_value(table, edited, model):
    """The author's edit if there is one, otherwise the model's value."""
    return table[edited].where(table[edited].str.strip() != "", table[model]).str.strip()


def write_final(table):
    """Final claims for the experiment: papers now in the sample, with the
    author's edits applied. pair_ready is TRUE when both papers of the pair
    are approved."""
    t = table[table["in_sample"] == "TRUE"].copy()
    bad = t.loc[(t["edited_direction"] != "") & ~t["edited_direction"].isin(DIRECTIONS), "pmid"]
    if len(bad):
        sys.exit(f"edited_direction must be one of {sorted(DIRECTIONS)}: {bad.tolist()}")
    final = pd.DataFrame({
        "sample": t["sample"], "pair_pmid": t["pair_pmid"], "group": t["group"],
        "pmid": t["pmid"], "approved": t["approved"],
        "claim": final_value(t, "edited_claim", "claim"),
        "direction": final_value(t, "edited_direction", "direction"),
        "f1_question": final_value(t, "edited_question", "f1_question"),
        "f2_prompt": t["f2_prompt"], "f3_prompt": t["f3_prompt"],
        "claim_hedged": t["claim_hedged"],
    })
    approved_pairs = final.groupby("pair_pmid")["approved"].apply(lambda a: (a == "YES").sum() == 2)
    final["pair_ready"] = final["pair_pmid"].map(approved_pairs).map({True: "TRUE", False: "FALSE"})
    final.to_csv(FINAL_PATH, index=False)
    print(f"Wrote {FINAL_PATH.relative_to(ROOT)}: {len(final)} papers, "
          f"{final.loc[final['pair_ready'] == 'TRUE', 'pair_pmid'].nunique()} pairs ready")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which not in ("pilot", "main", "all"):
        sys.exit("Usage: python scripts/12_build_claims_review.py pilot|main|all")

    existing = (pd.read_csv(REVIEW_PATH, dtype=str, keep_default_na=False)
                if REVIEW_PATH.exists() else pd.DataFrame(columns=COLUMNS))
    existing = fill_script_columns(existing)
    for col in AUTHOR_COLUMNS:   # older tables may not have every author column
        if col not in existing:
            existing[col] = ""
    papers = [p for p in s11.load_papers(which) if p["pmid"] not in set(existing["pmid"])]

    meta = metadata({p["pmid"] for p in papers})
    answers = latest_answers(papers)
    f2 = (PROMPTS / "f2_paper_question.txt").read_text().strip()
    f3 = (PROMPTS / "f3_status_question.txt").read_text().strip()

    rows, missing = [], []
    for p in papers:
        ext, f1, verified = answers[p["pmid"]]
        if not ext or not f1 or not verified:
            missing.append(p["pmid"])
            continue
        m = meta[p["pmid"]]
        title, label_removed = clean_title(m["raw_title"])
        fields = {"title": title, "first_author": m["first_author"],
                  "journal": clean_journal(m["raw_journal"]), "year": m["year"]}
        question = f1["question"].strip()

        flags = []
        if label_removed:
            flags.append(f"retraction label removed from title: {m['raw_title']!r}")
        if m["languages"] and m["languages"] != ["eng"]:
            flags.append(f"non-English article ({', '.join(m['languages'])})")
        if ext["direction"] == "NOT_STATED":
            flags.append("direction NOT_STATED: no sentence states the direction")
        if DIRECTION_WORDS.search(question):
            flags.append("F1 uses a direction word")
        if not m["first_author"]:
            flags.append("no first author in PubMed")
        if ext["comparison"].strip().lower() == "baseline":
            flags.append("no comparison group (baseline)")
        if len(question.split()) > 30:
            flags.append(f"F1 has {len(question.split())} words (over 30)")
        if re.search(r"\d", question):
            flags.append("F1 contains a number")
        if STUDY_WORDS.search(question):
            flags.append("F1 mentions a study/trial/research")
        if LEADING_WORDS.search(question):
            flags.append("F1 contains leading wording")
        if m["first_author"] and re.search(rf"\b{re.escape(m['first_author'])}\b", question, re.IGNORECASE):
            flags.append("F1 contains the first author's name")
        if STUDY_WORDS.search(ext["claim"]) or re.search(r"\d", ext["claim"]):
            flags.append("claim mentions a study or a number")

        rows.append({
            "sample": p["sample"], "pair_pmid": p["pair_pmid"], "group": p["group"],
            "pmid": p["pmid"], "in_sample": "TRUE", "support_sentence": ext["support_sentence"],
            **{k: ext[k] for k in ("claim", "population", "intervention", "comparison",
                                   "outcome", "direction")},
            "f1_question": question,
            "f2_prompt": s11.fill(f2, fields), "f3_prompt": s11.fill(f3, fields),
            # Descriptive variable: the support sentence uses hedged wording.
            "claim_hedged": verified["hedged_language"],
            "verify_flags": "; ".join(
                f"{k} = {bad}" for k, bad in s11.VERIFY_CHECKS.items() if verified[k] == bad)
                + "".join(f" | {x}" for x in verified.get("problems", []) if x),
            "check_flags": "; ".join(flags),
            "approved": "", "edited_claim": "", "edited_question": "",
            "abstract": p["abstract"], "edited_direction": "", "review_note": "",
        })

    table = pd.concat([existing, pd.DataFrame(rows, columns=COLUMNS)], ignore_index=True)
    # Pilot rows first, then main; within each sample, rows still in the
    # sample first, then rows with verify flags, then by pair, the retracted
    # row before its control. Reordering keeps the author's entries.
    table = table.assign(
        _flag=table["verify_flags"].eq(""), _sample=table["sample"].ne("pilot"),
        _out=table["in_sample"].ne("TRUE"), _group=table["group"].ne("retracted"),
    ).sort_values(["_sample", "_out", "_flag", "pair_pmid", "_group"]).drop(
        columns=["_flag", "_sample", "_out", "_group"])
    table.to_csv(REVIEW_PATH, index=False)
    write_final(table)
    print(f"Added {len(rows)} rows to {REVIEW_PATH.relative_to(ROOT)} "
          f"(now {len(table)}); without step-11 answers: {len(missing)} {missing}")
    if rows:
        print(f"Rows with flags: {(pd.DataFrame(rows)['check_flags'] != '').sum()}")


if __name__ == "__main__":
    main()
