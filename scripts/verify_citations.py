#!/usr/bin/env python3
"""
Check every knowledge-base entry in a prompt against the real publication record.

  python3 scripts/verify_citations.py                 # offline structure check only
  python3 scripts/verify_citations.py --online        # also resolve each DOI/PMID

Offline: each "### KBn" entry must have a Source line with a PMID or DOI, or be
marked [UNSOURCED].
Online (needs normal internet; PubMed and Crossref): the record found for each
PMID/DOI must match the entry's first-author surname and year. A mismatch or a
record that does not exist exits non-zero. Nothing here judges whether the
entry's *claim* matches the paper; read the paper for that.
"""
import argparse, json, re, sys, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = re.compile(r"^### (KB\d+)\b.*?(?=^### |\Z)", re.S | re.M)
DOI = re.compile(r"(?:doi:|doi\.org/)\s*(10\.\d{4,9}/[^\s,;)]+)", re.I)
PMID = re.compile(r"PMID\s*(\d{6,9})")


def entries(path):
    text = Path(path).read_text()
    for m in ENTRY.finditer(text):
        body = m.group(0)
        src = re.search(r"^Source:(.*?)(?=^Claim:|^Key claim:|\Z)", body, re.S | re.M)
        yield m.group(1), body, (src.group(1) if src else "")


def structure_problems(path):
    out = []
    for kb, body, src in entries(path):
        if "[UNSOURCED" in body or kb in ("KB6",):  # KB6 is a multi-source table, reviewed by hand
            continue
        if not (PMID.search(src) or DOI.search(src)):
            out.append("{}: no PMID or DOI in Source line".format(kb))
    return out


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "cycle-insights-verify"}), timeout=20) as r:
        return json.load(r)


def check_online(path):
    problems = []
    for kb, body, src in entries(path):
        first = re.match(r"\s*([A-Z][A-Za-z'\-]+)", src)
        year = re.search(r"\b(19|20)\d{2}\b", src)
        for pmid in PMID.findall(src):
            try:
                rec = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=" + pmid)["result"][pmid]
                names = " ".join(a["name"] for a in rec.get("authors", [])[:1])
                pub = rec.get("pubdate", "")
            except Exception as e:
                problems.append("{} PMID {}: not resolved ({})".format(kb, pmid, e)); continue
            if first and first.group(1).lower() not in names.lower():
                problems.append("{} PMID {}: first author {!r} does not match {!r}".format(kb, pmid, names, first.group(1)))
            if year and year.group(0) not in pub:
                problems.append("{} PMID {}: year {} vs record {}".format(kb, pmid, year.group(0), pub))
        for doi in DOI.findall(src):
            doi = doi.rstrip(".")
            try:
                rec = _get("https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]
                fam = " ".join(a.get("family", "") for a in rec.get("author", [])[:1])
                yr = str((rec.get("issued", {}).get("date-parts") or [[None]])[0][0])
            except Exception as e:
                problems.append("{} DOI {}: not resolved ({})".format(kb, doi, e)); continue
            if first and first.group(1).lower() not in fam.lower():
                problems.append("{} DOI {}: first author {!r} does not match {!r}".format(kb, doi, fam, first.group(1)))
            if year and year.group(0) != yr and yr != "None":
                problems.append("{} DOI {}: year {} vs record {}".format(kb, doi, year.group(0), yr))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", default=str(ROOT / "prompts" / "v3.3.md"))
    ap.add_argument("--online", action="store_true")
    a = ap.parse_args()
    problems = structure_problems(a.prompt_file)
    if a.online:
        problems += check_online(a.prompt_file)
    for p in problems:
        print("FAIL", p)
    print("{} entries checked, {} problems".format(len(list(entries(a.prompt_file))), len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
