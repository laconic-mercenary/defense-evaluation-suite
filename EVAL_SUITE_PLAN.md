# Eval Suite Plan — from case set to comprehensive evaluation

## Briefing

> **In one line:** a draft plan to automate the manual grading of our 14
> DFIR cases. The framework and stop-condition questions are now settled;
> no code exists yet, and the next step is a calibration spike.

**The situation.** The 14 DFIR cases and their graded rubrics exist and
work. Grading them does not scale: a human pastes an agent's answers into
a conversation and an LLM scores them against `grading_schema.md` by hand.
There is no code in either repo — no runner, no automated grading, no cost
or latency capture. This plan extends that into four evaluation domains
(Chip Huyen's framework): domain capability, generation quality,
instruction-following, and cost/latency.

**The constraint that dictates the architecture.** Case evidence is
enormous — up to 43.6M tokens / 120 MB for one case, with a single file
reaching 45.5 MB. 12 of the 14 cases exceed every current model's context
window, most by an order of magnitude. A single-turn "paste the evidence"
harness isn't merely expensive, it is impossible. The agent-under-test
must be a real tool-using agent that searches on demand. Pre-filtering the
evidence first was considered and rejected: if the harness decides what's
relevant, it has performed the search-and-filter skill the cases grade.

**The framework decision — currently live.** DeepEval was adopted for its
rubric grading while the runner was still assumed single-turn. Once the
runner became agentic, Phase 4 grew into the largest phase — and DeepEval
contributes nothing to it. Reopened.

| Candidate | Strength | Gap |
|---|---|---|
| **DeepEval** | `DAGMetric` rubric decision-trees | No runner, no judge ensemble, no cost/latency capture |
| **Inspect AI** (UK AISI) | `time_limit`/`cost_limit` as tested primitives, sandboxing, ensemble reducers | No DAG equivalent |
| **EvalScope** (Alibaba) | Best judge ensemble; native `skills_dir`; a working 460 MB mount precedent (OfficeQA); IFEval + Multi-IF; latency capture by default | **No wall-clock SLA**; custom benchmarks need an in-tree fork |

**Current lean: EvalScope alone**, conditional on the question below. A
source-level review retired the risks that previously counted against it
(evidence mounting, rubric grading, IFEval availability), leaving one.

**The blocking question, now resolved (2026-09-09): turn count, not
wall-clock.** Phase 4 had made a wall-clock SLA the *authoritative* stop
condition — too slow means FAIL. Reversed. A turn budget (`max_steps`) is
deterministic and reproducible where wall-clock is not: elapsed seconds
are confounded by provider queue depth, rate limiting, host load and
parallelism, so the same model on the same case scores differently on
different days, and a self-hosted model is not comparable to an API one at
all. Turn count also measures something we care about more directly — how
many tool calls it took to reach the answer. Latency stays a **reported
metric, never a gate**. This also dissolves a contradiction: all 14
`TASK.md` promise the AUT "there is no time limit," which stays literally
true under a turn budget, so no case files need editing.

**Consequence: the framework question resolves to EvalScope alone.** Its
only structural gap was the missing wall-clock SLA, which we no longer
want. `max_steps` is native.

**Security — changes the deployment, not the choice.** A source-level
assessment of EvalScope found 12 issues, 2 critical, mostly fixable by
configuration. What makes this sharper for us: the harness host holds the
answer keys, and the AUT is by design an agent with shell access that has
been *instructed to search the filesystem*. Answer-key disclosure wouldn't
merely leak data — it would invalidate every score silently and
retroactively. Hence: runner on a disposable host that never holds
`forensic-agent-answers/`, grading separately, Docker enforced by our own
assertion.

**Phase map.** 0 — decisions + scaffolding · 1 — encode rubrics (pilot
2-3 cases) · 2 — judge ensemble + human calibration · 3 — IFEval ·
4 — agentic runner · 5 — reporting.

**Settled vs. open.** *Settled:* EvalScope as the framework; agentic
runner; turn+token budget with wall-clock demoted to a metric; 2-3 model
judge ensemble; instruction-following as a separate probe set; one session
per case with per-question grading; no evidence splitting; new code in
`eval-harness/`. *Open:* the actual `max_steps` and token numbers (to be
calibrated, not decided up front), target models, pricing source, trials
per case.

**Next action: the Phase 0 spike** — port `officeqa_adapter.py` against
the smallest case and calibrate `max_steps`. First real code.

---

Status: draft, not yet approved for implementation. This is a discussion
artifact, not a build order — nothing described here should be built
without a separate, explicit go-ahead per phase.

## Measured facts

Everything below was measured directly, not estimated. These numbers drive
most decisions in this plan, so they're kept together.

**Case count: 14** (verified against disk 2026-09-09).
`forensic-agent-tests/cases/` and `forensic-agent-answers/case-*/` each
hold 14, fully paired, no orphans. Earlier drafts said 13 in prose while
the table below listed 14 rows; corrected throughout.

**Evidence volume** — `cl100k_base` counts via `tiktoken`, and uncompressed
bytes via `gzip -l` summed over *all* archives per case plus loose files:

| Case | Tokens | Uncompressed |
|---|---|---|
| `windows-lateral-movement-ntds-exfil` | 43,591,015 | 109.1 MB |
| `benign-breakglass-account` | 41,836,574 | 119.7 MB |
| `departing-employee-email-exfil` | 26,110,182 | 74.5 MB |
| `windows-log-search-basics` | 25,744,021 | 77.8 MB |
| `pth-lateral-logclear` | 23,114,913 | 65.7 MB |
| `credential-spray-domain-compromise` | 18,681,714 | 53.2 MB |
| `insider-dns-tunnel-exfil` | 18,204,196 | 51.4 MB |
| `phishing-c2-beacon` | 13,545,444 | 38.4 MB |
| `rogue-service-account-privcreep` | 10,778,065 | 30.9 MB |
| `dga-beacon-logclear` | 9,999,298 | 28.2 MB |
| `websqli-webshell-pivot` | 3,962,653 | 9.1 MB |
| `external-recon-no-breach` | 2,141,830 | 5.7 MB |
| `ssh-shared-key-overlap` | 657,451 | 1.7 MB |
| `rdp-remote-file-write` | 189,898 | 0.5 MB |

Consistent at 2.6-3.2 bytes/token throughout, so the two measurements
corroborate each other. Orderings differ at the top because token density
differs — **use bytes for sizing a mount, tokens for context reasoning.**
Only the last two fit any current context window; 12 of 14 exceed even the
largest (~1-2M) by an order of magnitude.

**Individual files are the real problem.** `benign-breakglass-account` is
44 files, largest `DC-01/windows_event_security.xml` at **45.5 MB**. One
`cat` ends a run — the per-case totals understate the risk.

**The XML is pretty-printed**: ~10 lines per event, ~33 bytes/line. That
45.5 MB file is ~1.4M lines holding ~134K events. **A bare `grep 4624`
returns `    <EventID>4624</EventID>` with no context** — the agent needs
`grep -A/-B`, `xmllint --xpath`, or a parse. This is plausibly part of what
we're testing, but a weak model will exhaust its budget discovering it.

**Exam shape: 73 graded items** across 14 cases (3-7 questions each). All
14 `TASK.md` use the same flow — answer every `EXAM.md` question, write to
`QUESTION_ANSWERS.md`, restate question numbers, cite evidence.

**Questions are interdependent.** E.g. `rdp-remote-file-write` Q5 asks what
identifier ties a process to "*this particular remote logon session*",
which is only meaningful given Q1-Q4. Per-question isolated sessions would
break the exams.

**All 14 `TASK.md` state "There is no time limit and no restriction on how
you investigate."** This contradicted Phase 4's original wall-clock SLA
decision, and was part of why that decision was reversed — a turn budget
keeps the sentence literally true, so no case files need editing.

## Decisions

Dated; superseded ones are archived at the end rather than deleted.

- **Runner: agentic/tool-using** (2026-09-09, reversing the original
  single-turn decision). Forced by evidence volume above — this is a
  capability wall, not a cost concern.
- **One agentic session per case, graded per question** (2026-09-09). The
  interdependence finding rules out per-question sessions; the existing
  `QUESTION_ANSWERS.md` flow already works this way. Yields 73 graded
  items. Variance data comes from repeated whole-case runs.
- **No evidence splitting** (2026-09-09). Splitting large files is milder
  than pre-filtering — it doesn't decide relevance — but it destroys what's
  measured: a 45 MB file you must search *is* the test. Replace it with 500
  small files and a search problem becomes a directory-listing problem.
  Chunked reads instead (Phase 4).
- **Stop condition: turn count + token ceiling, the same for every case
  and every model** (2026-09-09, reversing the wall-clock SLA). Rationale
  and the option comparison are in "Stop conditions" below.
- **Framework: EvalScope alone** (2026-09-09, following from the above).
  Its only structural gap was the wall-clock SLA we no longer want. Keep
  DeepEval only if Phase 1's pilot shows a DAG beats weighted binary
  criteria — default to not carrying it.
- **Judge: an ensemble of 2-3 models** per graded item, never same-family
  self-grading.
- **Instruction-following: a separate probe set**, not layered onto the 14
  cases — keeps the score from being confounded with forensic difficulty.
  Concretely IFEval, which ships in all three candidate frameworks, so this
  carries no weight in the framework decision.
- **MCQ conversion: dropped.** Grading free-text against a structured
  rubric gets the determinism the MCQ hybrid was chasing without rewriting
  any `EXAM.md` question or risking a distractor set leaking the answer.
  Independent of the framework question.
- **Grading library: reopened** (2026-09-09). DeepEval was adopted
  2026-09-08 for `DAGMetric`, chosen while the runner was still assumed
  single-turn. See the survey below.
- **New code's home**: a new sibling directory (`eval-harness/`, working
  name). Both existing repos' `AGENTS.md` forbid authoring outside their
  own processes.

