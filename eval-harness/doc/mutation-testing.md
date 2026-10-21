# Mutation testing

Checks whether the judge catches a single, known error. A generator writes a
`QUESTION_ANSWERS.md` that matches the rubric's expected answers, except for
one deliberate mutation, and the judge grades it.

The generator is a fixture tool, not an evaluation of the agent under test.

## Steps

1. **Choose** a mutation for a question, e.g. a wrong time, an invented
   action, the wrong user, a wrong identifier.
2. **Set the expected band** from the rubric before generating anything.
   Check its Zero conditions: one incorrect detail isn't always a Zero.
3. **Generate:** give a model the case's rubric and ask it to answer as the
   rubric's expected answers, with exactly that one mutation.
4. **Store** the file with the answer keys, recording the question, the
   mutation, the expected band, and the generator model and version.
5. **Grade** it with the judge and compare against the expected band.
6. **Repeat** across several iterations.

## Open questions

- **Generate once, or every run?** Regenerating changes the test inputs
  between calibration runs.
- **Who confirms the mutant?** Does the generator report the mutation it
  made, or does a person check the file contains that mutation and no other
  error?
- **Iterations:** the same mutation phrased differently, or different
  mutations? What does each tell you?
- **Mirror wording:** mutants echo the rubric's wording; real agent answers
  don't. How do you check the judge matches meaning, not wording?
- **Generator family:** does it matter if the generator is the same model
  family as the judge?
