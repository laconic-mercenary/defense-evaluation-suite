# d-agent-test

A DFIR benchmark for evaluating LLM agents, plus a Docker harness to run
one against it.

Cases hand an agent realistic evidence (Windows/Linux logs, network
traffic, email) and grade it on reconstructing events, identifying the
actor, judging whether it was malicious, and reporting soundly. Answer
keys live in a separate directory the agent-under-test never sees.

Umbrella for two independent projects plus the harness connecting them —
one shared private git repo for now, splitting into separate repos later.
Don't push `main` as more than a working copy.

## Start here

| You are... | Go to |
|---|---|
| A human running an agent against a case | [`HERMES_QUICKSTART.md`](HERMES_QUICKSTART.md) ([日本語版](HERMES_QUICKSTART.jp.md)) |
| A human building/fixing/auditing a case | [`forensic-agent-answers/AGENTS.md`](forensic-agent-answers/AGENTS.md) |
| A human wanting the case set and what each tests | [`forensic-agent-tests/README.md`](forensic-agent-tests/README.md) |
| An **agent-under-test** assigned a case | `forensic-agent-tests/cases/<slug>/AGENTS.md` — nothing else here |
| An **agent** doing general work in this repo | [`AGENTS.md`](AGENTS.md) |
| Anyone wanting the full automated-pipeline plan | [`EVAL_SUITE_PLAN.md`](EVAL_SUITE_PLAN.md) — draft, beyond the spike below |

**Agents-under-test**: read only your case's `AGENTS.md`. Never read
`forensic-agent-answers/` — see Status below for what does and doesn't
enforce that.

## Layout

- **`forensic-agent-tests/`** — the benchmark: 14 self-contained cases,
  evidence + task instructions only.
- **`forensic-agent-answers/`** — held-out answer keys and case-building
  methodology, paired by slug. Case-building work happens here.
- **`eval-harness/`** — Docker harness running Hermes/Qwen against a case,
  egress-locked. A manual spike, not the automated pipeline. See
  `HERMES_QUICKSTART.md`.
- **`EVAL_SUITE_PLAN.md`** — draft plan for the full automated pipeline
  `eval-harness/` is a step toward. Read before further eval-tooling work.
- **`HERMES_QUICKSTART.md`** (日本語版: `HERMES_QUICKSTART.jp.md`) — steps
  to actually run a case.

## Sources

Case evidence comes from two places:

- **[EvidenceForge](https://github.com/Cisco-Talos/EvidenceForge)** (Cisco
  Talos, MIT) — synthetic evidence generator, used for most cases.
- **[JPCERT/CC](https://github.com/JPCERTCC/log-analysis-training_v2)** —
  Japan's national CERT; two cases (`windows-log-search-basics`,
  `windows-lateral-movement-ntds-exfil`) use real JPCERT-published
  training data instead of synthetic evidence.

Full sourcing detail, licensing, and candidate/rejected sources:
`forensic-agent-answers/doc/SOURCES.md`.

## Status & caveats

**Answer keys aren't access-controlled, just conventionally separated.**
`forensic-agent-answers/` is meant to be gitignored but isn't (a
comment-only pattern) — it's already in this repo's history. Known,
pending the split.

**`eval-harness/` contains part of the blast radius**: its container only
ever mounts one case's evidence, never `forensic-agent-answers/`, and
can't reach the network beyond its model endpoint. Outside that container,
on this checkout, both directories still sit side by side — full
separation waits on the repo split.

**At split time**, `EVAL_SUITE_PLAN.md`, `eval-harness/`, and
`HERMES_QUICKSTART.md` all need new homes too — none belongs to either
existing project.
