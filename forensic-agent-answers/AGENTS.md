# AGENTS.md — forensic-agent-answers

This repo holds the held-out material for `forensic-agent-tests`: answer
keys, grading rubrics, case-building methodology, generator inputs, and a
vendored reference copy of the generator itself. **Nothing in this repo is
ever meant to reach an agent-under-test (AUT).** If you're an AUT assigned
a specific case, you should not be reading this file at all — go to the
paired `forensic-agent-tests` repo instead.

**Repo-layout convention assumed throughout this doc and `doc/`:**
`forensic-agent-tests` and `forensic-agent-answers` are checked out as
sibling directories on disk (`.../forensic-agent-tests/`,
`.../forensic-agent-answers/`, same parent). Relative paths below
(`../forensic-agent-tests/...`) assume this. If your checkout differs,
adjust paths accordingly — the logical structure they describe doesn't
change.

This doc is the procedure for going from "an idea for a case" to a graded
case split across both repos. Companion docs, all in `doc/` in this repo:

- `doc/TEST_OBJECTIVES.md` — category definitions, example scenarios,
  related skills/sources per category.
- `doc/TEST_CASE_MATRIX.md` — what's already covered, what isn't (the
  authoritative as-built coverage record).
- `doc/TEST_CASE_PROCESS.md` — the ordered Phase 0-7 checklist this doc's
  Phase 1/2 mechanics plug into.
- `doc/SOURCES.md` — what can supply or generate evidence, and its status.
- `doc/TEST_EVIDENCEFORGE_PROPOSED_CASES.md` — the original ten-case
  EvidenceForge proposal menu (now all built; kept as historical design
  record).

