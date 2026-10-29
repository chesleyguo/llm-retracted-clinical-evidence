"""Step 09: match each sampled retracted trial to one control trial.

Follows docs/analysis_plan.md, "Matched controls". For each trial in
data/processed/sample_main.csv, then data/processed/sample_pilot.csv:
- its MeSH major topics are read from the cached PubMed XML (step 07) and
  ordered most specific first (deepest MeSH tree number);
- PubMed is searched for clinical trials (randomized controlled trials only,
  if the retracted trial is one) with the same major topic, published
  within 1 year; candidates are put in random order (seed 2026) and the first
  one that passes every check is the control;
- if none is found, the rules are relaxed: level 2 = within 2 years, level 3 =
  within 2 years with the parent descriptor of each topic.

Every esearch / efetch response and the MeSH tree lookups are cached in
data/raw/pubmed_controls/ and data/raw/mesh/, so a re-run (or a resumed run
after an interruption) makes the same choices without new requests.

Writes data/processed/controls_main.csv, data/processed/controls_pilot.csv and
results/09_matching_log.txt. The controls are fixed once chosen, so the script
refuses to overwrite them.

Usage:
    python scripts/09_match_controls.py
"""

import hashlib
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
TRIAL_XML_DIR = RAW / "pubmed"
SEARCH_CACHE = RAW / "pubmed_controls" / "esearch"
FETCH_CACHE = RAW / "pubmed_controls" / "efetch"
MESH_CACHE = RAW / "mesh" / "descriptor_tree.json"
LOG_PATH = ROOT / "results" / "09_matching_log.txt"
# Append-only record of the random candidate order behind every chosen
# control, so a rejected control can be replaced by the next candidate in the
# same order (step 10).
DRAWS_PATH = PROCESSED / "control_draws.jsonl"
SAMPLES = [("main", PROCESSED / "sample_main.csv", PROCESSED / "controls_main.csv"),
           ("pilot", PROCESSED / "sample_pilot.csv", PROCESSED / "controls_pilot.csv")]

SEED = 2026
JOURNAL_CAP = 3
CHECK_BATCH = 20      # candidates fetched per efetch call while looking for a match
MAX_IDS = 9999        # esearch cannot page past this many results

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
MESH_SPARQL = "https://id.nlm.nih.gov/mesh/sparql"

# Same list as step 07 / analysis plan criterion 6.
TRIAL_TYPES = [
    "Clinical Trial", "Adaptive Clinical Trial", "Clinical Trial, Phase I",
    "Clinical Trial, Phase II", "Clinical Trial, Phase III", "Clinical Trial, Phase IV",
    "Controlled Clinical Trial", "Randomized Controlled Trial", "Equivalence Trial",
    "Human Challenge Trials", "Pragmatic Clinical Trial",
]
# Randomized controlled trial and its subtype (MeSH tree). A retracted RCT
# must be matched to an RCT (analysis plan, criterion 3a).
RCT_TYPES = ["Randomized Controlled Trial", "Equivalence Trial"]
# A control must carry none of these, as a publication type or as a linked
# notice (CommentsCorrections RefType).
# PubMed now labels retraction notices "Retraction Notice"; the older name
# "Retraction of Publication" is kept for the local check.
FLAG_TYPES = {"Retracted Publication", "Retraction of Publication", "Retraction Notice",
              "Expression of Concern", "Published Erratum"}
FLAG_LINKS = {"RetractionIn", "PartialRetractionIn", "ExpressionOfConcernIn", "ErratumIn"}

# Content rules for controls (analysis plan, criteria 7-9; added after the
# main-sample claims review).
HUMANS_UI = "D006801"   # MeSH descriptor "Humans"
NOT_A_RESULTS_PAPER_TITLE = re.compile(
    r"\b(study|trial) protocol\b"
    r"|\bprotocol (for|of) (a|an|the) (randomi[sz]ed|controlled|clinical|multicent|pragmatic|pilot|feasibility)"
    r"|design and rationale|rationale and design|statistical analysis plan"
    r"|\bmethodolog\w*|\bqualitative\b|\bmissing data\b|\bprobability model\b"
    r"|\bstatistical (method|model|approach)|\bsimulation study\b"
    r"|^(experiences|perceptions|views) of\b", re.IGNORECASE)
