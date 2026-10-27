# Grading benign-breakglass-account by hand

The automated judge reads `AGENTS.md` directly and grades one rubric entry
at a time. To grade this case by hand in a chat, give a model `AGENTS.md`'s
guidance plus the inputs below, and ask for the output below.

## Inputs

- The AUT's answers: `QUESTION_ANSWERS.md` (provided alongside this file
  for each grading run)
- The questions asked: the case's `EXAM.md` (paired repo:
  `forensic-agent-tests/cases/benign-breakglass-account/EXAM.md`, or as
  pasted into this conversation)
- The true story: `BRIEFING.md` in this directory
- The scored rubric: `grading_schema.md` in this directory

## Output

Produce a per-question score (out of the schema's point value), a total
out of 100, and 2-3 sentences on whether the AUT reached "no incident"
through genuine verification (not a guess) and whether it correctly
separated the two unrelated off-hours patterns in Q3.
