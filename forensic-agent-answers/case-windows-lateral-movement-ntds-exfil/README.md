# Grading windows-lateral-movement-ntds-exfil by hand

The automated judge reads `AGENTS.md` directly and grades one rubric entry
at a time. To grade this case by hand in a chat, give a model `AGENTS.md`'s
guidance plus the inputs below, and ask for the output below.

## Inputs

- The AUT's answers: `QUESTION_ANSWERS.md` (provided alongside this file
  for each grading run)
- The questions asked: the case's `EXAM.md` (paired repo:
  `forensic-agent-tests/cases/windows-lateral-movement-ntds-exfil/EXAM.md`,
  or as pasted into this conversation)
- The true story: `BRIEFING.md` in this directory
- The scored rubric: `grading_schema.md` in this directory
- Source PDF (for verification only, not for grading language):
  `supporting/log-analysis_handson_v2_advance_with_comment.pdf`

## Output

Produce a per-question score (out of the schema's point value), a total
out of 100, and 2-3 sentences on whether the AUT correctly reconstructed
the full attack path (Q7) without inventing unevidenced stages, and
whether it showed appropriate restraint on Q1/Q5 rather than overclaiming
certainty the data doesn't support.
