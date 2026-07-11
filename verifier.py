"""
Legal Citation Verifier v0.1
============================
Takes a legal text (e.g., an AI-generated brief), extracts its case
citations, and checks each one against CourtListener's database of real
court opinions. Flags citations that don't exist.

Why this exists: courts across the US have sanctioned lawyers for filing
briefs with AI-hallucinated citations. This is the checker that should
have run first.

HOW TO RUN (see README.md for setup):
    python3 verifier.py sample_brief.txt

Pipeline:
    1. eyecite extracts citations from the text (Free Law Project's library)
    2. Each citation is POSTed to CourtListener's citation-lookup API
    3. Report: VERIFIED (found real case) / NOT FOUND (possible hallucination)
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests                      # pip install requests
from eyecite import get_citations   # pip install eyecite

LOOKUP_URL = "https://www.courtlistener.com/api/rest/v3/citation-lookup/"
LOG_FILE = "verification_log.jsonl"


def extract_citations(text):
    """
    Use eyecite to find citation strings like '576 U.S. 644'.
    Returns the list of full-case citations (skips short-form references
    like 'Id.' for v0.1 — a known limitation worth noting in the README).
    """
    citations = get_citations(text)
    full_cites = [c for c in citations if type(c).__name__ == "FullCaseCitation"]
    return full_cites


def lookup_text(text, api_token=None):
    """
    CourtListener's citation-lookup endpoint takes raw text and returns
    every citation it recognizes, each with matching real opinions (if any).
    An empty 'clusters' list for a citation = no real case found.

    Anonymous use is rate-limited; a free API token raises the limit.
    """
    headers = {}
    if api_token:
        headers["Authorization"] = f"Token {api_token}"
    resp = requests.post(LOOKUP_URL, data={"text": text}, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def build_report(lookup_results):
    """Turn API results into verdicts, one per citation found in the text."""
    report = []
    for item in lookup_results:
        clusters = item.get("clusters", [])
        if clusters:
            top = clusters[0]
            report.append({
                "citation": item.get("citation"),
                "verdict": "VERIFIED",
                "matched_case": top.get("case_name", "(name unavailable)"),
                "court_listener_url": "https://www.courtlistener.com" + top.get("absolute_url", ""),
            })
        else:
            report.append({
                "citation": item.get("citation"),
                "verdict": "NOT_FOUND",
                "matched_case": None,
                "note": "No real opinion matches this citation — possible hallucination.",
            })
    return report


def print_report(report):
    verified = [r for r in report if r["verdict"] == "VERIFIED"]
    not_found = [r for r in report if r["verdict"] == "NOT_FOUND"]

    print(f"\n{'CITATION':<28}{'VERDICT':<12}CASE")
    print("-" * 80)
    for r in report:
        case = r.get("matched_case") or r.get("note", "")
        print(f"{r['citation']:<28}{r['verdict']:<12}{case}")
    print("-" * 80)
    print(f"{len(report)} citations checked: "
          f"{len(verified)} verified, {len(not_found)} NOT FOUND.")
    if not_found:
        print("\n⚠  NOT FOUND citations must be manually confirmed before filing.")
        print("   (A missing match can also mean a very new case, a typo'd")
        print("   reporter, or database gaps — verify, don't assume.)")


def write_log(report, source_file):
    """Every check leaves a trail — same discipline as the expense agent."""
    stamp = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for r in report:
            f.write(json.dumps({"run_at": stamp, "source": source_file, **r}) + "\n")


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 verifier.py <textfile>")
    source = sys.argv[1]
    with open(source, encoding="utf-8") as f:
        text = f.read()

    token = os.environ.get("COURTLISTENER_API_TOKEN")  # optional, raises rate limit

    extracted = extract_citations(text)
    print(f"eyecite found {len(extracted)} full case citations in {source}")

    print("Checking against CourtListener...")
    results = lookup_text(text, api_token=token)
    report = build_report(results)
    print_report(report)
    write_log(report, source)
    print(f"\nLog appended to {LOG_FILE}")


if __name__ == "__main__":
    main()