## Stop conditions

Decided 2026-09-09, reversing Phase 4's original wall-clock SLA. Verified
against EvalScope source at `203cdc93`.

Two decisions were previously conflated — **what bounds a run** and **what
happens when the bound is hit**. Separating them is what resolved this.

### What bounds a run

| Bound | Reproducible? | Measures | Native? |
|---|---|---|---|
| Wall-clock | **No** | Operational acceptability | Native only on the external-CLI path |
| **Turn count** (`max_steps`) | Yes | Investigative efficiency | **Yes** |
| **Token budget** | Yes | Actual work done | Recorded, not enforced |
| Cost ($) | Yes | Deployment economics | No |

**Wall-clock is not reproducible, and that disqualifies it as a gate.**
Elapsed seconds are confounded by provider queue depth, rate limiting,
host load and how many cases run in parallel — so the same model on the
same case scores differently on different days, and a model that was slow
because the API throttled is indistinguishable from one that was slow
because it is bad. It is also incomparable across serving setups: a
self-hosted Qwen3-8B second and a hosted-API second are not the same unit.
For a benchmark meant to be re-run and compared over time, that is
disqualifying.

Turn count is deterministic, and measures something closer to what we
actually want to know: how many tool calls it took to reach the answer.
Its blind spot is that turns are not equal — one `grep` returning 50 KB is
more work than five `ls` — which is what the token ceiling covers.

- **`max_steps` is native and fully at our disposal**, settable per run
  (`--agent-config '{"mode":"native","max_steps":N}'`) and recorded into
  `AgentTrace.max_steps`, so every run carries the budget it ran under and
  old runs stay interpretable after recalibration.