NOT_A_RESULTS_PAPER_ABSTRACT = re.compile(
    r"\b(this|the|our) (study |trial )?protocol (describes|will|is designed)"
    r"|\bwe will (recruit|randomi[sz]e|enrol|enroll|assess|evaluate|compare)\b"
    r"|\bwill be (randomi[sz]ed|recruited|enrolled|allocated)\b"
    r"|\bqualitative (study|analysis|interview|content analysis|research)\b"
    r"|\b(content|thematic|framework) analysis\b|\bsemi-structured interviews?\b"
    r"|\bfocus groups?\b", re.IGNORECASE)
# Section labels used only by protocols (e.g. BMJ Open).
PROTOCOL_SECTIONS = {"METHODS AND ANALYSIS", "ETHICS AND DISSEMINATION"}
# Sections that come before any results.
INTRO_SECTIONS = {"BACKGROUND", "INTRODUCTION", "OBJECTIVE", "OBJECTIVES", "AIM", "AIMS",
                  "PURPOSE", "CONTEXT", "IMPORTANCE", "RATIONALE"}
# Research-methods trials (criterion 10): the randomized intervention is a
# way of collecting data or running research (survey or questionnaire format,
# Delphi procedure, recruitment, consent, reminders), not a health
# intervention. "Response rate" alone is not used: it is a common clinical
# outcome (e.g. tumour response).
METHODS_TRIAL = re.compile(
    r"\bdelphi\b|\b(survey|questionnaire) response rates?\b|\bresponse rates? to (the |a )?(survey|questionnaire)"
    r"|\bsurvey (mode|method|format|design|administration)|\bmode of (questionnaire |survey )?(administration|data collection)"
    r"|\bquestionnaire (format|design|length|administration)\b|\b(rating|ranking) (versus|vs\.?) (ranking|rating)\b"
    r"|\bdata collection method|\b(study|trial) within a trial\b", re.IGNORECASE)
# These are often mentioned in passing in a health trial's abstract (e.g.
# "future trials should consider recruitment strategies"), so they count only
# in the title.
METHODS_TRIAL_TITLE = re.compile(
    r"\brecruitment (strateg|method)\w*|\bconsent (form|process|procedure)s?\b"
    r"|\breminder (letter|e-?mail|call|text)s?\b", re.IGNORECASE)

# An unstructured abstract counts as reporting results if it contains at
# least one of these.
RESULT_WORDS = re.compile(
    r"\bp\s*[<=>≤≥]|\bsignificant|\bno (significant )?difference|\bdid not differ"
    r"|\b(was|were) (higher|lower|similar|greater|smaller|reduced|increased|decreased|improved)"
    r"|\b(reduc|increas|decreas|improv|lower|higher)\w*|\bshowed\b|\bfound\b"
    r"|\d+(\.\d+)?\s*%", re.IGNORECASE)

# (level, years either side, use parent descriptors)
LEVELS = [(1, 1, False), (2, 2, False), (3, 2, True)]


# ------------------------------------------------------------------ requests

load_dotenv(ROOT / ".env")
API_KEY = os.getenv("NCBI_API_KEY")
BASE_PARAMS = {"tool": "llm-retracted-clinical-evidence",
               "email": os.getenv("CONTACT_EMAIL", "")}
if API_KEY:
    BASE_PARAMS["api_key"] = API_KEY
# NCBI allows 3 requests/second without a key and 10 with one.
PAUSE = 0.15 if API_KEY else 0.4


