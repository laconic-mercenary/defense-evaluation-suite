#!/usr/bin/env bash
# Copies three read-only mounts (bound `:ro` at `docker run` time) into
# plain writable, container-local directories before handing off to Hermes:
#   /case-src          -> /case                case evidence (see run-case.sh)
#   /hermes-config-src -> $HERMES_HOME          your own pre-configured ~/.hermes
#   /skills-src         -> $HERMES_HOME/skills   whatever skills you want indexed
# Same reason for all three: the case files tell the agent to write
# QUESTION_ANSWERS.md "in this directory," and Hermes needs to write its
# own session/runtime state (including installing/indexing skills) --
# neither works against a `:ro` mount. Neither host original is ever
# touched; this container is discarded after one run, so nothing written
# during it persists back.
#
# A fourth mount, /output, goes the other way -- read-write, so this run's
# QUESTION_ANSWERS.md and trace actually escape the container instead of
# being deleted with it (`docker run --rm`). See the bottom of this file.
#
# This deliberately does not know anything about Hermes's config schema
# (config.yaml, provider: custom, etc.) -- point HERMES_CONFIG_DIR (see
# run-case.sh) at a directory you've already configured with Hermes's own
# `hermes setup` / `hermes model`, and whatever you built is what runs here.
# Same philosophy for SKILLS_DIR: whatever skill folders are in there get
# copied in and indexed, no curation or filtering done by this script.
#
# All three mounts are required and hard-fail if missing -- a silently-
# skipped copy would mean running against no evidence, an unconfigured
# Hermes, or no skills, which looks like a normal session and isn't. Not
# caught by `set -e` on its own: `[ -d ... ]` failing doesn't abort the
# script, it's a false branch, so absence has to be checked and exited on
# explicitly.
set -euo pipefail

if [ ! -d /case-src ]; then
  echo "entrypoint: /case-src not mounted -- run-case.sh should have passed -v <case dir>:/case-src:ro" >&2
  exit 1
fi
cp -a /case-src/. /case/

if [ ! -d /hermes-config-src ]; then
  echo "entrypoint: /hermes-config-src not mounted -- set HERMES_CONFIG_DIR (see .env.example)" >&2
  exit 1
fi
cp -a /hermes-config-src/. "${HERMES_HOME}/"
# Accepted risk, not an oversight: this puts the real model-endpoint
# credential (e.g. MODAL_API_KEY) inside the same filesystem the --yolo
# agent has full bash access to. Hermes's own secret redaction (on by
# default -- agent/redact.py's _is_secret_file_arg treats any .env-named
# file, and config.yaml under $HERMES_HOME, as secret-bearing, masking
# KEY=value reads before they reach the model's context) covers the
# realistic case -- an agent incidentally reading its own config while
# exploring. It's explicitly "defense-in-depth, not a boundary" per that
# same source: a deliberately evasive read (piping through another tool,
# reading byte ranges, etc.) isn't caught. Acceptable for this manual,
# human-supervised spike; revisit (a bridge process holding the real
# credential outside this container entirely) before this becomes the
# automated, less-supervised harness run against an untrusted AUT.

# Whatever's in SKILLS_DIR (see run-case.sh) gets copied in as-is and
# indexed by Hermes -- no filtering here. Hermes builds a compact per-skill
# line (name + truncated description) into the system prompt for every
# skill it finds under $HERMES_HOME/skills/, and loads a skill's full
# content only on demand (skill_view), so what's indexed is entirely a
# function of what's physically in this directory -- curating that is on
# you, same as HERMES_CONFIG_DIR's contents are.
if [ ! -d /skills-src ]; then
  echo "entrypoint: /skills-src not mounted -- run-case.sh should have passed -v <SKILLS_DIR>:/skills-src:ro" >&2
  exit 1
fi
mkdir -p "${HERMES_HOME}/skills"
cp -a /skills-src/. "${HERMES_HOME}/skills/"

# Always runs, no on/off toggle. `hermes dashboard` (config/API-key/session
# management -- it does NOT stream the live chat session below) defaults to
# --host 127.0.0.1, which a container's published port cannot reach at all
# (loopback is per network-namespace). --host 0.0.0.0 is required for
# `docker run -p` to work -- but Hermes enforces, on purpose, that "a
# non-loopback bind always requires an auth provider," and refuses to start
# otherwise for any non-interactive caller (Docker has no TTY). Set
# HERMES_DASHBOARD_BASIC_AUTH_USERNAME/_PASSWORD_HASH/_SECRET (see
# run-case.sh / .env.example) or this will exit with an error -- that is
# Hermes's fail-closed behavior working as intended, not a bug here.
read -ra dashboard_args <<< "${HERMES_DASHBOARD_ARGS:-}"
hermes dashboard \
  --host 0.0.0.0 \
  --port "${HERMES_DASHBOARD_PORT:-9119}" \
  --no-open \
  "${dashboard_args[@]}" &

# Not `exec "$@"` -- deliberately. exec would replace this process with
# hermes chat, so nothing below (copying the answer out, exporting the
# trace) would ever run: exec never returns. Capturing the exit code
# instead of letting `set -e` abort on a non-zero one, since a failed or
# truncated run still needs its partial QUESTION_ANSWERS.md/trace copied
# out -- "the run failed" and "we lost the output" are different problems.
set +e
"$@"
HERMES_EXIT_CODE=$?
set -e

# /output is a plain read-write bind mount to a host directory run-case.sh
# creates per test run (see its RUN_DIR/testrun_* logic) -- world-writable
# on the host side specifically so this works regardless of which UID this
# container runs as or whether docker itself runs under sudo, rather than
# trying to match UIDs across the container/host boundary.
if [ -d /output ]; then
  if [ -f /case/QUESTION_ANSWERS.md ]; then
    cp /case/QUESTION_ANSWERS.md /output/QUESTION_ANSWERS.md
  else
    echo "entrypoint: /case/QUESTION_ANSWERS.md missing at exit (exit code $HERMES_EXIT_CODE) -- nothing to copy out" >&2
  fi
  # --format trace (a "Claude Code JSONL trace export," confirmed in
  # hermes_cli/sessions_cmd.py) with no --session-id resolves to "the last
  # thing I did" -- the most recently active session -- which in this
  # single-use, single-session container is always the run above. Failure
  # here shouldn't mask a real hermes chat failure, so it's logged, not
  # fatal.
  if ! hermes sessions export --format trace /output/trace.jsonl; then
    echo "entrypoint: hermes sessions export failed -- no trace captured for this run" >&2
  fi
else
  echo "entrypoint: /output not mounted -- QUESTION_ANSWERS.md and the trace stay trapped in this container. Set up RUN_DIR in run-case.sh." >&2
fi

exit "$HERMES_EXIT_CODE"
