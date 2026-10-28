"""Step 05: look up PubMed publication types for the duplicate-title PMIDs.

Reads the PMIDs in data/processed/duplicate_title_review.csv, fetches their
PubMed records with E-utilities (efetch, XML), saves the raw XML to
data/raw/pubmed_duplicate_titles_<YYYY-MM-DD>.xml, and fills the column
pubmed_pub_types with the publication types exactly as PubMed lists them,
joined by "; ".

Only pubmed_pub_types is written; all other columns, including the manual
ones, are left as they are. If a raw XML file already exists it is reused
instead of querying PubMed again.

Usage:
    python scripts/05_fetch_duplicate_title_pubtypes.py
"""

import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
TABLE_PATH = ROOT / "data" / "processed" / "duplicate_title_review.csv"
RAW_DIR = ROOT / "data" / "raw"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def main():
    table = pd.read_csv(TABLE_PATH, dtype=str, keep_default_na=False)
    pmids = sorted(set(table["pmid"]), key=int)
    print(f"PMIDs to look up: {len(pmids)}")

    existing = sorted(RAW_DIR.glob("pubmed_duplicate_titles_*.xml"))
    if existing:
        raw_path = existing[-1]
        print(f"Using existing {raw_path.relative_to(ROOT)}")
    else:
        load_dotenv(ROOT / ".env")
        params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml",
                  "tool": "llm-retracted-clinical-evidence",
                  "email": os.getenv("CONTACT_EMAIL", "")}
        if os.getenv("NCBI_API_KEY"):
            params["api_key"] = os.getenv("NCBI_API_KEY")
        r = requests.get(EFETCH_URL, params=params, timeout=60)
        r.raise_for_status()
        raw_path = RAW_DIR / f"pubmed_duplicate_titles_{datetime.now(timezone.utc):%Y-%m-%d}.xml"
        raw_path.write_bytes(r.content)
        print(f"Saved {raw_path.relative_to(ROOT)}")

    pub_types = {}
    for article in ET.parse(raw_path).getroot().iter("PubmedArticle"):
        pmid = article.findtext("MedlineCitation/PMID")
        pub_types[pmid] = "; ".join(
            pt.text for pt in article.iter("PublicationType"))
    missing = [p for p in pmids if p not in pub_types]
    print(f"Records returned: {len(pub_types)}; missing: {missing or 'none'}")

    table["pubmed_pub_types"] = table["pmid"].map(pub_types).fillna("NOT_FOUND")
    table.to_csv(TABLE_PATH, index=False)
    print(f"Updated pubmed_pub_types in {TABLE_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
