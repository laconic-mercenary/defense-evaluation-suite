# Eval Suite Plan — from case set to comprehensive evaluation

Status: draft, not yet approved for implementation. This is a discussion
artifact, not a build order — nothing described here should be built
without a separate, explicit go-ahead per phase.

## Why this exists

`forensic-agent-tests`/`forensic-agent-answers` are a strong
**domain-specific capability** benchmark (13 DFIR cases, graded rubrics)
but currently rely on a manual process: a human pastes an AUT's
`QUESTION_ANSWERS.md` into a conversation and an LLM grades it against
`grading_schema.md` per each case's answer-side `AGENTS.md`. There is no
code anywhere in either repo — no runner, no automated grading, no
cost/latency capture.

This plan extends that into the four-domain structure from Chip Huyen's
*AI Engineering* evaluation framework: domain-specific capability
(existing), generation capability (fluency/hallucination), instruction-
following capability, and cost/latency — each with a scoring method
grounded in established methodology rather than an invented rubric.

Decided so far (2026-09-08 discussion):

- **Runner: agentic/tool-using, not single-turn** (revised 2026-09-09,
  reversing the original decision below, after measuring real evidence
  volume — see "Verified: evidence volume forces the agentic runner").
  The AUT gets real filesystem/tool access to a case's `data/` and works
  multi-turn, matching how the case bundles are actually structured
  (`AGENTS.md`'s "router + evidence index" framing, `TASK.md`'s "targeted
  search rather than reading every file front-to-back"). This is no
  longer an optional, more-realistic upgrade — it's the only architecture
  that works at all for 11 of the 13 cases, because their evidence
  volume exceeds every current model's context window by an order of
  magnitude or more.
  <details><summary>Original 2026-09-08 decision (superseded)</summary>
  Originally: build a minimal, single-turn, context-stuffed harness first
  (paste `TASK.md` + `data/` into one prompt, one API call), deferring an
  agentic runner to a later phase as a "closer to realistic, more
  expensive" upgrade. That framing assumed evidence would be small enough
  to fit in one prompt — checking the actual case data disproved that.
  </details>
- **Judge**: an ensemble of 2-3 judge models per graded item, not a
  single fixed judge or same-family self-grading.
- **Instruction-following**: a separate, content-independent probe set,
  not layered onto the existing 13 cases — keeps instruction-following
  score from being confounded with forensic difficulty. Now concretely:
  DeepEval's built-in **IFEval** benchmark (see below), not a hand-built
  probe set.
- **Grading/metrics library: adopt [DeepEval](https://deepeval.com/)**
  (2026-09-08, after evaluating it directly) as the metrics layer instead
  of hand-rolling G-Eval/DAG-style rubric grading/faithfulness checks.
  Open-source, runs fully local (no forced cloud dependency — Confident AI
  is an optional hosted add-on for dashboards/regression tracking across
  runs, explicitly not adopted for now, revisit only if centralized
  reporting across many runs becomes painful to do locally).
- **MCQ conversion: dropped**, superseded by DeepEval's `DAGMetric` (see
  Phase 1) — grading free-text directly against a rubric-as-decision-tree
  gets the structure/determinism the MCQ hybrid was chasing, without
  rewriting any `EXAM.md` question or risking a distractor set leaking the
  justification answer (a real risk the MCQ approach had, noted in the
  prior draft of this plan).
- **New code's home**: a new sibling directory under this umbrella
  (`eval-harness/`, working name), not inside `forensic-agent-tests` or
  `forensic-agent-answers` — both of those repos' own `AGENTS.md`
  explicitly say nothing should be authored there outside the existing
  case-building process.

## What DeepEval provides vs. what's still custom

Checked directly against deepeval.com before adopting (2026-09-08):

| Need | DeepEval provides | Still ours to build |
|---|---|---|
| Rubric-based grading of free-text (per-question, partial credit) | `DAGMetric` — deterministic decision tree (`BinaryJudgementNode`/`NonBinaryJudgementNode`) mapping verdicts to scores, can embed an LLM judgment node per decision | Translating each `grading_schema.md` entry into a DAG structure |
| Fluency/coherence | `GEval` (built-in G-Eval implementation) | Criteria text per Huyen's framework (structure/clarity/register — reuse cases' own "register/tone" language) |
| Hallucination/faithfulness | `HallucinationMetric` — claim vs. a curated, static `context` (not `FaithfulnessMetric`, which keys off `retrieval_context` and assumes a live/noisy RAG retrieval step we don't have) | Wiring `BRIEFING.md`/`GROUND_TRUTH.json`/raw `data/` in as the `context` list |
| Instruction-following | **IFEval built in as a standard benchmark** | Just running it — effectively finishes Phase 3 |
| Judge ensemble (2-3 judges) | Not supported — every metric takes one `model=` | Call each metric N times with different judge models, own aggregation (majority vote for DAG's discrete verdicts, mean for GEval/Faithfulness's continuous scores) |
| Judge calibration vs. human grades | Not supported | Own comparison step, same as before |
| Cost/latency capture | `LLMTestCase` has `token_cost`/`completion_time` fields to carry this data, but **neither is auto-populated** | The runner still makes the actual target-model API call, times it, counts tokens, computes cost, and populates these fields itself |
| Generating the AUT's answer in the first place | Not in scope — DeepEval evaluates outputs handed to it | The single-turn runner (Phase 4) |

Net effect: DeepEval absorbs essentially all of Phase 1 and Phase 3's
build effort, and gives Phase 2 its metric implementations — but Phase 2's
ensemble/calibration logic and all of Phase 4 (actually running the AUT
and capturing cost/latency) remain genuinely custom work.

## Verified: evidence volume forces the agentic runner

Measured directly (2026-09-09, real `cl100k_base` token counts via
`tiktoken` on each case's fully *uncompressed* `data/`, not the
compressed `.tar.gz` size):

| Case | Tokens |
|---|---|
| `windows-lateral-movement-ntds-exfil` | 43,591,015 |
| `benign-breakglass-account` | 41,836,574 |
| `windows-log-search-basics` | 25,744,021 |
| `departing-employee-email-exfil` | 26,110,182 |
| `pth-lateral-logclear` | 23,114,913 |
| `credential-spray-domain-compromise` | 18,681,714 |
| `insider-dns-tunnel-exfil` | 18,204,196 |
| `phishing-c2-beacon` | 13,545,444 |
| `rogue-service-account-privcreep` | 10,778,065 |
| `dga-beacon-logclear` | 9,999,298 |
| `websqli-webshell-pivot` | 3,962,653 |
| `external-recon-no-breach` | 2,141,830 |
| `ssh-shared-key-overlap` | 657,451 |
| `rdp-remote-file-write` | 189,898 |

Only the last two fit in any current model's context window at all;
11 of 13 exceed even the largest publicly available context windows
(~1-2M tokens) by an order of magnitude or more, and all 14 exceed a
small local model's (e.g. Qwen3-8B-class, ~32K-128K native) by a much
wider margin. This is a hard capability wall, not a cost/performance
concern — a single-turn prompt containing a case's full evidence simply
cannot be sent to (or processed by) any AUT for the vast majority of
cases. This directly forced the runner decision above.

Two things this does **not** affect, confirmed separately:

- **The judge side stays small.** `HallucinationMetric`'s `context` field
  only needs the curated ground truth, not raw evidence —
  `benign-breakglass-account`'s `BRIEFING.md` (1,324 tokens),
  `grading_schema.md` (935 tokens), and `GROUND_TRUTH.json`/`.md`
  (~9,200 tokens combined) are trivially small for any judge model
  (Claude Opus included). The 40M-token problem is exclusively an
  AUT-evidence-access problem, not a judge-context problem — Phase 2's
  design is otherwise unaffected by this finding.
- **Considered and rejected: pre-filtering evidence before stuffing.**
  Even a generous 3-4x reduction from stripping XML verbosity leaves
  most cases still far beyond any workable context budget, and — more
  fundamentally — if the harness decides what's "relevant" before the
  AUT ever sees it, the harness has performed the search/filter step
  `TASK.md` explicitly assigns to the investigator ("targeted search
  rather than reading every file front-to-back") and that Category 1
  (Log Analysis) is graded on. Pre-filtering doesn't just risk missing
  evidence — it tests something narrower and easier than what these
  cases are built to measure. Not adopted for this reason, independent
  of whether it could get enough cases under budget.

`Golden`/`LLMTestCase.input`/`.context` are confirmed (2026-09-08, direct
doc check) to be plain in-memory strings/lists with **no chunking,
truncation, or size management performed by DeepEval** — entirely the
caller's responsibility. This is consistent with the wall above: DeepEval
was never going to solve this for us either way.

## Phase 0 — Scaffolding decisions (no code yet)

- [ ] Confirm the new directory name/location (`eval-harness/` proposed)
      and whether it's git-ignored from this shared umbrella repo the
      same way `forensic-agent-answers/` nominally is (see root
      `README.md`'s note — that pattern is currently non-functional by
      design/accepted, don't copy it uncritically).
- [ ] `pip install deepeval`; confirm license terms are acceptable for
      this project (open-source, checked 2026-09-08 — reconfirm at
      adoption time in case terms changed).
- [ ] Decide which target models are in scope for the first comparison
      run (this determines which vendor APIs the runner needs auth for).
- [ ] Read **DFIR-Metric** (arXiv 2505.19973), already cited in
      `forensic-agent-answers/doc/TEST_OBJECTIVES.md` as the closest
      published prior art, before finalizing DAG rubric structure — check
      what grading methodology it actually uses, don't just cite it as
      precedent without reading it.
- [ ] Decide a versioned pricing source for cost calculation per target
      model (prices change; needs a dated reference, not a hardcoded
      one-time table).

## Phase 1 — Encode `grading_schema.md` as DeepEval `DAGMetric`s

Pilot on 2-3 cases before rolling out to all 13 (don't touch the other
10 until the pilot's judge-vs-human-grade agreement is checked).

- [ ] Pick pilot cases spanning different rubric shapes: at least one
      with a clean discrete-fact check (event ID / host / timestamp —
      `BinaryJudgementNode`), one with a yes/no + justification-quality
      structure (`benign-breakglass-account` Q2 is a good template —
      binary node feeding a `NonBinaryJudgementNode` for justification
      tier), one "flexible answer" question (e.g. `benign-breakglass-
      account` Q4, "what evidence would change your answer" — these may
      need a single LLM-judgment node with no deterministic decomposition
      at all; not everything needs, or benefits from, a DAG).
- [ ] For each question, build the DAG so its verdict scores match the
      existing point values in `grading_schema.md` exactly — the rubric
      text ("Full credit / Partial / Zero") already reads like a decision
      tree, so this is a translation exercise, not new rubric design.
      Confirm the translation preserves the original grading intent
      (e.g. `AGENTS.md`'s explicit instruction to penalize false-positive
      escalation and under-investigation *equally* — make sure the DAG's
      score mapping doesn't accidentally weight one failure direction
      more than the other).
- [ ] Run the pilot DAGs against a few known-good and known-bad sample
      answers (hand-written, not from a real AUT run yet) to sanity-check
      the tree actually produces the expected score before trusting it on
      real transcripts.

## Phase 2 — Judge ensemble (built on DeepEval metrics)

- [ ] Pick the 2-3 judge models. Confirm none of them is also a target
      model under test in the same run (self-preference bias risk this
      project should avoid, not just note).
- [ ] Domain-specific grading: run each pilot `DAGMetric` once per judge
      model, aggregate discrete verdicts via majority vote — decide the
      tie-break rule before the first real run, not after seeing a split
      decision.
- [ ] Fluency/coherence: `GEval` criteria = structure, clarity, register/
      hedging (several cases already grade "register/tone" like
      `departing-employee-email-exfil`, reuse that language as the
      criteria text). Aggregate via mean across judges, not majority vote
      (continuous, not discrete).
- [ ] Hallucination/faithfulness: use **`HallucinationMetric`**, not
      `FaithfulnessMetric` — confirmed 2026-09-08 that they key off
      different fields (`context` vs. `retrieval_context`) and target
      different situations. Our Phase 4 runner has no real retrieval step
      (single-turn, context-stuffed — the model gets all of `data/` at
      once, nothing is "retrieved" at runtime), and `BRIEFING.md`/
      `GROUND_TRUTH.json` are genuinely curated, static ground truth, not
      noisy RAG-retrieved chunks — exactly the case DeepEval's own docs
      say `HallucinationMetric`'s `context` field is for, and exactly the
      case they warn `FaithfulnessMetric`'s `retrieval_context` field is
      *not* for. Wire `BRIEFING.md`/`GROUND_TRUTH.json`/raw `data/` in as
      the `context` list. Confirm this mapping actually works for one
      real case before assuming it generalizes to all 13.
- [ ] **Calibration, before trusting any of the above at scale**: run the
      judge ensemble against a small set of *already manually-graded*
      transcripts (if any exist from prior informal grading sessions) or
      deliberately manually grade a fresh small batch, and check
      judge-vs-human agreement. Don't skip this — it's the step that
      catches position/verbosity/self-preference bias before it's baked
      into every future score.

## Phase 3 — Instruction-following: run DeepEval's IFEval benchmark

- [ ] Confirm IFEval's built-in implementation still matches the current
      DeepEval version at adoption time (re-check, don't assume the
      earlier web check stays accurate).
- [ ] Run it per target model as a standalone score, independent of the
      13 forensic cases — no new probe-writing needed, this phase is
      mostly wiring, not content design.
- [ ] `FollowBench` (graduated constraint difficulty) remains a reference
      for later if more fine-grained instruction-following signal is
      wanted — not needed for a first pass.

## Phase 4 — Runner v1 (agentic, tool-using)

Superseded 2026-09-09: see "Verified: evidence volume forces the agentic
runner" above. The AUT needs real, on-demand file access — it cannot be
handed the evidence pre-flattened, for 11 of 13 cases it categorically
cannot fit in one prompt, and even where it technically could, having the
harness pre-select what to include defeats the search/filter skill the
cases are built to test. DeepEval's
[MeetingSummarizer tutorial](https://deepeval.com/tutorials/summarization-agent/introduction)
(checked 2026-09-08) is no longer the architectural template for this
phase — it's a single-turn, pre-read-transcript pattern, which is exactly
what the token-count finding rules out. Two things from that tutorial
still carry over unchanged, though: (1) DeepEval doesn't care how the
`LLMTestCase.actual_output` was produced — single API call or a full
multi-turn tool-using session both end up as one finished
input/actual_output pair by the time DeepEval sees it; (2) **one AUT run
should still yield multiple `LLMTestCase`s** — one per `EXAM.md`
question, each fed to its own `DAGMetric`, not one monolithic test case
per case-run.

- [ ] Decide the tool surface given to the AUT: minimal (`list_dir`,
      `read_file`, `grep`/search over a case's `data/`) is the likely
      starting point — matching `TASK.md`'s own "targeted search" framing
      — rather than a full coding-agent tool suite the cases don't need.
- [ ] Decide the scaffolding approach per target model. This is the
      concrete question Qwen3-8B (this thread's example AUT) raises:
      does it get served through something exposing OpenAI-compatible
      function-calling (vLLM/Ollama), and do we standardize the tool loop
      across vendors via a shared layer (e.g. LiteLLM's unified interface,
      or DeepEval's own `DeepEvalBaseLLM` adapter extended to drive a tool
      loop) rather than hand-rolling a different agent scaffold per
      vendor. Decide this before wiring up a second target model, not
      after — the whole point of standardizing is avoiding N bespoke
      scaffolds for N target models.
- [ ] Investigate `Golden`'s `expected_tools`/`tools_called` fields
      (surfaced 2026-09-09 while checking `Golden`'s schema) — DeepEval
      appears to have some native support for evaluating *which*
      tools/files an agent actually used, not just its final text, which
      may be directly useful for grading whether the AUT's investigation
      process itself was sound (e.g. did it actually check the hosts a
      question requires, not just guess the right answer). Not yet
      confirmed how this pairs with a metric — check before assuming it
      covers this need.
- [ ] **`AGENTS.md` is delivered as something the AUT reads, not
      something the harness pre-loads** (decided 2026-09-09). The AUT's
      very first message is a generic, case-agnostic bootstrap — e.g.
      "Begin your investigation. Start by reading `AGENTS.md` in your
      working directory." — with no case content in it at all. The AUT
      must call `read_file("AGENTS.md")` itself as its opening move, then
      follow *its own* pointers (`TASK.md`, `data/ENVIRONMENT.md`,
      `EXAM.md`) from there via the same tool calls, exactly as a human
      analyst would navigate the case directory. This also means the
      initial bootstrap message is identical across every case — nothing
      case-specific needs harness-side parsing before the run starts.
- [ ] **SLA timeout, not a turn-count budget, is the authoritative stop
      condition** (decided 2026-09-09). There's no human watching a
      session to notice a stuck or slow investigation, so a wall-clock
      deadline per (case, target model) run is the real requirement: if
      the AUT hasn't called `submit_answers` within X minutes, the run is
      marked **FAIL** outright — not partial credit, not a truncated
      transcript scored as-is. This is a genuine open parameter (X isn't
      picked yet) and should be the **same fixed value across every
      target model**, not adjusted per model's expected speed — the
      point of measuring latency as its own eval domain is exactly that a
      too-slow investigation is a real failure, not a metric to
      normalize away. Two implementation details this implies: (1) the
      deadline needs enforcing both between loop iterations *and* as a
      hard per-call timeout on the model API call itself, since a single
      hung network call wouldn't otherwise be caught by an
      only-check-between-iterations approach; (2) a secondary token/cost
      ceiling is still worth keeping alongside the SLA, since a fast but
      expensive model could rack up large cost within the time budget
      without tripping a wall-clock limit — the SLA bounds time, not
      spend, and both are real constraints.
- [ ] `eval-harness/run_case.py` (or similar): starts an agentic session
      per (case, target model), governed by the SLA timeout and bootstrap
      pattern above, with tool access to `data/` (decompressing/
      converting binary evidence — `.tar.gz`, raw `.evtx` — before it's
      readable; per `forensic-agent-answers/AGENTS.md`'s "Known
      pitfalls," `.evtx` is UTF-16 inside a compressed structure and
      needs `evtx_dump -o jsonl` first, not a raw read). Captures the
      full tool-call transcript, token counts, wall-clock latency (now
      genuinely multi-turn, so this includes however many tool
      round-trips the AUT takes — worth reporting as its own metric, not
      just noise), computes cost from the Phase 0 pricing source, and
      builds one `LLMTestCase` per `EXAM.md` question with `token_cost`/
      `completion_time` populated — or, if the SLA timeout fires first,
      one `LLMTestCase` per question with a distinct `SLA_TIMEOUT_FAIL`
      outcome instead of an `actual_output`.
- [ ] `eval-harness/judge_case.py`: runs the Phase 1/2 DAG/GEval/
      Hallucination metrics (each across the judge ensemble) against each
      saved `LLMTestCase`, saves per-question scores.
- [ ] `eval-harness/aggregate.py`: rolls up scores + cost + latency (now
      including tool-round-trip count) across cases × target models into
      a comparison report.
- [ ] Decide up front whether to run each case once or multiple trials
      per (case, model) pair for variance bars — LLM output is
      stochastic (and now so is the *investigation path* an agentic AUT
      takes) and a single run may not be representative; this is a
      cost/rigor tradeoff to make consciously, not default to N=1 without
      noting the limitation.
- [ ] Start with the two cases small enough to sanity-check outputs by
      hand (`rdp-remote-file-write`, `ssh-shared-key-overlap`) to validate
      the full pipeline end-to-end before running all 13 × every target
      model × every judge — cost multiplies fast across that matrix, and
      an agentic session's cost is much less predictable up front than a
      single API call's.

## Phase 5 — Reporting

- [ ] One report per target model: domain-specific score (DAG-graded
      rubrics), generation-capability score (GEval fluency + Hallucination
      metric), instruction-following score (IFEval), cost, latency.
- [ ] Consider a cost-vs-accuracy view (Pareto-style — several public
      leaderboards now report this pairing) rather than a single ranked
      list, since cost/latency and domain accuracy are genuinely
      different axes of comparison.
- [ ] Confident AI (DeepEval's optional hosted layer) stays out of scope
      for now — local `deepeval test run` output is sufficient for a
      first pass; revisit only if cross-run regression tracking becomes
      painful to maintain by hand.

## Deferred, not dropped

- **Full DAG rollout to all 13 cases** — only after Phase 1's pilot shows
  judge-vs-human agreement holds up.
- **Category 2 (Browser History) gap** — unrelated to this eval-suite
  work, already tracked in `forensic-agent-answers/doc/TEST_OBJECTIVES.md`
  as the one remaining structural coverage gap; not in scope here.
