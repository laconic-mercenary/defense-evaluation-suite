# AGENTS.md — d-agent-test (umbrella, temporary)

This folder is a **temporary umbrella** holding two projects that are
meant to become fully separate repositories (see `README.md`). Until that
split happens, both live here as sibling directories in one shared git
repo:

- **`forensic-agent-tests/`** — the AUT-facing DFIR benchmark. Its own
  `README.md` and `AGENTS.md` are the entry points for anyone (human or
  agent) working inside it.
- **`forensic-agent-answers/`** — the held-out answer keys, grading
  rubrics, and case-building methodology, paired by slug with
  `forensic-agent-tests/cases/`. Its `AGENTS.md` is the canonical,
  full case-building procedure — **that's where you want to be** if
  you're adding, fixing, or auditing a case. This file doesn't duplicate
  that procedure; go there directly.

**If you're building or maintaining a case, start at
`forensic-agent-answers/AGENTS.md`, not here.** This file exists only to
orient a fresh session to the umbrella structure before it goes to the
repo that actually matters for the task at hand.

There is one workstream that belongs to neither repo:

- **`EVAL_SUITE_PLAN.md`** (this directory) — the plan for automating the
  currently-manual grading process into a full eval pipeline (agentic
  runner, judge ensemble, cost/latency capture). Still a **draft
  discussion artifact beyond what's actually built** — read it first if
  you're asked to work on evaluation tooling, scoring automation, or
  framework selection; it carries dated decisions with their reasoning,
  including two that were later reversed, and re-deriving them wastes the
  record. Don't start building further from it without an explicit
  per-phase go-ahead; that constraint is stated in the file itself and is
  deliberate.
- **`eval-harness/`** (this directory) — a real, working Docker harness
  that runs Hermes (backed by Qwen) against a case, one manual run at a
  time, behind an in-container egress lockdown. This *is* built and
  tested — it's a spike validating the plan's mechanics, not the
  automated pipeline `EVAL_SUITE_PLAN.md` still describes as future work.
  See `HERMES_QUICKSTART.md` (this directory) to run it; see
  `eval-harness/docker/*.sh` for how it actually works.

Once the two projects actually split into separate repositories, this
file and `d-agent-test/`'s `.git` go away — don't add new durable content
here that would need migrating; put it in whichever of the two repos it
actually belongs to.