- **The token ceiling is ours to enforce.** No `token_limit`/`usage_limit`
  exists in the agent loop (the only "budgets" there are nudge streaks and
  the external runner's wall-clock). But `AgentTrace.total_usage`
  aggregates usage across every `MODEL_GENERATE` event and each event
  carries `token_usage`, so a cumulative check between iterations is small
  custom work. Free backstop: `LoopMessages.MODEL_CONTEXT_OVERFLOW` means
  the loop already detects a run that blows its context.
- **One budget for all 14 cases, not per case.** Simpler and more
  defensible: per-case budgets scaled to evidence size would embed our own
  judgement of difficulty into the score. Accepted cost — a budget sized
  for `benign-breakglass-account` (120 MB) is generous for
  `rdp-remote-file-write` (0.5 MB), so a model that flails on a small case
  won't be caught by the budget. Revisit if the small cases turn out not
  to discriminate between models.
- **Numbers are calibration, not design.** EvalScope's `max_steps` default
  of 10 is an order of magnitude too low for us — the largest case is 44
  files across 8 hosts with 7 questions, which puts a competent run in the
  low hundreds of tool calls. The Phase 0 spike exists to measure this.
- **Latency remains a reported metric, never a gate** — see Phase 5.

### What happens when a bound is hit

**Grade whatever is in `QUESTION_ANSWERS.md` at cutoff, flagged as
truncated.** The case design makes this natural: `TASK.md` has the agent
write answers to a *file*, not a single terminal `submit` call, so an
agent that writes as it goes leaves partial answers on disk. "Answered 4
of 7 questions within budget" is real signal; a zero is not.

Rejected: **FAIL (score 0)** discards everything the run did achieve.
**VOID (discard and re-run)** wastes the run and hides a real capability
difference.

### Run outcomes are a five-way taxonomy, not pass/fail

The loop already distinguishes these, and they are documented as part of
its "externally observable contract" with tests asserting the literal
strings:

| Outcome | Meaning |
|---|---|
| `submission_source: post_tool` / `sentinel` | Clean submit |
| `max_steps_exceeded` | Exhausted turn budget |
| `model_context_overflow` | Ran out of context |
| `submission_source: implicit_no_nudge` | Stopped calling tools and declined the nudge — **gave up** |
| `submission_source: parse_error_exhausted` | Kept breaking the output protocol — **couldn't drive the tools** |

The source keeps the last two deliberately distinct because "the model
stopped calling tools" and "the model kept breaking the output protocol"
need different diagnoses. **This matters for scoring:** a
`parse_error_exhausted` run is a tool-use/instruction-following failure,
not a forensic-capability failure. Collapsing both into a domain-score
zero would actively mislead — report the outcome as its own column
(Phase 5).

## Framework survey

Surveyed 2026-09-09. DeepEval and Inspect AI from documentation only;
EvalScope additionally from source at v1.11.1 @ `203cdc93`.

**Rejected quickly:** Ragas (RAG-metric-shaped; we have no retrieval step
in that sense) · promptfoo (config assertions + red-teaming, no agentic
sandbox) · OpenCompass (benchmark-dataset-centric; its task scheduling
would suit our matrix but bespoke case bundles run against the grain) ·
FlagEval, lm-evaluation-harness (leaderboard/static-benchmark shaped;
lm-eval remains a fallback IFEval source) · Langfuse / Phoenix / Braintrust
(observability, complementary not substitutes — Langfuse is the *local*
answer if cross-run regression tracking ever becomes painful, avoiding the
Confident AI hosted dependency already declined).

### What EvalScope gives us, verified at source

- **Mounting a case's `data/`: yes.** Docker environments support volume
  mounts and `put_dir` (`agent/environments/enclave.py`). **OfficeQA**
  (`benchmarks/officeqa/officeqa_adapter.py:145-157`) mounts a ~460 MB
  read-only corpus at `/corpus` and has the agent `grep`/`cat` to an
  answer, in ~200 lines — our exact shape, at 4× our largest case. Port it
  rather than starting blank.
- **`skills_dir`** — `NativeAgentConfig` reads host folders containing
  `SKILL.md`. A native home for `TEST_OBJECTIVES.md`'s already-adopted
  decision to enrich the AUT with a skills library. No other framework
  surveyed offers this directly.
- **Judge config is the best of the three**: `models` as a list,
  `aggregation` (`mean`/`median`/`majority_vote`), `position_swap`,
  `repeats`, `min_valid_judges` with invalid replies *excluded* rather than
  scored zero, and `judge.contract` for custom prompt/score mapping.
- **Rubric grading without a DAG**: ResearchRubrics (101 tasks × 2,593
  weighted binary criteria) and HealthBench are in-tree patterns; weighted
  binary criteria are structurally close to a DAG of binary nodes.
  ResearchRubrics is additionally an **agentic** benchmark
  (`AgentLoopAdapter` + `run_bash`) rather than a pure scorer, which makes
  it the single best starting template for us — see Phase 4.
- **A catalogue of agentic precedents** beyond OfficeQA: DeepSearchQA and
  WideSearch (retrieval over a corpus), Terminal-Bench (command-line in a
  sandbox), GAIA, τ-bench family (agent↔simulated-user, bespoke loops).
  Worth skimming if the ResearchRubrics/OfficeQA combination leaves gaps.
- **Latency by default**: `--collect-perf` is on and writes per-request
  latency, TTFT and token usage into the *evaluation* report
  (`config.py:338`); TTFT needs `stream=true`. Separate `evalscope perf`
  adds throughput sweeps and trace-replay datasets for agent-shaped load.
- **IFEval, IFBench and Multi-IF** all present.
- **External Agent Bridge** delegates a sample to Claude Code / Codex /
  Gemini CLI. Inspect can do this too — not a differentiator.

**Costs:** no wall-clock SLA (`max_steps` + `command_timeout` only) —
no longer a problem, see "Stop conditions"; no abort-on-spend ceiling
(token usage *is* captured, so cost is computable post-hoc). No
cybersecurity content in tree, which doesn't matter to us since we're
authoring the domain benchmark either way.

**The fork requirement is weaker than first recorded** (corrected
2026-09-09 from source). `docs/en/advanced_guides/add_benchmark.md:281`
describes the in-tree contribution path, and this plan previously took
that to mean a vendored fork was mandatory — a third artifact to re-home
at the repo split. In fact `register_benchmark` (`api/registry.py:89`) is
a plain decorator writing into a module-level `BENCHMARK_REGISTRY`, the
same pattern as `register_agent_tool`. The in-tree layout is what
`benchmarks/__init__.py`'s `importlib` auto-*discovery* walks, not the
only registration route: an external module should register fine if
imported before `run_task`, which the Python API allows. A fork would
only be needed for CLI discovery. **Confirm in the spike** — if it holds,
`eval-harness/` stays a normal sibling directory with EvalScope as an
ordinary dependency, and the repo-split objection disappears.

### Verdict

**EvalScope alone. Decided 2026-09-09.** It covers Phase 2 better than
anything surveyed, covers Phase 3, covers Phase 5's latency axis by
default, has a working precedent for Phase 4's hardest mechanical problem,
and is the only one with a native home for skills enrichment. One
dependency, one config, one report format.

The one thing standing against it — no wall-clock SLA — stopped mattering
when the stop condition became a turn budget, which is native. That
reversal was made on measurement grounds (reproducibility), not to
accommodate the framework; it happens to remove the objection as a side
effect. Worth being explicit about the direction of causation, since
"we changed the requirement to fit the tool" would be a bad reason and
this isn't that.

Keep DeepEval only if Phase 1's pilot shows a DAG beats weighted binary
criteria on judge-vs-human agreement. Default to not carrying it.

**Caveat on using security to decide:** we hold a source-level assessment
of EvalScope and none of the alternatives. Absence of findings is not
absence of vulnerabilities, and scoring the reviewed candidate down is a
straightforward selection error. If security decides this, commission the
equivalent review rather than inferring from silence.

## Security posture

Source-level assessment of EvalScope v1.11.1 @ `203cdc93`, 2026-09-09.
Its conclusion, concurred with: **not disqualifying, but it changes the
deployment from "run it on the workstation" to "run it on a host that
holds nothing you care about."**

| # | Sev | Issue |
|---|---|---|
| 1 | P1 | `eval()` on raw model output (`benchmarks/docmath/utils.py:113`), reached from the normal scoring path — in-process, no sandbox. **The evaluated model is the attacker.** Confirmed executable. |
| 2 | P1 | `POST /api/v1/eval/invoke` takes an arbitrary `TaskConfig` with **no auth** (`service/blueprints/eval.py:181`); defaults to `0.0.0.0` + blanket CORS. Chains to RCE, SSRF, or reading others' runs. |
| 3 | P2 | Unauthenticated arbitrary file read — `realpath()` without containment check (`reports.py:101-135`), extension-gated, symlinks followed. |
| 4 | P2 | `pickle.loads` on dataset-controlled data (`live_code_bench/load_utils.py:35`) — RCE at load time. |
| 5 | P2 | Model-generated code on host behind `reliability_guard()` (`humaneval/utils.py:44`), which is monkeypatching, not containment. |
| 6 | P3 | `environment='local'` runs model-chosen `bash` on the host, inheriting env incl. API keys. Docs say dev-only; **nothing enforces it.** |
| 7-10 | P3 | Zip Slip in two adapters; bridge proxy forces `0.0.0.0`, plaintext HTTP; `trust_remote_code=True` hardcoded in four places; `shell=True` in two backends. |
| 11-12 | P4 | `exec()` on config-supplied logic (matters because #2 *is* a trust boundary); a scratch script with `pickle.loads` shipped in-package. |

Credited in the same assessment: API keys use `SecretStr` with recursive
redaction, no key leakage found; `claw_eval`/`miniwob` extract archives
safely; `acebench` deliberately replaced upstream's `eval()` with AST
resolution. A hardening pass has happened — `docmath` was missed.

### Why this project is a sharper case

1. **Answer-key disclosure invalidates the benchmark silently and
   retroactively.** Not a leak that gets noticed and contained — a loss
   that makes every score unfalsifiable with no signal. #3 is
   extension-gated, but #2 gives code execution, and that reads anything.
2. **The AUT is adversarial by construction and is told to search the
   filesystem.** #6 means one config field puts that agent on the host
   holding the answer keys. **This needs no malice** — an over-eager agent
   walking up one directory is sufficient. Most likely risk on this page.
3. **The held-out boundary is a directory, not an access control.** Root
   `README.md` records that `forensic-agent-answers/` was committed
   despite intent to exclude it. Until the repo split, physical separation
   of the eval host is the only real control.

### Non-negotiable deployment rules

- [ ] Runner on a **disposable host that never holds
      `forensic-agent-answers/`**. Grading is a separate step elsewhere;
      transcripts are the only thing that crosses. The
      `run_case.py`/`judge_case.py` split already has this shape.
- [ ] Mount **the case subdirectory, read-only** —
      `-v .../cases/<slug>:/case:ro`. Never `cases/`: that exposes the
      other 13, and the cases' own `AGENTS.md` says not to read them.
- [ ] **`environment='docker'` enforced by our own assertion.** The
      framework will not stop us.
- [ ] Never start `evalscope app`/`service` without `--host 127.0.0.1`;
      preferably don't run the dashboard on the eval box at all.
- [ ] **Skip or patch `docmath`** if a baseline battery is run; same for
      code benchmarks unless the host is genuinely disposable.
- [ ] Treat `trust_remote_code=True` as a constraint on model selection —
      **locally-loaded weights are code, not data**. Bears on Phase 0's
      target-model item; API-served models don't carry this risk.
- [ ] Report finding #1 upstream via `.github/SECURITY.md` — one-line fix
      (`ast.literal_eval`), worth doing regardless of adoption.

## Phase 0 — Decisions and scaffolding (no code yet)

- [x] ~~Answer the SLA question~~ — **resolved 2026-09-09**: turn count +
      token ceiling, one budget for all cases and models, wall-clock
      demoted to a reported metric. See "Stop conditions". This also
      settled the framework (EvalScope alone).
- [ ] **The spike, now the first real work** — port `officeqa_adapter.py`
      against `rdp-remote-file-write` (0.5 MB, smallest): mount `data/`
      read-only, give the agent `bash`, answer one `EXAM.md` question.
      Its job is **calibrating `max_steps`** — the default of 10 is an
      order of magnitude too low — plus checking whether `AgentLoop`
      degrades at depth and confirming the truncation outcomes surface as
      documented. Produces a transcript usable as a Phase 1 sample.
      Escalate to `ssh-shared-key-overlap` (1.7 MB) if the first is too
      small to stress the loop, then to a large case to find the real
      ceiling — the budget has to be sized for
      `benign-breakglass-account`, not for the case we spiked on.
- [ ] Set the token ceiling alongside it, enforced off
      `AgentTrace.total_usage` between iterations. Pick the number from
      the same spike runs, sized so it only catches the
      few-turns-enormous-context pathology rather than binding before
      `max_steps` does in a normal run.
- [ ] Verify whether EvalScope caps tool output by default. If not, the
      cap is a hard prerequisite for any large case (Phase 4) — one `cat`
      of the 45.5 MB file otherwise ends a run regardless of budgets.
- [ ] Confirm `eval-harness/` name/location, and whether it's git-ignored
      the way `forensic-agent-answers/` nominally is (root `README.md`'s
      note — that pattern is currently non-functional, don't copy it
      uncritically).
- [ ] Confirm license terms at adoption time — EvalScope Apache-2.0,
      Inspect AI MIT, DeepEval open-source; all checked by doc only
      2026-09-09.
- [ ] Decide target models in scope (determines which vendor APIs need
      auth). **Self-hosted weights execute code on load** — see the
      security rules.
- [ ] Read **DFIR-Metric** (arXiv 2505.19973), cited in
      `TEST_OBJECTIVES.md` as the closest published prior art, before
      finalising rubric structure — check what grading methodology it
      actually uses rather than citing it as precedent unread.
- [ ] Decide a **versioned, dated pricing source** for cost calculation.

## Phase 1 — Encode `grading_schema.md` as machine-gradable rubrics

Pilot on 2-3 cases before rolling out to all 14 (don't touch the other 11
until judge-vs-human agreement is checked).

**The DAG is not the assumed approach.** EvalScope's ResearchRubrics and
HealthBench patterns cover weighted multi-criterion grading, and weighted
binary criteria are structurally close to a DAG of binary nodes. Run the
pilot as a comparison, defaulting to *not* carrying a second library.

- [ ] Pick pilot cases spanning different rubric shapes: a discrete-fact
      check (event ID / host / timestamp), a yes/no + justification-quality
      structure (`benign-breakglass-account` Q2), and one "flexible answer"
      question (`benign-breakglass-account` Q4, "what evidence would change
      your answer") — the last may need a single judgment with no
      deterministic decomposition at all.
- [ ] Build one pilot case's rubric **both** ways — weighted binary
      criteria and a `DAGMetric` — and score the same hand-written
      known-good/known-bad samples with each. The DAG only justifies a
      second library if it measurably wins on agreement.
- [ ] Match verdict scores to existing `grading_schema.md` point values
      exactly — the rubric text already reads like a decision tree, so this
      is translation, not new rubric design.
- [ ] Preserve the answer-side `AGENTS.md` requirement to penalise
      false-positive escalation and under-investigation **equally**. This
      is easier to break in weighted criteria than in a DAG: a list with
      more "did you find X" items than "did you correctly decline to
      escalate" items silently weights one direction. **Check criterion
      counts per direction, not just weights.**

## Phase 2 — Judge ensemble

- [ ] Pick the 2-3 judge models. Confirm none is also a target model in the
      same run (self-preference bias).
- [ ] Adopt **EvalScope's judge schema as the design spec** whichever
      framework wins: `position_swap` (automated position-bias mitigation,
      vs. this plan merely watching for it), `min_valid_judges` with
      invalid replies excluded not zeroed (a malformed judge reply
      otherwise looks identical to a wrong AUT answer), and `repeats`
      (self-consistency per judge). Decide whether N judges × M repeats is
      affordable at 73 items × models, or whether repeats are pilot-only.
- [ ] `judge.contract` carries each case's answer-side `AGENTS.md` grading
      instructions — the ensemble config governs *how many* judges and how
      verdicts combine; the contract governs what each is told. Don't
      conflate them.
- [ ] Domain grading: run each pilot rubric once per judge, aggregate
      discrete verdicts by majority vote. **Fix the judge count at 3 or
      write the tie-break rule down** — "we'll see" means it gets decided
      by whatever the code happened to do.
- [ ] Fluency/coherence: criteria = structure, clarity, register/hedging
      (reuse cases' own "register/tone" language, e.g.
      `departing-employee-email-exfil`). Aggregate by mean, not majority —
      continuous, not discrete.
- [ ] Hallucination: per-case "does this claim contradict
      `GROUND_TRUTH.json`" still needs building. **Keep it separate from
      the standalone benchmarks** — HaluEval/TruthfulQA measure *a model*,
      not our AUT's case answers; those belong in Phase 3. Don't let the
      cheap one stand in for the one that grades our cases.
      <details><summary>Superseded metric-choice reasoning</summary>
      Phase 2 originally chose DeepEval's `HallucinationMetric` over
      `FaithfulnessMetric` partly because "our runner has no real retrieval
      step (single-turn, context-stuffed)." That premise died with the
      agentic reversal — an agent grepping through `data/` *is* retrieving
      at runtime, and what it pulls back *is* noisy. The surviving half of
      the argument: `BRIEFING.md`/`GROUND_TRUTH.json` are curated static
      ground truth, not RAG chunks. Both may apply to different questions —
      consistency-with-ground-truth vs. did-the-conclusion-follow-from-the-
      evidence-opened, the latter close to the investigation-soundness
      question in Phase 4.
      </details>
- [ ] **Calibration before trusting any of this at scale**: run the
      ensemble against already-manually-graded transcripts, or deliberately
      grade a fresh small batch, and check agreement. This is the step that
      catches position/verbosity/self-preference bias before it's baked
      into every future score.

## Phase 3 — Instruction-following

- [ ] Run IFEval per target model, standalone, independent of the 14 cases.
      Mostly wiring. Framework-agnostic, so it should carry no weight in
      the framework decision.
- [ ] **Prefer Multi-IF alongside plain IFEval** if we land on EvalScope —
      the runner is multi-turn, so single-turn IFEval measures something
      narrower than what the AUT does. Both are cheap; report both.
- [ ] Add the standalone hallucination benchmarks here (HaluEval,
      TruthfulQA) — fabricated findings are the dominant failure mode in
      investigative agents, and these target it directly.
- [ ] `FollowBench` remains a reference if finer-grained signal is wanted
      later. Not needed for a first pass.

## Phase 4 — Runner (agentic, tool-using)

The AUT needs real, on-demand file access. It cannot be handed evidence
pre-flattened; for 12 of 14 cases it categorically cannot fit in one
prompt, and even where it could, harness pre-selection defeats the
search/filter skill being tested.

Two durable points, framework-neutral: a grading layer doesn't care how an
answer was produced (which is what makes mixing a runner and a grader from
different frameworks viable); and **one run yields one graded item per
`EXAM.md` question**, not one monolithic result per case.

### Why the no-code path doesn't work for us

Checked 2026-09-09. EvalScope's `general_qa` benchmark takes a JSONL of
`{"query": ..., "response": ...}` (or a full `messages` array) plus a
config block, and routes it through the AgentLoop with tools, a Docker
mount and an LLM judge — **no adapter code at all**. That is a real
afternoon-sized path, and it is the right answer for a benchmark whose
questions share one evidence corpus.

**It is not available to us, for one structural reason: our evidence is
per-case, not shared.** `benign-breakglass-account` is 8 hosts / 44 files
/ 120 MB; `rdp-remote-file-write` is 2 hosts / 4 files / 0.5 MB. Nothing
is common between them. And per-sample evidence cannot be declared in the
data:

- `Sample` has `files`, `setup` and `sandbox` fields, but they are
  **vestigial**. `files`/`setup` are populated at load time
  (`api/dataset/utils.py:43-44`) and never read downstream; `sandbox` has
  no references at all. The GAIA adapter says so in-tree — *"evalscope's
  `Sample.files` field is currently not consumed by any environment"* —
  and works around it by mounting the whole split directory read-only.
- `GeneralQAAdapter.record_to_sample` returns
  `Sample(input=..., target=...)` and **discards every other field**, so an
  `evidence_dir` column in the JSONL would simply be dropped.

GAIA's workaround is closed to us too: mounting the whole `cases/`
directory would expose the other 13 cases, which both our security rules
and the cases' own `AGENTS.md` forbid.

**But per-sample mounting is fully supported one level up.**
`build_environment(self, sample)` receives the sample, so an adapter can
mount `sample.metadata['evidence_dir']` per case. The limitation is
declarative-only. That is the whole argument for writing the adapter.

Two traps worth recording even though we're not taking this path:

- **`general_qa`'s default metrics are BLEU and Rouge**
  (`metric_list=['BLEU', 'Rouge']`, main score `Rouge-L-R`). For "identify
  the initial access vector," n-gram overlap against a reference string is
  close to meaningless — a correct answer phrased differently scores near
  zero, and a wrong answer recycling the question's vocabulary scores
  well. Any use of `general_qa` needs the LLM judge configured explicitly
  or the numbers will look fine and mean nothing.
- `environment_extra` is forwarded verbatim to the environment
  constructor (`agent/runner.py:147-148`), so Docker options — volumes,
  network mode, memory caps — pass straight through.

### Session and exam flow

- [ ] **One sample per case — not one per question.** This is the easiest
      thing to get wrong, because the obvious adapter shape (and every QA
      benchmark in the tree) is one record = one question, which would
      make our JSONL 73 lines with an `evidence_dir` each. That breaks two
      ways: **cost** — 73 full agentic investigations instead of 14, each
      re-discovering the same evidence, roughly 5× the spend; and
      **correctness** — our questions are interdependent, so
      `rdp-remote-file-write` Q5 ("what identifier ties notepad.exe to
      *this particular remote logon session*") is unanswerable in
      isolation. One session per case, all questions, one submission,
      matching the existing `QUESTION_ANSWERS.md` contract.
- [ ] Consequently `target` is **not a single reference answer** — it is
      the whole rubric for that case's 3-7 questions, and `match_score`
      splits the submission and scores per question, emitting 73 graded
      items from 14 samples. This is the ResearchRubrics shape (one
      response scored against many weighted criteria), not the QA shape —
      another reason to start from that adapter rather than a QA one.
- [ ] **Don't parse free-form markdown for the split.** Either require
      `submit` to carry JSON keyed by question number, or keep
      `QUESTION_ANSWERS.md` with an enforced per-question header format
      plus a schema check. Prefer the latter with a judge-assisted parse
      fallback — it preserves the case-file contract, whereas changing the
      answer format means editing all 14 `TASK.md`.
- [ ] Start sequence, to be implemented as:
      `record_to_sample()` → one Sample per case ·
      `build_environment()` → container up, case dir mounted read-only ·
      strategy sets the system prompt · first user message is the
      **case-agnostic bootstrap** ("Begin your investigation. Start by
      reading `AGENTS.md` in your working directory.") · loop until
      `submit` / `max_steps` / SLA · `AgentTrace` persisted.
- [ ] **`AGENTS.md` is read by the AUT, never pre-loaded by the harness.**
      The bootstrap contains no case content, so it is identical across all
      14 — which works because the cases already self-route (`AGENTS.md` →
      `TASK.md` → `EXAM.md` + `data/ENVIRONMENT.md`).

### Tools and evidence access

- [ ] **A hard tool-output cap is mandatory** — the single most important
      item in this phase. Every tool result re-enters context; without a
      cap, one `cat` on the 45.5 MB file ends the run. Cap at ~50-100 KB
      with an explicit truncation notice stating how much was elided and
      how to page. It is simultaneously a context, cost and blast-radius
      control. **Verify whether EvalScope caps by default; if not, it's
      ours to add.**
- [ ] Tool surface: `bash` alone may be the whole answer. EvalScope ships
      `bash`, `python_exec`, `submit` and no file-read tool; OfficeQA
      reaches a mounted corpus with bash only. That matches `TASK.md`'s
      "targeted search" framing and handles `evtx_dump` without a custom
      tool. Options in increasing fidelity: (a) `bash` only; (b) a
      filesystem MCP server, no code; (c) `@register_agent_tool` for
      `read_file(path, offset, limit)` with schemas matching production —
      worth it only if eval-time schemas must match production exactly,
      since schema wording measurably changes tool-use behaviour. (c) needs
      `import your_module` before `run_task`.
- [ ] **Put large-evidence guidance in the harness system prompt, not the
      case files** — "evidence files are large; check sizes before reading;
      events are pretty-printed XML so grep with context." This is
      navigational, not relevance-deciding, so it doesn't reopen the
      pre-filtering objection, and a real analyst gets it from `ls -la`.
      Editing 14 `AGENTS.md`/`TASK.md` would mean going through the
      port-over process in a repo that forbids direct authoring. Trade-off:
      guidance in the harness rather than the case record makes results
      harder to reproduce outside our harness — accept consciously.
- [ ] **Start from `researchrubrics_adapter.py`, not `officeqa_adapter.py`**
      (revised 2026-09-09 after reading both). ResearchRubrics is the
      closer match to our shape because it is *both* halves at once: it
      extends `AgentLoopAdapter` (agentic, multi-turn, `run_bash`) **and**
      drives the judge API (`JudgeDefinition`, `JudgeCase`, `OutputContract`,
      `CaseVerdict`, `ReducedVerdict`, `ScoringPolicy`) for weighted binary
      rubric grading — which is exactly Phase 1 plus Phase 4 in one
      working example. It also carries **judge-side chunking**
      (`judge_context_limit` 150000, `judge_chunk_size` 100000,
      `chunk_document`) for when the material being judged exceeds the
      judge's context — worth knowing about if we ever judge transcripts
      rather than just `QUESTION_ANSWERS.md`. Take the corpus-mount
      mechanics from OfficeQA (below); take the structure from
      ResearchRubrics.
- [ ] The mount incantation, verified from
      `officeqa_adapter.py:build_environment`:
      ```python
      sandbox_config = {
          'working_dir': _CONTAINER_CORPUS_DIR,
          'volumes': {self._corpus_dir: {'bind': _CONTAINER_CORPUS_DIR, 'mode': 'ro'}},
      }
      return EnclaveAgentEnvironment(engine='docker', sandbox_config=sandbox_config)
      ```
      `mode: 'ro'` is confirmed available, so read-only mounting of a case
      directory is a solved problem.
- [ ] **Remove OfficeQA's `LocalAgentEnvironment` fallback when porting.**
      Its `build_environment` silently falls back to running `bash` on the
      *host* when `task_config.sandbox.enabled` is false. That is security
      finding #6 sitting inside the template we are copying — not a
      config mistake we might make, but a default we would inherit. Our
      adapter must raise instead of falling back. This is the single
      easiest way for the answer-key exposure scenario to happen by
      accident.
- [ ] `skills_dir` delivers the AUT skill enrichment
      (`TEST_OBJECTIVES.md`'s adopted decision). **Decide which skills get
      mounted — it's a test-design question, not config.** A
      category-matched subset leaks which of the nine categories a case
      belongs to; all 818 avoids the leak but makes skill *selection* part
      of the task. Record which was used with any published score.
- [ ] Decompress/convert binary evidence before it's readable —
      per `forensic-agent-answers/AGENTS.md`'s "Known pitfalls," `.evtx` is
      UTF-16 inside a compressed structure and needs `evtx_dump -o jsonl`
      first, not a raw read.

### Limits, cost and outputs

- [ ] **Turn count + token ceiling as the stop condition** — one budget
      for every case and every model. Full rationale in "Stop conditions".
      `max_steps` is native and recorded into the trace; the token ceiling
      is ours, enforced off `AgentTrace.total_usage` between iterations,
      with `model_context_overflow` as a free backstop.
- [ ] **On budget exhaustion, grade the partial `QUESTION_ANSWERS.md`** —
      not a zero, not a discarded run. Record the run outcome alongside the
      score using the loop's own five-way taxonomy (`max_steps_exceeded`,
      `model_context_overflow`, `implicit_no_nudge`,
      `parse_error_exhausted`, clean submit). Keep these out of the domain
      score: a run that couldn't emit valid tool calls failed at tool use,
      not at forensics, and scoring it as forensic incompetence would
      mislead.
- [ ] Nothing enforces that the agent writes `QUESTION_ANSWERS.md`
      incrementally rather than all at once at the end — and partial
      credit on truncation depends on it. Check what models actually do in
      the spike. If they buffer to the end, either the system prompt asks
      for incremental writes, or partial credit quietly never materialises
      and truncation collapses back to a zero.
- [ ] `eval-harness/run_case.py`: starts a session per (case, model),
      captures the full tool-call transcript, token counts, wall-clock
      latency (now including tool round-trips — report as its own metric,
      not noise), computes cost, and emits one item per question, each
      tagged with the run's outcome from the five-way taxonomy. **Write
      transcripts to disk as the durable artifact**: a re-gradeable
      transcript survives a framework change, and survives recalibrating
      `max_steps` — which will happen, so runs need to stay interpretable
      against the budget they actually ran under (`AgentTrace.max_steps`
      records it).
- [ ] `eval-harness/judge_case.py`: runs Phase 1/2 metrics across the
      ensemble against saved transcripts, saves per-question scores. Reads
      from disk, on a different host — two processes, not two functions.
- [ ] `eval-harness/aggregate.py`: rolls up scores + cost + latency +
      tool-round-trip count across cases × models.
- [ ] Investigate whether the framework can grade *which* tools/files the
      agent used, not just its final text — e.g. did it actually check the
      hosts a question requires, or guess right. `AgentTrace.events`
      records every call, so the data exists; what's unclear is how it
      pairs with a metric.
- [ ] Decide **one run or N trials** per (case, model) for variance bars.
      Output is stochastic and so now is the investigation *path*. A
      conscious cost/rigor tradeoff, not a default to N=1.
- [ ] Validate end-to-end on the two smallest cases
      (`rdp-remote-file-write`, `ssh-shared-key-overlap`) before running
      14 × every model × every judge — cost multiplies fast and an agentic
      session's cost is far less predictable than a single call's.

## Phase 5 — Reporting

- [ ] One report per target model: domain score, generation score
      (fluency + hallucination), instruction-following (IFEval/Multi-IF),
      cost, latency.
- [ ] **Run outcome is its own column, not folded into a score.** Report
      the distribution across the five-way taxonomy per model — how many
      cases ended in a clean submit, `max_steps_exceeded`,
      `model_context_overflow`, `implicit_no_nudge`, or
      `parse_error_exhausted`. "Model X scored 0.4" and "Model X scored
      0.4 because it never emitted a valid tool call on 6 of 14 cases" are
      different findings, and only the second tells you whether the score
      is about forensics at all.
- [ ] **Report turn count and token usage as first-class efficiency
      metrics**, not just as budget-compliance checks. Two models that both
      answer correctly are not equivalent if one needed 40 tool calls and
      the other 300.
- [ ] **Latency is reported, never a gate** (2026-09-09). Publish it —
      wall-clock per run, TTFT, tool round-trips — but no score depends on
      it. If a deployment-readiness answer is wanted later, it derives from
      these numbers without having contaminated the capability score.
- [ ] **Two latency instruments.** `--collect-perf` is on by default and
      puts per-request latency/TTFT/token usage in the evaluation report,
      so accuracy and latency come from one run (set `stream=true` for
      TTFT). `evalscope perf` is the second, for throughput sweeps — its
      trace-replay datasets are the right load shape for an agentic AUT;
      single-turn QA load would measure the wrong thing.
- [ ] **Locally-served models need a different cost axis.** No API bill, so
      dollar cost is meaningless or a GPU-hour estimate, and one wall-clock
      number hides whether the model or the serving setup was slow. Decide
      how served and API models are presented together without implying
      false equivalence.
- [ ] Dollar cost stays ours to compute — token usage is captured, Phase 0
      supplies the rates. No framework surveyed provides an abort-on-spend
      ceiling; that's a Phase 4 concern.
- [ ] Consider a cost-vs-accuracy Pareto view rather than a single ranked
      list — these are genuinely different axes.
- [ ] Confident AI stays out of scope; local output suffices for a first
      pass. Langfuse is the local option if cross-run tracking gets painful.

## Open questions

Nothing here blocks starting. The Phase 0 spike answers 1-3 directly.

1. **What `max_steps` and token ceiling to set.** Calibration, not design —
   the spike measures it. Default of 10 is an order of magnitude too low.
2. Whether `AgentLoop` degrades at the step count a real corpus search
   needs (the mount is proven; the *depth* is not).
3. Whether EvalScope caps tool output by default — if not, the cap is a
   hard prerequisite for any large case.
4. **Whether models write `QUESTION_ANSWERS.md` incrementally.** Partial
   credit on truncation depends on it and nothing enforces it.
5. Which skills get mounted via `skills_dir`, given the category-leak
   problem.
6. Whether `register_benchmark` works from an external module (no fork).
   Likely yes — it's a plain decorator — but unconfirmed by running it.
7. Target models, pricing source, trials per case.

## Deferred, not dropped

- **Full rubric rollout to all 14 cases** — after Phase 1's pilot shows
  judge-vs-human agreement holds.
- **A security review of whichever framework is adopted, if it isn't
  EvalScope** — we hold a source-level assessment of one candidate and
  none of the others.
- **Vendoring decision for the skills library** (submodule vs. directory
  vs. pinned copy) — `TODO.md` item 3. A pinned copy is the safer default:
  an upstream change to a community-maintained skill silently changes what
  the benchmark measures.
- **Category 2 (Browser History) gap** — tracked in `TEST_OBJECTIVES.md`,
  unrelated to this work.

## Superseded decisions (archive)

Kept so they aren't re-litigated.

- **Single-turn, context-stuffed runner** (2026-09-08 → reversed
  2026-09-09). Assumed evidence would fit in one prompt; the token
  measurements disproved it by orders of magnitude.
- **MCQ conversion** (dropped before 2026-09-08) — risked a distractor set
  leaking the justification answer.
- **Pre-filtering evidence before stuffing** (considered, rejected
  2026-09-09). Even a generous 3-4× reduction from stripping XML verbosity
  leaves most cases far beyond any budget — but the real objection is that
  it tests something narrower and easier than what the cases measure.
- **DeepEval as the settled metrics layer** (2026-09-08 → reopened
  2026-09-09). Chosen while Phase 4 was a single API call. Its own summary
  table conceded that Phase 2's ensemble logic and all of Phase 4 remained
  custom — and those are exactly the phases that grew.
- **Wall-clock SLA as the authoritative stop condition, with breach scored
  FAIL** (2026-09-09 → reversed same day). Rationale at the time: no human
  watches a session, so a wall-clock deadline is the real requirement, and
  a too-slow investigation is a genuine failure rather than a metric to
  normalise away. What broke it: wall-clock isn't reproducible — it's
  confounded by queue depth, rate limiting, host load and parallelism, and
  isn't comparable between self-hosted and API models — so it can't
  underpin a benchmark meant to be re-run over time. Scoring a breach FAIL
  also discarded everything a run did achieve. Replaced by turn count +
  token ceiling with partial credit; latency demoted to a reported metric.
  Two details from the original reasoning survive and are still true: the
  budget should be identical across models, and a token/cost bound is
  needed alongside the primary one.
- **Inspect AI as the recommended harness** (doc-only recommendation,
  2026-09-09 → revised same day). The source-level EvalScope review retired
  the mount risk, surfaced `skills_dir`, and shrank the DAG advantage.
  Inspect's remaining edge is almost entirely its SLA primitives — which is
  why the SLA question now decides the framework.
