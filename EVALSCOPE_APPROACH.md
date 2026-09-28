# EvalScope Approach — agent loop & tool-call functional tests

Companion to `EVAL_SUITE_PLAN.md` (the overall eval suite plan — framework
choice, stop conditions, security posture, phases). This document is
scoped narrower and goes deeper: **how we functionally test the agent
loop itself** — the AUT's tool-calling mechanics inside our EvalScope
harness — before trusting any transcript it produces well enough to grade.

Not in scope here (see `EVAL_SUITE_PLAN.md` instead): domain-capability
grading (Phase 1/2 rubrics), instruction-following (Phase 3), cost/latency
reporting (Phase 5). This doc is entirely about Phase 4's mechanics: does
the harness correctly run an AUT through a case and produce a transcript
whose outcome classification can be trusted.

Status: draft, being built iteratively. Code snippets are checked against
a real `modelscope/evalscope` checkout at `203cdc93` (v1.11.1) — cited
paths/line numbers are verified, not recalled from memory.

## Why this layer needs its own tests

The grading pipeline (Phase 1/2) can only be as trustworthy as the
transcripts it's fed. A bug in *our* adapter — the mount, the tool-output
cap, the stop-condition enforcement, the outcome classification — doesn't
look like a bug. It looks like a bad AUT score. We can't tell "Qwen3-8B
failed this case" from "our harness truncated Qwen3-8B's tool output and
called that a failure" unless the harness's own mechanics are tested
independently of any real AUT run. That's the point of this layer.

## Proposed test taxonomy (draft — confirm before we write code)

1. **Environment/mount correctness** — does `build_environment(sample)`
   expose exactly `cases/<slug>/data/`, read-only, and nothing else
   (not `forensic-agent-answers/`, not sibling cases, not the host
   filesystem outside the mount)?
2. **Tool surface correctness** — does `bash` (or whatever tool surface
   we land on) actually work inside the container the way the adapter
   assumes (evtx_dump available, grep/xmllint available, working directory
   correct)?
3. **Tool-output cap** — does a tool call returning more than the cap
   actually get truncated with a notice, rather than blowing context or
   silently passing through?
4. **Stop-condition enforcement** — does `max_steps` actually stop the
   loop at the configured number, and does the token ceiling actually
   trip before `AgentTrace.total_usage` exceeds it?
5. **Outcome classification** — for each of the five outcomes
   (`post_tool`/`sentinel` clean submit, `max_steps_exceeded`,
   `model_context_overflow`, `implicit_no_nudge`, `parse_error_exhausted`),
   can we force that exact condition with a scripted/mock agent and get
   the harness to classify it correctly?
6. **Bootstrap correctness** — does the AUT's first message really carry
   no case content, and does a scripted agent that calls
   `read_file("AGENTS.md")` first actually receive the real file content
   back (not a stale cache, not a wrong case's file)?
7. **Partial-credit-on-truncation plumbing** — when a run is cut off
   mid-investigation, is whatever's in `QUESTION_ANSWERS.md` at that
   instant actually captured and readable afterward, not lost with the
   container?
8. **Security containment (the two P1s from `EVAL_SUITE_PLAN.md`)** — does
   the disposable-host/read-only-mount/no-`LocalAgentEnvironment`-fallback
   rule set actually hold under an adversarial-shaped test (e.g. a
   scripted agent that tries `cat ../../../forensic-agent-answers/...` or
   `cd /` and lists the host)?

## Open questions to settle before writing the first test

- Do we test against **real EvalScope** (`AgentLoopAdapter`,
  `EnclaveAgentEnvironment`, real Docker) from the start, or start with a
  **scripted fake AUT** (a tiny script that emits canned tool calls,
  standing in for a real model) so we can force each of the five outcomes
  deterministically without needing a real model to misbehave on cue?
- Which case is the test fixture — the smallest (`rdp-remote-file-write`,
  0.5 MB) for speed, or a synthetic minimal fixture we build specifically
  for these tests so they don't depend on real case content changing?
- Test runner: plain `pytest` around EvalScope's Python API, or something
  that also drives the CLI path (since the plan notes CLI discovery may
  need the fork/registration path that the Python API doesn't)?

---

*(Everything below this line gets filled in as we go, section by section.)*
