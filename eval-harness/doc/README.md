# Judge evaluation procedures

How to evaluate a judge before trusting its grades. Run these for every new
judge, and again whenever an existing judge changes (prompt, model, version,
reading rules, rubrics or fixtures).

| Procedure | Answers |
|---|---|
| [Fixture calibration](fixture-calibration.md) | Does the judge agree with hand-labelled grades, and with itself? |
| [Confidence calibration](confidence-calibration.md) | Does the judge's reported confidence mean anything? |
| [Mutation testing](mutation-testing.md) | Does the judge catch a single, known error in an otherwise correct answer? |

All fixtures, including generated ones, are answer keys in disguise. Store
them with `forensic-agent-answers/`, never where the agent under test can
read them.