**Scenario generation happens outside both repos, in a real EvidenceForge
checkout**: `/Users/mlcs/Documents/github/EvidenceForge` —
[Cisco-Talos/EvidenceForge](https://github.com/Cisco-Talos/EvidenceForge)
(MIT). Do all authoring/iteration there, not in either repo. Only
finished, validated scenarios get ported over.

## Phase 1 — Generate a scenario in EvidenceForge

```bash
cd /Users/mlcs/Documents/github/EvidenceForge
uv sync                          # first time / after a pull — see "Environment setup" below
uv run eforge validate scenarios/<slug>/scenario.yaml
uv run eforge generate scenarios/<slug>/scenario.yaml --verbose --force
uv run eforge eval scenarios/<slug>/data --scenario scenarios/<slug>/scenario.yaml --verbose   # optional
```

Use that checkout's own `eforge-scenario`/`eforge-generate`/`eforge-validate`/
`eforge-evaluate` skills for authoring — don't re-derive scenario schema from
memory or from the vendored copy in `EvidenceForge/` in this repo (stale,
see "Known pitfalls" below).

Before moving to Phase 2, record: the scenario slug, the `generation_seed`
(in `data/COLLECTION_PROFILE.json` after generation), and the EvidenceForge
commit (`git -C /Users/mlcs/Documents/github/EvidenceForge rev-parse HEAD`
plus the version in `pyproject.toml`). These three facts are the only
non-rederivable provenance — everything else in the output can be
regenerated from the scenario file.

### Environment setup (if `uv sync` fails)

On this machine, `uv sync` needs a working Rust toolchain to compile
`cryptography` from source (no prebuilt wheel for this platform/Python
combination). If it fails with `openssl-sys` / `pkg-config not found`:

```bash
brew install pkgconf openssl@3
export PKG_CONFIG_PATH="$(brew --prefix openssl@3)/lib/pkgconfig:$PKG_CONFIG_PATH"
cd /Users/mlcs/Documents/github/EvidenceForge && uv sync
```

## Phase 2 — Port a generated scenario into both repos

Never point an agent-under-test at anything generated directly in the
EvidenceForge checkout. Every port-over goes through this checklist, in
order — steps 3 and 4 exist because skipping them has already shipped a
real answer leak once.

1. **Copy the generator input.** `scenario.yaml` only (not `ENVIRONMENT.md`
   — that's case content, see step 2) into
   `generators/evidenceforge/<slug>/scenario.yaml` **in this repo**, plus
   a `README.md` recording the EvidenceForge version/commit, the seed,
   and the exact `eforge generate` command to reproduce it. This never
   goes in `forensic-agent-tests` — a `scenario.yaml` is effectively the
   ground truth in YAML form (the exact storyline every exam question is
   graded against), so it belongs with the held-out answer material.

2. **Split the generated output.**
   - `data/` (the logs) + `ENVIRONMENT.md` →
     `../forensic-agent-tests/cases/<slug>/data/`
   - `GROUND_TRUTH.md`, `GROUND_TRUTH.json`, `KNOWN_DEFICIENCIES.md` →
     `case-<slug>/supporting/` in this repo.
   - `COLLECTION_PROFILE.json`, `OBSERVATION_MANIFEST.json`,
     `OUTPUT_TARGET.txt` → **do not carry these into `cases/`.** See "Known
     pitfalls" below. If a future EvidenceForge version needs one of these
     for something legitimate, re-derive the decision fresh against that
     version's actual field content — don't assume the pattern still holds.

3. **Audit the entire intended `forensic-agent-tests/cases/<slug>/` tree**
   (not just `data/`) before writing anything else:
   - grep case-insensitive for `evidenceforge|eforge|cisco.?talos|talos` —
     zero hits anywhere the AUT can read, including `README.md` and
     `CHANGELOG.md`, not just `data/`.
   - grep for `"storyline_id"|"kind": *"red_herring"|"activity":` — a
     narrative/answer leak pattern. Any match means that file does not
     belong in `cases/<slug>/`, regardless of what it's named or what its
     schema is documented to be for.
   - Don't trust a sidecar file's stated purpose over its actual rendered
     content for this specific scenario — read it.

4. **Verify claims against the raw data, not against `GROUND_TRUTH.md`
   alone** before writing a grading key. EvidenceForge's own ground truth
   can diverge from what's actually rendered (e.g. `rdp-remote-file-write`'s
   ~21-minute timing gap between the authored offset and the rendered
   `4624`/Sysmon evidence). Pull exact timestamps/fields/identifiers from
   the log files themselves.

5. **Write the case bundle** in
   `../forensic-agent-tests/cases/<slug>/`: `README.md` (human-facing, no
   provenance/brand mentions), `AGENTS.md` (thin router + evidence index,
   also no provenance), `TASK.md`, `EXAM.md` (questions only, no framing),
   `CHANGELOG.md`, `.gitignore` (containing `QUESTION_ANSWERS.md`).

6. **Write the answer bundle** in `case-<slug>/` in this repo:
   `BRIEFING.md` (true story, decoys, undetermined facts, known evidence
   quirks), `grading_schema.md` (per-question rubric, 1:1 with `EXAM.md`),
   and the grader instructions split in two:
   - `AGENTS.md`: read verbatim by the automated judge, which grades one
     rubric entry at a time. Only the safety note and case-specific
     grading guidance. No Inputs or Output sections, no references to
     files the judge doesn't receive (`EXAM.md`, `supporting/`), and refer
     to "the rubric entry", not `grading_schema.md`.
   - `README.md`: the manual grading workflow (Inputs, Output, and any
     case-level summary a person should write).

7. **Sanity-check every exam question against the raw data for internal
   contradictions** before finalizing — mismatched process lineage, causal
   ordering that doesn't hold up, fields that contradict `ENVIRONMENT.md`.
   A question resting on self-contradictory evidence isn't hard, it's
   broken. Reword if the fix doesn't change what's being tested; drop the
   question and let a broader one (e.g. full timeline reconstruction)
   absorb its intent if not; hold the whole case out of active use if the
   contradiction sits on more than one graded fact. Don't paper over a data
   problem with grading-key language alone.

8. **Update `../forensic-agent-tests/README.md`'s case table** and
   `doc/TEST_CASE_MATRIX.md` in this repo.

## Known pitfalls (read before repeating any of this work)

- **This repo (`forensic-agent-answers`) and `forensic-agent-tests` both
  currently live in one shared umbrella git repo** (`d-agent-test`, on a
  private GitHub remote), not yet split into two separate repos — despite
  the intent that they should be. The root `.gitignore`'s
  `forensic-agent-answers/` entry there is comment-only (no actual ignore
  pattern), confirmed via `git check-ignore`, so this repo's content has
  in fact already been committed and pushed to that shared remote's
  history. This is a known, accepted state: prior explicit instruction
  was not to remediate it (no `git rm --cached`, no history purge, no
  fixing the pattern) — the intended fix is a future manual hand-pick
  into two properly separated repos, not something to do unilaterally.
  Once that split actually happens, this note becomes historical —
  update it then, don't carry it forward unchanged.
- The vendored `EvidenceForge/.agents/skills/` copy in this repo is stale
  relative to the live checkout — current EvidenceForge ships skills
  under `commands/eforge/*.md`, not `.agents/skills/eforge-*/`, and the
  vendored `scenario-reference.md` is behind by dozens of lines. Don't
  treat it as authoritative; it's kept for rough reference only.
- A case can look internally consistent in `GROUND_TRUTH.md` and still be
  wrong in the rendered data — cross-source timing/identity fields
  (process parent images, domain/SID fields, event ordering at sub-second
  granularity) have shipped real contradictions before (mismatched
  parent-process binary vs. declared `services`, a domain-style SID in a
  scenario declaring no AD, an effect rendered before its cause). Spot-check
  the fields a graded question actually depends on, not just whether
  `eforge validate`/`eforge eval` passed.
- `grep -a` on a binary artifact (`.evtx` and similar) is not a reliable
  leak audit — binary EVTX stores text as UTF-16 inside a compressed
  structure, and ASCII grep only catches some substrings by accident, not
  all of them (`windows-log-search-basics` shipped with an undetected
  bare-brand-name and a plaintext-password leak inside two `.evtx` files
  because the original audit only checked `grep -a` against the binary).
  To actually audit binary evidence, convert it to text first (e.g.
  `evtx_dump -o jsonl`), grep the converted text, then decide from there.
- When transcribing an answer key from source material that includes
  screenshots (Event Viewer, a UI, anything rendering a timestamp), the
  displayed time may be in the *screenshot tool's local timezone*, not
  UTC — even when the underlying raw data field genuinely is UTC.
  `windows-log-search-basics` shipped with every timestamp in its answer
  key wrong by exactly 9 hours (JST vs. UTC) because the transcription
  copied times straight off the source PDF's screenshots without
  cross-checking the raw data's own timestamp field. This is the same
  "verify against raw data, not the narrative" rule already in this list,
  but the failure mode is easy to miss specifically because a screenshot
  *looks like* raw data — it isn't. Always independently pull the
  timestamp from the actual evidence file's own timezone-stamped field
  before writing it into `BRIEFING.md`/`grading_schema.md`, especially for
  any source not authored in UTC-adjacent timezones.
- **`CHANGELOG.md` (in the `forensic-agent-tests` case bundle) is the file
  most likely to leak something**, not `README.md`/`AGENTS.md`/`EXAM.md`.
  It has happened four separate times across this project — brand name
  twice, a case's decoy account names once, a brand name a fourth time in
  a later case — always writing it last, in "explain what I just did"
  narrative mode, pulls in whatever's fresh in context (a brand name, a
  decoy account, an internal detail) without the same scrutiny applied to
  the more obviously AUT-facing files. Run the leak grep on `CHANGELOG.md`
  specifically, every time, even when the rest of the case tree is
  already clean.
