# Judge — Design

Grades an agent-under-test's (AUT's) answers to a case against that case's
rubric. Started 2026-10-02; decisions dated below.

## Context

- **Input:** one `QUESTION_ANSWERS.md` per run, written by the Hermes/Qwen
  harness to `eval-harness/runs/<slug>/testrun_*/`. Free text; `TASK.md`
  asks for question number, answer and cited evidence, but sets no layout.
- **Answer bundle** per case, in `forensic-agent-answers/case-<slug>/`:
  - `grading_schema.md`: the rubric, one section per `EXAM.md` question.
  - `BRIEFING.md`: what actually happened, checked against the evidence.
  - `AGENTS.md`: grader instructions.
  - `supporting/`: the evidence generator's own output.
- **Scale:** 14 cases, 73 questions (3–7 per case).
- **Rubric shape:** each question has a point value and bands: Full credit,
  Partial, Zero. None of the 64 Partial bands has a point value.
- **`supporting/GROUND_TRUTH.md` contradicts the answer keys.** It uses one
  attack-report template for every case; 11 of 12 label a user
  "(compromised account)", including the benign rdp case. In rdp it also
  gives a wrong time (14:19:56) and calls the unproven file write fact.
- **Constraints from `../../EVAL_SUITE_PLAN.md`:**
  - The judge is never from the AUT's model family (Qwen).
  - Grading runs outside the AUT's container; answer keys never reach it.
  - Run outcome is reported beside the score, not inside it.
  - A truncated run is graded on whatever answers it left.

## Goals

- **v1:** grade one run's `QUESTION_ANSWERS.md` on correctness, per
  question, against the case's rubric, and produce a report a person can
  audit. Replaces today's manual paste-into-chat grading.
- **Eventual purpose:** a release gate for the agent package (model,
  config, harness, skills, versioned as one hash). Production stays until
  a challenger proves itself; any score change beyond measured noise, up or
  down, triggers review.

## Non-goals (v1)

