# Fixture calibration

Checks whether the judge agrees with hand-labelled grades (validity, R6) and
with itself across repeats (reliability, R2).

## Steps

1. **Fixtures:** real agent answers plus fake ones written to hit each band,
   each Zero condition, a no-band-fits case, an overlap case, a true detail
   BRIEFING doesn't mention, an injection attempt, and odd layouts. Store
   them with the answer keys: a perfect fake answer *is* an answer key.
2. **Label** each question's band by hand before seeing the judge's output,
   applying the same reading rules, with an R5-style rationale. A second
   labeller is optional; their disagreements point at ambiguous rubrics.
3. **Split:** hold some fixtures back; tune the prompt only on the rest.
4. **Run** every fixture K times, recording the judge version.
5. **Measure:** agreement with labels, consistency across repeats, error
   direction (too lenient vs too strict), quote-check failures.
6. **Decide:** pass or fail. On failure, fix the judge, the label, or send
   the rubric to the case authors.
7. **Re-run** on any change to prompt, model, reading rules, rubric or
   fixtures.
8. **Spot-check** a random live grade per batch; disagreements become
   fixtures.

## Parameters

TBD after the first calibration run: thresholds, K, fixture count,
held-back share, spot-check rate. Pilot case: `rdp-remote-file-write`.
