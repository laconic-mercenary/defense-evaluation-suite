# Grading phishing-c2-beacon by hand

The automated judge reads `AGENTS.md` directly and grades one rubric entry
at a time. To grade this case by hand in a chat, give a model `AGENTS.md`'s
guidance plus the inputs below, and ask for the output below.

## Inputs

- The AUT's answers: `QUESTION_ANSWERS.md` (provided alongside this file
  for each grading run)
- The questions asked: the case's `EXAM.md` (paired repo:
  `forensic-agent-tests/cases/phishing-c2-beacon/EXAM.md`, or as pasted
  into this conversation)
- The true story: `BRIEFING.md` in this directory
- The scored rubric: `grading_schema.md` in this directory

## Output

Produce a per-question score (out of the schema's point value), a total
out of 100, and 2-3 sentences on whether the AUT correctly correlated
the two execution events without over-claiming lineage evidence that
isn't there, and whether it found the single outlier connection in Q4
rather than stopping at "a beacon exists."
