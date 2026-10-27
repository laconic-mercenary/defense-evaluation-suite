# Confidence calibration

Checks whether the confidence the judge reports with each grade matches how
often it is actually right. Produces a calibration curve and its expected
calibration error (ECE).

## Prerequisites

- Hand-labelled fixtures ([fixture calibration](fixture-calibration.md), steps 1–2).
- The judge reports a confidence value with every grade. Form TBD: a number
  0–100, or categories (low / medium / high).

## Steps

1. **Run** the judge on every fixture, K times. Record band and reported
   confidence per grade.
2. **Mark** each grade right or wrong against its label.
3. **Group** grades by reported confidence (boundaries TBD, e.g. 0–50,
   50–70, 70–90, 90–100).
4. **Accuracy per group:** number right ÷ number in the group.
5. **Compare** each group's accuracy with its average reported confidence.
   The gap is that group's calibration error; the weighted average of the
   gaps is the **ECE**.
6. **Check group sizes.** Small groups support no conclusion.
7. **Decide:**
   - Groups line up → confidence is meaningful and can be used (e.g. route
     low-confidence grades to human review).
   - Groups don't line up → ignore reported confidence.
8. **Re-run** on any judge change.

## Open questions

- Is the fixture count (~60 graded items) enough to fill each group?
- **Self-consistency** (how often the K repeats agree) is a confidence
  signal that doesn't rely on the model's self-report. How does it compare?
- Disagreement between two judges from different families: what does it
  tell you, and what should happen to those grades?
