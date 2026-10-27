# Grading rogue-service-account-privcreep by hand

The automated judge reads `AGENTS.md` directly and grades one rubric entry
at a time. To grade this case by hand in a chat, give a model `AGENTS.md`'s
guidance plus the inputs below, and ask for the output below.

## Inputs

- The AUT's answers: `QUESTION_ANSWERS.md` (provided alongside this file
  for each grading run)
- The questions asked: the case's `EXAM.md` (paired repo:
  `forensic-agent-tests/cases/rogue-service-account-privcreep/EXAM.md`,
  or as pasted into this conversation)
- The true story: `BRIEFING.md` in this directory
- The scored rubric: `grading_schema.md` in this directory

## Output

Produce a per-question score (out of the schema's point value), a total
out of 100, and 2-3 sentences on whether the AUT correctly distinguished
legitimate `svc-reportgen` usage from the attacker's (Q1/Q2), and
whether it identified the explicit-credentials event — not the
group-add — as the earliest actionable anomaly (Q4).
