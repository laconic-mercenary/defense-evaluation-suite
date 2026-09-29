# d-agent-test

Working umbrella for two independent projects. Right now everything here is
one throwaway git repo (`origin` = `github.com/laconic-mercenary/d-agent-test`,
currently private) that will eventually be split apart — don't push `main`
as more than a private working copy in the meantime.

- **`forensic-agent-tests/`** — DFIR benchmark cases (evidence + task
  instructions) for evaluating LLM agents. Own `README.md`/`AGENTS.md`.
- **`forensic-agent-answers/`** — held-out answer keys, grading rubrics,
  and the full case-building methodology, paired by case slug with
  `forensic-agent-tests/cases/`. Own `README.md`/`AGENTS.md` — **this is
  where case-building work happens**, see its `AGENTS.md`.
- **`EVAL_SUITE_PLAN.md`** — a *draft* plan for turning the manual
  paste-and-grade process into an automated eval harness (agentic runner,
  judge ensemble, cost/latency capture). **Discussion artifact, not a
  build order — no code exists and nothing in it is approved.** It
  proposes a third sibling directory (`eval-harness/`, working name)
  which does not exist yet. Read it before starting any evaluation-tooling
  work, so that work doesn't get re-derived from scratch.

**Known gap, not yet fixed**: the root `.gitignore`'s
`forensic-agent-answers/` entry is comment-only — there's no actual
ignore pattern under it, so despite the intent that this directory stay
out of this repo's history, it has in fact already been committed and
pushed to the (private) `origin` remote above. This is a known, accepted
state pending the actual repo split — see
`forensic-agent-answers/AGENTS.md`'s "Known pitfalls" for detail. Don't
assume the directory boundary is an access-control boundary yet.

**This has a consequence for evaluation runs.** Since a single checkout
holds both the cases and their answer keys, any host that runs an
agent-under-test also holds every `GROUND_TRUTH.json` and
`grading_schema.md` — and the AUT is, by design, an agent handed shell
access and told to search the filesystem. Answer-key disclosure wouldn't
just leak data; it would invalidate every score produced before and after
it, with no signal that anything happened. Until the repo split, physical
separation of the eval host from this checkout is the only real control
available. See `EVAL_SUITE_PLAN.md`'s "Harness security posture".

Eventually each moves into its own permanent repository, at which point this
top-level folder and its `.git` go away.

When that split happens, `EVAL_SUITE_PLAN.md` (and any `eval-harness/`
built from it) needs a home too — it belongs to neither existing project,
since it consumes both. Worth deciding at split time rather than
discovering it then. Its chosen framework, EvalScope, probably does
*not* need a fork: `register_benchmark` is a plain decorator, so an
external module should register. If the Phase 0 spike disproves that, a
vendored fork becomes a *third* thing to re-home.
