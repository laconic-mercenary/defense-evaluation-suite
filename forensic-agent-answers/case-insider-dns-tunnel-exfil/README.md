# Grading insider-dns-tunnel-exfil by hand

The automated judge reads `AGENTS.md` directly and grades one rubric entry
at a time. To grade this case by hand in a chat, give a model `AGENTS.md`'s
guidance plus the inputs below, and ask for the output below.

## Inputs

- The AUT's answers: `QUESTION_ANSWERS.md` (provided alongside this file
  for each grading run)
- The questions asked: the case's `EXAM.md` (paired repo:
  `forensic-agent-tests/cases/insider-dns-tunnel-exfil/EXAM.md`, or as
  pasted into this conversation)
- The true story: `BRIEFING.md` in this directory
- The scored rubric: `grading_schema.md` in this directory

## Output

Produce a per-question score (out of the schema's point value), a total
out of 100, and 2-3 sentences on whether the AUT correctly identified
the DNS tunnel (not just "unusual DNS activity") as the exfiltration
mechanism, and whether it avoided both under-reporting ("nothing
happened, no compromised account") and over-reporting (fabricating an
attacker) in Q4.