- Baseline-generated "legitimate" cross-segment traffic does not
  appear to be fully gated by a scenario's declared firewall
  `policy:` rules the way explicitly-authored storyline/scan traffic
  is — confirmed in `websqli-webshell-pivot`, where the declared
  policy listed exactly one DMZ→internal exception (port 445) but the
  rendered `cisco_asa.log` also showed baseline monitoring-style
  traffic (health-check polling, ICMP, background SSH noise) crossing
  the same boundary on other ports the policy never listed. By
  contrast, `external-recon-no-breach`'s firewall cleanly gated all of
  that scenario's (fully attacker-authored) port-scan traffic. Don't
  assume a declared `policy:` block is the sole source of truth for
  what crosses a segment boundary in the rendered data — check the
  actual ASA/Zeek output for baseline noise before writing an
  `ENVIRONMENT.md` claim like "no other traffic is permitted."
- **Never use the `adversarial_payload` storyline event type in any case
  whose evidence reaches the agent-under-test.** It is a hard,
  unconditional safety guardrail in the engine itself (see
  `src/evidenceforge/config/activity/payload_families.yaml`'s
  `default_marker`): every payload it renders — regardless of family,
  surface, or scenario content — carries the literal string
  `EFORGE_TEST` on every line, by design, with no way to disable it.
  That string directly matches this project's own leak-audit grep
  (`evidenceforge|eforge`) and would appear in whatever surface the
  payload is injected into (a URL, a user agent, a syslog line, a
  process command line). Model attacker-controlled HTTP/log content a
  different way instead — e.g. a plain `connection` event with
  `service: http` and a hand-written URI/query string carrying the
  injection shape you want (SQLi, XSS, log-forging, etc.) — which gives
  full control over the rendered content and carries no such marker.
