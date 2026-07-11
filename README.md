# Legal Citation Verifier

Checks the case citations in a legal text against [CourtListener](https://www.courtlistener.com)'s
database of real court opinions, and flags citations that don't exist.

**Why:** courts across the US have sanctioned lawyers for filing briefs containing
AI-hallucinated citations. Legal AI's most public failure mode is fabricated
authority that *looks* perfectly formatted. This tool is the check that should
run before anything gets filed.

Built as part of my ongoing work auditing AI systems that apply rules to facts —
see my companion project, an AI compliance auditor with a documented
failure catalog.

## How it works

1. **Extract** — [eyecite](https://github.com/freelawproject/eyecite) (Free Law
   Project's citation parser) finds citations like `576 U.S. 644` in the text
2. **Verify** — each citation goes to CourtListener's citation-lookup API,
   which returns matching real opinions (or nothing)
3. **Report** — `VERIFIED` with the real case name and link, or `NOT_FOUND` =
   possible hallucination, human must confirm
4. **Log** — every check appends to `verification_log.jsonl` (audit trail)

## Setup

```
pip3 install requests eyecite
python3 verifier.py sample_brief.txt
```

Optional: get a free API token at courtlistener.com (Profile → API) and
`export COURTLISTENER_API_TOKEN=...` for higher rate limits.

## Sample output

`sample_brief.txt` contains 4 real Supreme Court cases and 3 fabricated ones
(realistic-looking citations to cases that have never existed). The verifier
should verify the real four and flag the three fakes.

## Honest limitations (v0.1)

- Skips short-form citations (`Id.`, `supra`) — only full case citations checked
- `NOT_FOUND` ≠ proof of hallucination: could be a very new case, a typo'd
  reporter, or a database gap. The tool flags for human review; it doesn't accuse.
- Doesn't yet check whether a real case actually *says* what the brief claims
  (quote/holding verification — the harder and more interesting problem, planned next)
- CourtListener coverage is strongest for federal and appellate courts

## Roadmap

- [ ] Quote verification: does the cited case contain the quoted language?
- [ ] Holding check: retrieve opinion text, compare against the claimed proposition
- [ ] Failure catalog: document where the verifier itself fails (false alarms, misses)
