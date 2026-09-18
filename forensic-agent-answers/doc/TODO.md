## TODOs

1. Develop a scoring rubric system
   - Planned in `../../EVAL_SUITE_PLAN.md` (Phase 1). Still draft — not
     approved for implementation, and no code exists yet.
2. Run rubric against 3 frontier models and produce report
   - Same plan, Phases 4-5. Note the runner is now agentic/tool-using, not
     single-turn: 12 of 14 cases exceed every current model's context
     window (largest is 43.6M tokens / 120MB uncompressed), so evidence
     cannot be pasted into a prompt. Blocked on Phase 0's framework
     decision. Note the case count is **14**, not 13 — the plan said 13 in
     prose while its own table listed 14; verified against disk
     2026-09-09, both repos paired with no orphans.
3. Determine how to handle anthropic-skills loading (git submodule,
   seperate directory, etc)
   - **Consumption mechanism found** (2026-09-09): if the harness lands on
     EvalScope, `NativeAgentConfig(skills_dir=...)` points at host folders
     containing `SKILL.md` and needs no scaffold. That settles *how* the
     AUT reads them; it does **not** settle vendoring (submodule vs.
     directory vs. pinned copy), which is still open — and the library is
     a third-party community project, so a pinned copy is the safer
     default. Open question raised in `EVAL_SUITE_PLAN.md` Phase 4:
     mounting a category-matched subset of the 818 skills would leak which
     of the nine categories a case belongs to. **Decided 2026-09-18: all
     818 are mounted, for every case.** The AUT is now Qwen on the Hermes
     harness via EvalScope's external runner, which also accepts
     `skills_dir`. Vendoring is still open.
4. Develop tests that also include the browser history
   - Category 2, unchanged. Tracked in `TEST_OBJECTIVES.md`; explicitly
     out of scope for the eval-suite work.