- A leak grep on a raw file only catches plaintext substrings — it does
  not see anything hiding behind an encoding. `phishing-c2-beacon`'s
  generated `.eml` email artifact had a synthetic attachment body whose
  base64-encoded filler content, once decoded, spelled out the
  scenario's own storyline event ID in plain text
  (`email-attachment:evt-phish-001-...`) — a raw-text grep against the
  `.eml` file found nothing, because the string only exists after
  base64 decoding. Same category of miss as the `grep -a`-on-binary-EVTX
  pitfall above, different encoding. Before porting any generated
  artifact that carries base64/hex/other encoded binary content
  (`.eml` files, attachments, anything with a `Content-Transfer-Encoding:
  base64` part) into a case's AUT-facing `data/`, decode and inspect it
  first — don't trust a clean grep on the raw file.
- `AuthenticationPackageName` (Kerberos vs. NTLM) on rendered network
  logons is a fixed 70/30 random roll in this engine version
  (`_select_auth_package` in
  `src/evidenceforge/generation/activity/generator.py`), completely
  independent of whether the account is domain- or local-scoped.
  Confirmed by reading the engine source after `pth-lateral-logclear`'s
  first design (a local-admin credential meant to render reliably as
  NTLM, distinguishing it from Kerberos-authenticated legitimate
  traffic) produced a near-random mix instead — only 1 of 6 attacker
  logon events came out NTLM. There is no scenario-authoring path to
  force deterministic auth-package rendering for a specific account;
  design the exam around the account's identity/timing pattern
  instead, and treat any auth-package observation as a secondary,
  non-required signal at most.
- `log_cleared` does not remove any preceding events from the affected
  host's own rendered log in this engine version — it is purely
  additive (adds the Event ID 1102 record without suppressing anything
  before it). Confirmed independently in both `pth-lateral-logclear`
  and `dga-beacon-logclear`: the host's own prior evidence (a logon,
  a process-creation event) remained fully present and citable after
  the clear. Don't design a case around "this evidence is now
  destroyed" without verifying that claim directly against the
  rendered output first — instead, a good use of this event type is
  testing whether the agent-under-test *verifies* the clear's actual
  effect rather than assuming a clear attempt necessarily succeeded.
- Declaring an account under `environment.service_accounts` reliably
  produces baseline Event ID 4648 ("explicit credential usage") noise
  from `SYSTEM`-context automated processes (`taskhostw.exe`,
  `ops-agent.exe`, and — confirmed in `rogue-service-account-privcreep`
  — sometimes `powershell.exe` too) — and this noise is **not confined
  to the one host you'd narratively expect**. Confirmed across four
  cases (`credential-spray-domain-compromise`, `pth-lateral-logclear`,
  `benign-breakglass-account`, `rogue-service-account-privcreep`): the
  noise consistently spans *every* host in the environment the account
  has any plausible reason to touch, not just the one server hosting its
  "documented" job. An early answer-key draft for
  `rogue-service-account-privcreep` listed only 3 of the actual 4 hosts
  carrying this noise and claimed the process name alone was a reliable
  discriminator — both wrong, caught by an independent audit. When
  characterizing this baseline for an exam, check **every** host in the
  scenario, not just the obvious one, and confirm which field (usually
  `SubjectUserName`, not `ProcessName` or `IpAddress`) is actually the
  reliable signal by checking what baseline noise renders, not by
  assuming it from the process names the scenario happens to reference.
- Any `roles:` assignment can trigger the engine's own built-in
  "legitimate lateral movement" baseline patterns
  (`src/evidenceforge/config/activity/network_params.yaml`) connecting
  hosts by role pairing (e.g. any `web_server`-role host automatically
  gets baseline SMB traffic to any `file_server`-role host, modeled as
  a content-publishing pattern) — confirmed in `websqli-webshell-pivot`,
  where this silently generated realistic-looking "legitimate" traffic
  toward a host a case's premise required to have no legitimate
  visitors at all. If a case's design depends on a host having *no*
  baseline traffic from a particular role, don't just declare the
  target's role and assume — generate once, grep the rendered
  ASA/Zeek/Windows output for unexpected connections to that host, and
  remove the role (or pick a target role with no such pairing) if the
  premise doesn't hold.
- When delegating an audit (or any read-only investigation) of a case with
  compressed evidence (`.tar.gz` in `data/`), don't instruct the agent to
  unpack with `-C data/` — that leaves raw, uncompressed evidence sitting
  in the real case directory afterward, undoing the compression and
  getting staged alongside the compressed originals on the next
  `git add`. This happened twice in one session. Either tell the agent to
  unpack into a scratch/temp location instead, or explicitly tell it to
  clean up its extraction when done, and always `git status`/`ls` the
  case's `data/` directory after any delegated audit completes, before
  staging anything.