def cache_name(text):
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def post(url, data):
    """POST with retries on rate limits, server errors and dropped connections."""
    for attempt in range(1, 6):
        try:
            r = requests.post(url, data=data, timeout=120)
            r.content   # read the whole body here, so a cut-off response is retried
        except (requests.ConnectionError, requests.Timeout,
                requests.exceptions.ChunkedEncodingError):
            if attempt == 5:
                raise
            time.sleep(5 * attempt)
            continue
        time.sleep(PAUSE)
        if r.status_code == 200:
            return r
        if attempt == 5 or r.status_code not in (429, 500, 502, 503, 504):
            r.raise_for_status()
        time.sleep(PAUSE * 5 * attempt)


def write_new(path, content):
    """Write via .part and rename, so an interrupted run leaves no half file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_bytes(content)
    part.rename(path)


def esearch(query):
    """All PMIDs for a query, cached by query text."""
    path = SEARCH_CACHE / f"{cache_name(query)}.json"
    if not path.exists():
        r = post(EUTILS + "esearch.fcgi", {**BASE_PARAMS, "db": "pubmed", "term": query,
                                           "retmax": MAX_IDS, "retmode": "json"})
        result = r.json()["esearchresult"]
        # PubMed silently drops a phrase it cannot find. For a topic term that
        # would widen the search to every trial, so stop. A publication type
        # with no records (e.g. "Human Challenge Trials" today) is harmless:
        # it is one of several ORed types, and every candidate is re-checked
        # locally.
        missing = (result.get("errorlist", {}).get("phrasesnotfound", [])
                   + result.get("warninglist", {}).get("quotedphrasesnotfound", []))
        if "ERROR" in result or any(not m.endswith("[pt]") for m in missing):
            sys.exit(f"esearch problem for query {query!r}: {result}")
        record = {"query": query,
                  "searched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "count": int(result["count"]), "pmids": result["idlist"]}
        write_new(path, json.dumps(record, indent=1).encode())
    record = json.loads(path.read_text())
    if record["count"] > MAX_IDS:
        sys.exit(f"Query returns {record['count']} records, more than esearch can list: {query}")
    return record


def efetch(pmids):
    """PubMed XML for a list of PMIDs, cached by the list."""
    key = ",".join(pmids)
    path = FETCH_CACHE / f"{cache_name(key)}.xml"
    if not path.exists():
        r = post(EUTILS + "efetch.fcgi", {**BASE_PARAMS, "db": "pubmed",
                                          "retmode": "xml", "id": key})
        ET.fromstring(r.content)  # fail now if the XML is broken
        write_new(path, r.content)
    return ET.parse(path).getroot()


# ---------------------------------------------------------------- MeSH tree

def load_mesh_tree(uis):
    """Tree numbers and parent descriptors for each descriptor UI (cached)."""
    tree = json.loads(MESH_CACHE.read_text()) if MESH_CACHE.exists() else {}
    todo = sorted(set(uis) - set(tree))
    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        query = f"""
        PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
        PREFIX mesh: <http://id.nlm.nih.gov/mesh/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?d ?tn ?pd ?plabel FROM <http://id.nlm.nih.gov/mesh> WHERE {{
          VALUES ?d {{ {' '.join('mesh:' + u for u in chunk)} }}
          ?d meshv:treeNumber ?tn .
          OPTIONAL {{ ?tn meshv:parentTreeNumber ?ptn .
                     ?pd meshv:treeNumber ?ptn ; rdfs:label ?plabel . }}
        }}"""
        r = requests.get(MESH_SPARQL, params={"query": query, "format": "JSON"}, timeout=120)
        r.raise_for_status()
        for ui in chunk:
            tree[ui] = {"tree_numbers": [], "parents": {}}
        for row in r.json()["results"]["bindings"]:
            ui = row["d"]["value"].rsplit("/", 1)[1]
            tn = row["tn"]["value"].rsplit("/", 1)[1]
            if tn not in tree[ui]["tree_numbers"]:
                tree[ui]["tree_numbers"].append(tn)
            if "pd" in row:
                tree[ui]["parents"][row["pd"]["value"].rsplit("/", 1)[1]] = row["plabel"]["value"]
        time.sleep(PAUSE)
    if todo:
        MESH_CACHE.parent.mkdir(parents=True, exist_ok=True)
        MESH_CACHE.write_text(json.dumps(tree, indent=1, sort_keys=True))
    return tree


def depth(ui, tree):
    # Depth of the deepest tree number, e.g. E04.100.376.719.332 -> 5.
    return max((tn.count(".") + 1 for tn in tree[ui]["tree_numbers"]), default=0)


# ------------------------------------------------------------------ parsing

def major_topics(article):
    """[(UI, name)] of descriptors that are major topics (descriptor or a
    qualifier starred), the same definition as step 07."""
    out = []
    for heading in article.findall("MedlineCitation/MeshHeadingList/MeshHeading"):
        d = heading.find("DescriptorName")
        if d.get("MajorTopicYN") == "Y" or any(
                q.get("MajorTopicYN") == "Y" for q in heading.findall("QualifierName")):
            out.append((d.get("UI"), d.text))
    return out


def text_of(elem):
    return "".join(elem.itertext()).strip() if elem is not None else ""


def parse_candidate(article):
    citation = article.find("MedlineCitation")
    art = citation.find("Article")
    pub_types = [pt.text for pt in art.findall("PublicationTypeList/PublicationType")]
    links = {c.get("RefType") for c in citation.findall("CommentsCorrectionsList/CommentsCorrections")}
    doi = next((i.text for i in article.findall("PubmedData/ArticleIdList/ArticleId")
                if i.get("IdType") == "doi" and i.text), "")
    abstract = []
    sections = []   # (section names, text); names = label and NLM category
    for part in art.findall("Abstract/AbstractText"):
        label, text = part.get("Label"), text_of(part)
        abstract.append(f"{label}: {text}" if label else text)
        names = {(x or "").upper() for x in (label, part.get("NlmCategory"))} - {"", "UNASSIGNED"}
        sections.append((names, text))
    authors = []
    for a in art.findall("AuthorList/Author"):
        authors.append(a.findtext("CollectiveName") or
                       " ".join(x for x in (a.findtext("LastName"), a.findtext("Initials")) if x))
    pub_date = art.find("Journal/JournalIssue/PubDate")
    date = (pub_date.findtext("MedlineDate") or " ".join(
        x for x in (pub_date.findtext(k) for k in ("Year", "Month", "Day")) if x)) if pub_date is not None else ""
    return {
        "pmid": citation.findtext("PMID"),
        "doi": doi.strip().lower(),
        "title": text_of(art.find("ArticleTitle")),
        "abstract": "\n".join(abstract),
        "journal": art.findtext("Journal/Title", ""),
        "pub_date": date,
        "authors": "; ".join(authors),
        "pub_types": pub_types,
        "flag_links": links & FLAG_LINKS,
        "major_uis": {ui for ui, _ in major_topics(article)},
        "mesh_uis": {d.get("UI") for d in
                     citation.findall("MeshHeadingList/MeshHeading/DescriptorName")},
        "abstract_sections": sections,
        "mesh_major": "; ".join(name for _, name in major_topics(article)),
    }


def trial_records(pmids):
    """Cached step-07 PubMed records for the sampled trials."""
    found = {}
    for path in sorted(TRIAL_XML_DIR.glob("efetch_*.xml")):
        for article in ET.parse(path).getroot().iter("PubmedArticle"):
            pmid = article.findtext("MedlineCitation/PMID")
            if pmid in pmids:
                found[pmid] = article
    return found


# ----------------------------------------------------------------- matching

def build_query(term, field, year, window, require_rct):
    types = " OR ".join(f'"{t}"[pt]' for t in (RCT_TYPES if require_rct else TRIAL_TYPES))
    flags = " OR ".join(f'"{t}"[pt]' for t in sorted(FLAG_TYPES))
    return (f'"{term}"[{field}] AND ({types}) AND {year - window}:{year + window}[dp] '
            f"AND hasabstract NOT ({flags})")


def content_problem(c):
    """Content rules every control must meet (criteria 7-10), or None."""
    if HUMANS_UI not in c["mesh_uis"]:
        return "MeSH has no Humans"
    if "Clinical Trial Protocol" in c["pub_types"]:
        return "protocol, methods or qualitative paper"
    if NOT_A_RESULTS_PAPER_TITLE.search(c["title"]) or NOT_A_RESULTS_PAPER_ABSTRACT.search(c["abstract"]):
        return "protocol, methods or qualitative paper"
    if (METHODS_TRIAL.search(c["title"]) or METHODS_TRIAL.search(c["abstract"])
            or METHODS_TRIAL_TITLE.search(c["title"])):
        return "research-methods trial"
    sections = [(names, text) for names, text in c["abstract_sections"] if names]
    all_names = set().union(*(n for n, _ in sections)) if sections else set()
    if all_names & PROTOCOL_SECTIONS:
        return "protocol, methods or qualitative paper"
    if any("RESULT" in x or "FINDING" in x for x in all_names):
        return None
    # No results section (or an unstructured abstract): look for result
    # wording outside the introductory sections.
    text = " ".join(t for n, t in c["abstract_sections"] if not n & INTRO_SECTIONS)
    if not RESULT_WORDS.search(text):
        return "abstract reports no results"
    return None


def why_not(c, ctx):
    """Reason a candidate fails, or None if it is eligible. Order is fixed so
    the log counts are comparable."""
    if not set(c["pub_types"]) & set(TRIAL_TYPES):
        return "not a trial"
    if ctx["require_rct"] and not set(c["pub_types"]) & set(RCT_TYPES):
        return "not an RCT (retracted trial is an RCT)"
    if not c["abstract"]:
        return "no abstract"
    if set(c["pub_types"]) & FLAG_TYPES or c["flag_links"]:
        return "PubMed retraction/concern/erratum marker"
    if c["pmid"] in ctx["rw_pmids"] or (c["doi"] and c["doi"] in ctx["rw_dois"]):
        return "in Retraction Watch"
    problem = content_problem(c)
    if problem:
        return problem
    if c["pmid"] in ctx["used"]:
        return "already a control"
    if ctx["journals"][c["journal"]] >= JOURNAL_CAP:
        return "journal cap"
    if ctx["exact_ui"] and ctx["exact_ui"] not in c["major_uis"]:
        return "topic not a major topic"
    # The [dp] search also matches the electronic publication date, so check
    # the window again on the journal-issue year, the same field used for the
    # retracted trial.
    if abs(int(c["pub_date"][:4]) - ctx["year"]) > ctx["window"]:
        return "publication year outside window"
    return None


def find_control(pmids, rng, ctx, order=None, start=0):
    """Check candidates in random order, from position `start`; return
    (control, position of the control in the order, order). A given `order`
    (a recorded one) is used instead of drawing a new one."""
    if order is None:
        order = [str(p) for p in rng.permutation(sorted(pmids, key=int))] if pmids else []
    for i in range(start, len(order), CHECK_BATCH):
        batch = order[i:i + CHECK_BATCH]
        records = {a.findtext("MedlineCitation/PMID"): parse_candidate(a)
                   for a in efetch(batch).iter("PubmedArticle")}
        for j, pmid in enumerate(batch):  # keep the random order, not the order returned
            c = records.get(pmid)
            reason = "not returned by efetch" if c is None else why_not(c, ctx)
            ctx["rejections"][reason or "chosen"] += 1
            if reason is None:
                return c, i + j, order
    return None, None, order


def topic_plan(article, tree):
    """Topics to try at each level: own major topics most specific first, then
    their parent descriptors (deduplicated) most specific first."""
    own = sorted(set(major_topics(article)), key=lambda t: (-depth(t[0], tree), t[1]))
    parents = {}
    for ui, _ in own:
        for pui, pname in tree[ui]["parents"].items():
            parents[pui] = pname
    parent_list = sorted(parents.items(), key=lambda t: (-depth(t[0], tree), t[1]))
    return own, [p for p in parent_list if p[0] not in {u for u, _ in own}]


def load_rw_ids():
    """PMIDs and DOIs that appear anywhere in the Retraction Watch snapshot."""
    rw_path = sorted(RAW.glob("retraction_watch_*.csv"))[-1]
    rw = pd.read_csv(rw_path, dtype=str, keep_default_na=False)
    # Any appearance in Retraction Watch excludes a candidate, whatever the
    # record type (retraction, correction, expression of concern, ...).
    rw_pmids = set(rw["OriginalPaperPubMedID"].str.strip()) - {"", "0"}
    rw_dois = set(rw["OriginalPaperDOI"].str.strip().str.lower()) - {"", "unavailable"}
    return rw_path, rw_pmids, rw_dois


def match_trial(trial, article, tree, rng, ctx_base, resume=None):
    """Find a control for one retracted trial, trying the levels in order.
    ctx_base holds the shared state (used controls, journal counts, ...); a
    chosen control is added to it.

    resume (step 10, rejected control): a recorded draw with keys level,
    topic_ui, order and chosen_index. The search continues after the chosen
    candidate in that recorded order, then with the topics and levels that
    come after it, exactly as the original search would have gone on."""
    year = int(trial["pm_pub_date"][:4])
    require_rct = bool(set(RCT_TYPES) & set(trial["pm_pub_types"].split("; ")))
    own, parents = topic_plan(article, tree) if article is not None else ([], [])
    result = {"pmid": trial["pmid"], "stratum": trial["stratum"],
              "retracted_year": year, "retracted_is_rct": require_rct,
              "match_level": "NONE"}
    skipping = resume is not None
    for level, window, use_parent in LEVELS:
        topics = parents if use_parent else own
        for ui, term in topics:
            # When resuming, skip the topics tried before the recorded one.
            if skipping and (level, ui) != (resume["level"], resume["topic_ui"]):
                continue
            # Own topics: exact descriptor (noexp). Parents: exploded, so any
            # descriptor under the parent counts.
            field = "majr" if use_parent else "majr:noexp"
            query = build_query(term, field, year, window, require_rct)
            search = esearch(query)
            ctx = {**ctx_base, "require_rct": require_rct,
                   "exact_ui": None if use_parent else ui,
                   "year": year, "window": window}
            if skipping:
                skipping = False
                control, pos, order = find_control(search["pmids"], rng, ctx, order=resume["order"],
                                                   start=resume["chosen_index"] + 1)
            else:
                control, pos, order = find_control(search["pmids"], rng, ctx)
            if control:
                ctx_base["used"].add(control["pmid"])
                ctx_base["journals"][control["journal"]] += 1
                result.update({
                    "match_level": level, "matched_topic_ui": ui,
                    "matched_topic": term, "topic_depth": depth(ui, tree),
                    "n_search_results": search["count"], "n_checked": pos + 1,
                    "query": query, "searched_at_utc": search["searched_at_utc"],
                    "control_pmid": control["pmid"],
                    "control_year_diff": int(control["pub_date"][:4]) - year,
                    "control_title": control["title"],
                    "control_abstract": control["abstract"],
                    "control_journal": control["journal"],
                    "control_pub_date": control["pub_date"],
                    "control_authors": control["authors"],
                    "control_doi": control["doi"],
                    "control_pub_types": "; ".join(control["pub_types"]),
                    "control_mesh_major": control["mesh_major"],
                    # Popped by the caller and written to DRAWS_PATH.
                    "_draw": {"level": level, "topic_ui": ui, "topic": term, "query": query,
                              "order": order, "chosen_index": pos},
                })
                return result
    if skipping:
        raise ValueError(f"Recorded topic {resume['topic_ui']} (level {resume['level']}) "
                         f"is not among the topics of {trial['pmid']}.")
    result["note"] = "no MeSH major topics" if not own else "no eligible control at any level"
    return result


def append_draw(result, sample, source):
    """Move the candidate order out of a match result into DRAWS_PATH."""
    draw = result.pop("_draw", None)
    if draw is None:
        return
    record = {"sample": sample, "retracted_pmid": result["pmid"],
              "control_pmid": result["control_pmid"], "source": source,
              "recorded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              **draw}
    with open(DRAWS_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def latest_draw(retracted_pmid, control_pmid):
    """The most recent recorded draw that chose this control for this trial."""
    found = None
    if DRAWS_PATH.exists():
        with open(DRAWS_PATH) as f:
            for line in f:
                r = json.loads(line)
                if (r["retracted_pmid"], r["control_pmid"]) == (retracted_pmid, control_pmid):
                    found = r
    return found


def main():
    for _, _, out_path in SAMPLES:
        if out_path.exists():
            sys.exit(f"{out_path.relative_to(ROOT)} already exists; controls are fixed once chosen.")

    rw_path, rw_pmids, rw_dois = load_rw_ids()

    samples = {name: pd.read_csv(path, dtype=str, keep_default_na=False).sort_values(
        "draw_order", key=lambda s: s.astype(int)) for name, path, _ in SAMPLES}
    all_pmids = set().union(*(s["pmid"] for s in samples.values()))
    articles = trial_records(all_pmids)
    tree = load_mesh_tree({ui for a in articles.values() for ui, _ in major_topics(a)})
    tree = load_mesh_tree({p for ui in list(tree) for p in tree[ui]["parents"]})

    rng = np.random.default_rng(SEED)
    used = set()
    log = [f"Seed: {SEED} (numpy {np.__version__}, default_rng)",
           f"Retraction Watch snapshot: {rw_path.name}",
           f"Run at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}"]
    rejections = Counter()

    for name, _, out_path in SAMPLES:
        journals = Counter()
        rows = []
        for _, trial in samples[name].iterrows():
            ctx_base = {"rw_pmids": rw_pmids, "rw_dois": rw_dois, "used": used,
                        "journals": journals, "rejections": rejections}
            result = match_trial(trial, articles.get(trial["pmid"]), tree, rng, ctx_base)
            append_draw(result, name, "step 09")
            print(f"  {name} {trial['pmid']}: level {result['match_level']}")
            rows.append(result)

        out = pd.DataFrame(rows)
        out["control_year_diff"] = out["control_year_diff"].astype("Int64")
        out.to_csv(out_path, index=False)
        matched = out[out["match_level"] != "NONE"]
        log += ["", f"== {name} sample: {len(out)} retracted trials ==",
                "Match level used:"]
        log += [f"  {lvl}: {n}" for lvl, n in out["match_level"].astype(str).value_counts().sort_index().items()]
        if "note" in out:
            for _, r in out[out["match_level"] == "NONE"].iterrows():
                log.append(f"  unmatched {r['pmid']}: {r['note']}")
        log.append(f"Year difference (control - retracted): "
                   f"{dict(sorted((int(k), n) for k, n in Counter(matched['control_year_diff']).items()))}")
        jc = Counter(matched["control_journal"])
        log.append(f"Control journals: {len(jc)} distinct; trials per journal: "
                   f"{dict(sorted(Counter(jc.values()).items()))}")
        log += [f"  {n}  {j}" for j, n in jc.most_common() if n > 1]

    log += ["", "Candidates checked, by outcome (all samples):"]
    log += [f"  {n:>6}  {k}" for k, n in rejections.most_common()]
    LOG_PATH.write_text("\n".join(log) + "\n")
    print("\n".join(log))
    print(f"\nSaved controls and {LOG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