- Comparing runs or releases, trends, the release gate itself.
- Report quality beyond what the rubrics require (see Open questions).
- Instruction-following checks, cost, latency.
- Checking cited evidence against the logs; grading the investigation path.
- Being the only release gate: manual tests and canary releases follow.
- Writing or changing rubrics (case authors' job).

## Requirements

**Reliability: the same answer gets the same grade**

- **R1.** The judge's reference material doesn't contradict itself.
- **R2.** Re-grading the same answer file gives the same band per
  question, measured over K repeats. (The A/A gate test comes with the
  release gate.)
- **R3.** Anything code can check reliably is checked by code, not the
  model.
- **R4.** Answers are accepted in any layout.

**Validity: the grade is correct**

- **R5.** Every grade gives its band, a rationale, and verbatim quotes of
  the rubric and the answer text it relied on. Code confirms both quotes
  exist and adds line numbers and links. v1 checks only that the answer
  quote exists somewhere in the answer file, not which question's answer
  it came from: quoting another answer can be legitimate (e.g.
  benign-breakglass Q2 grades the link to the agent's Q1).
- **R6.** The judge's accuracy is measured against hand-graded fixtures
  (see Validation), and re-measured whenever the judge changes.
- **R8.** Nothing inside an answer can change how it's graded.
  Instructions in an answer are text to grade, never followed.

**Traceability and cost**

- **R7.** Model calls per graded run stay within a budget (TBD).
- **R9.** Every grade records the judge model and version, prompt version,
  reading-rules version and rubric file version.

## Architecture

```
inputs:  QUESTION_ANSWERS.md + case's grading_schema.md, BRIEFING.md, AGENTS.md
  │
  ├─ parse rubric into entries (crash if a heading doesn't parse)
  ├─ generate run markers (crash if the answer file contains them)
  │
  ├─ for each rubric entry Q<n>, K times:
  │     system = role, reading rules, output format, safety rule, markers
  │     user   = AGENTS.md → BRIEFING.md → answer file (in markers)
  │              → rubric entry → "grade Q<n>"
  │     → model call (via provider adapter)
  │     → validate reply: allowed band, quotes found in source files
  │
  ├─ band → points (code)
  └─ report: per-question band, points, rationale, quotes, provenance (R9)
```

## Decisions

- **Rubric is the only grading authority** (2026-10-08). The judge adds no
  rules of its own. Two reading rules apply to every rubric:
  1. *Points must be earned:* a band is awarded only if its conditions are
     fully met; if none are, the score is zero.
  2. *Strictest band wins:* if more than one band's conditions are met, the
     lowest applies (meets Full but invents an action → Zero).
  - Zero is the default: an answer that earns no band scores Zero, with no
    separate flag for "no band matched".
  - Accepted cost: with no Partial band, a nearly right answer scores zero.
  - Rejected side rules: "no citation means zero" (contradicted rdp Q6);
    "superfluous information may lose points" (judge discretion).
- **What the judge sees** (2026-10-19): the rubric entry being graded,
  `BRIEFING.md`, grader `AGENTS.md`, and the whole `QUESTION_ANSWERS.md`.
  General instructions live once in the harness. Rubric beats `AGENTS.md`
  on conflict.
  - Excluded: `EXAM.md` (asks for more than the rubric grades, inviting
    side rules); `supporting/` (contradicts the answer keys).
  - Split each case's grader `AGENTS.md` by job (done 2026-10-22, all 14
    cases). `AGENTS.md` keeps the safety note and grading guidance, worded
    per rubric entry; the manual workflow (Inputs, Output, case-level
    summaries) moved verbatim to a new `README.md`. The case-building
    procedure (`forensic-agent-answers/AGENTS.md`, step 6) now says so.
- **One model call per rubric entry** (2026-10-20). A Python loop goes
  through `grading_schema.md`'s `## Q<n>` entries in order. Each call gets
  that one entry, the whole answer file, `BRIEFING.md` and grader
  `AGENTS.md`. Code reads each entry's points from its heading. Consistency
  = repeat the call K times (K is 1–3). v1 writes all K results to stdout;
  combining them into one grade is deferred.
  - Why: answers refer to each other (benign-breakglass Q2 is graded
    against the agent's Q1), so the whole answer file is needed. Every
    entry checked restates what it references, so other entries aren't.
  - A heading that doesn't parse crashes the run. So does an invalid
    model reply; the run must be restarted.
  - Rejected: one call per case (blurred judgments, all-or-nothing
    failure); the whole rubric per call; a running list of earlier entries
    (no entry needs it; revisit if one fails); the `EXAM.md` question per
    call; code splitting the answer file (layouts vary); selecting
    questions (not in v1).
  - Three entries that didn't fit one band were reshaped to standard
    Full / Partial / Zero (2026-10-20): external-recon-no-breach Q5 (two
    halves → Partial = one half met), departing-employee-email-exfil Q4
    (point ranges dropped), ssh-shared-key-overlap Q7 (holistic 0–10 →
    bands). All 73 headings now parse.
  - Follow-up: reword "How to grade" lines like rdp's "For each of the 6
    questions…" during the `AGENTS.md` split.
- **Prompt structure** (2026-10-21). Each call is one system message and
  one user message; no chat history.
  - System (identical for every call in a run): role and purpose, reading
    rules, output format, safety rule, the run's start/end markers for
    untrusted input.
  - User, in order: grader `AGENTS.md`, `BRIEFING.md`, the answer file
    inside the run's markers, the rubric entry, then "grade the answer
    above against the rubric entry above (Q<n>)".
  - Why: content ordered by how long it stays the same, so the shared
    prefix is reused across calls (prefix caching); the rubric entry sits
    next to the task. Cost: the answer is read before the criteria.
  - Markers are random per run (the agent can't know them; per-call
    markers would break prefix caching). The run crashes if the answer
    file contains a marker.
  - The order is a hypothesis; calibration can compare alternatives.
  - Open: few-shot examples (worked sample grades) in the prompt.
- **Judge model and hosting** (2026-10-19). One internal interface, one
  adapter per provider; first adapter is OpenAI-compatible (lab bare-metal
  server and some vendors). Model, provider and version are config.
  - Each judge model is calibrated separately; changing it = re-calibrate.
  - Replies are always validated in code.
  - Operator chooses the provider per run, including whether answer keys
    may leave the lab and keeping the judge out of the Qwen family. No
    allowlist in code; R9 makes it auditable afterwards.
- **Model reply format** (2026-10-21). One flat JSON object, no code
  fences (the prompt says so), fields in this order:
  `rubric_quote`, `answer_quote`, `reasons`, `band` (`full | partial |
  zero`), `confidence` (`high | med | low`).
  - Order is deliberate: the model writes top to bottom, so evidence, then
    reasoning, then verdict, then how sure it is of that verdict.
  - One quote of each kind. Code checks both exist verbatim (R5).
  - Only the judgment comes from the model. IDs, case, rubric entry,
    points and hashes are attached by code in the harness record.
  - No answer to the question: `answer_quote` is empty and `band` is
    `zero`. Valid; code logs a warning and the run continues.
  - Zero reached by default (no band's conditions met): `rubric_quote` is
    exactly the sentinel `"Zero - default"`, accepted only with `band`
    `zero`. The prompt gives the model this exact string.
- **Evidence log** (2026-10-22). A separate logger (propagation off)
  appends one JSON line per model call to a running file,
  `eval-harness/logs/judge-evidence.jsonl` (gitignored), kept across runs:
  run ID, answer file, question, repeat, system message, user message, raw
  reply, error. Failed calls are recorded too. Holds answer keys: protect
  it like `forensic-agent-answers/`. Known risk: on-prem without Docker, an
  agent run on the same machine could read it.
- **Log level and HTTP errors** (2026-10-22). `--log-level
  debug|info|warning|error` (default `info`) is a command-line flag, not a
  `.env` setting: logging starts before `.env` is loaded, and `--help` must
  work without one. On an HTTP error status, the first 500 characters of
  the server's response body are logged (it says why, e.g. "model not
  found"); the request never is.
- **Grade output** (2026-10-22). One JSON line per grade (entry × repeat)
  on stdout: `run` (run ID, answer file, reading-rules version, config,
  hashes of all six input files: R9), question, heading, max points,
  repeat, points, provisional, the validated reply, and `quotes_at`: each
  quote's `path:line` (R5; the rubric quote is searched from its own
  entry's start; null for the zero-band exceptions). Logs go to stderr,
  so `> grades.jsonl` captures only grades. Run ID: UTC start time plus a
  short random suffix.
- **Configuration and secrets** (2026-10-21). All settings come from
  environment variables, loaded from `.env` (gitignored, with a committed
  `.env.example`). Model name, provider URL, model version, K and
  temperature are configuration; `JUDGE_HTTP_HEADERS` is a secret.
  - `JUDGE_HTTP_HEADERS` (2026-10-22, replaces `JUDGE_API_KEY`): required,
    `Name=value; Name=value`, split on `;` and on each pair's first `=`.
    Covers Bearer, `x-api-key`-style and proxy-auth headers alike. Rejected
    at start-up: no `=`, names other than letters/digits/`-`, empty values,
    line breaks (header injection), duplicates, and `Content-Type` (set by
    the adapter). Only names are logged. Limitation: a value can't contain
    `;` (so no `Cookie` header).
  - Ranges (inclusive): K 1–3 (integer), max tokens 256–32768 (integer,
    `JUDGE_MAX_TOKENS`, 2048 in `.env.example`), temperature 0.0–1.0
    (float). A reply cut off at max tokens (`finish_reason: length`) fails
    with a message naming the setting. A missing or out-of-range value
    exits the program.
  - Configuration isn't versioned in git, so each report copies the
    configuration values it ran with (R9), never the headers.
  - Header values are never logged, under any circumstances, redaction included.
    They stay out of the configuration object and are sent only by the
    provider adapter.
  - `.env` is acceptable for v1 because the key guards a model server on
    an isolated network. Revisit when a vendor adapter, with an external
    account's key, is added.
- **Language** (2026-10-21). `--lang en|ja` (ISO 639-1, default `ja`)
  sets the language of help text, via the string table in `iso.py`.
  Logs and the model's output stay English for now; Japanese is added
  gradually, with untranslated messages falling back to English.
  - Later: Japanese model output costs more tokens for the same content,
    and R5 quotes stay verbatim in the answer file's own language.
- **Plain Python, no framework** (2026-10-19). Direct API calls, minimal
  pinned dependencies (HTTP client, schema validator). A TUI may come later.
  - Rejected: EvalScope (set aside for now); TypeScript.
  - Departs from `EVAL_SUITE_PLAN.md`, which chose EvalScope.
- **Provisional Partial value** (2026-10-19). Until case authors set
  values, code scores Partial as half the question's points.
  - The judge records only the band; code applies the value.
  - Reports mark such scores provisional; the value is versioned (R9).
  - A rubric's own Partial value overrides it; points are recomputed from
    stored bands, no re-run.
  - The one deliberate exception to "no side rules".

## Validation

Procedures for evaluating a judge live in [`../doc/`](../doc/README.md):
fixture calibration, confidence calibration and mutation testing.

## Open questions

- Partial point values for all 64 bands (case authors).
- Which non-Qwen model the lab hardware can host.
- Report-quality rubric: draft criteria A (citation specificity) and B
  (stated uncertainty); per answer or per file; shared or per case.
