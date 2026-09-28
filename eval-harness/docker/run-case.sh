#!/usr/bin/env bash
# Manual spike runner: build (if needed) and run the Hermes/Qwen container
# against one case, evidence mounted read-only. Interactive/attached by
# design -- see EVAL_SUITE_PLAN.md Phase 0. You're meant to watch this run,
# not automate it yet. `--oneshot` on the hermes chat invocation below is
# still required despite that, though -- without it, `-q` only seeds the
# first turn and the session stays open afterward waiting for more input
# that never comes, so the container never exits and entrypoint.sh's
# QUESTION_ANSWERS.md copy / trace export (both running after hermes chat
# returns) never execute either. Confirmed the hard way: a run that
# finished its investigation and wrote its answer sat alive for 8+ minutes
# with nothing reaching /output, `docker top` showing the hermes process
# still running. You can still watch the whole thing live via -it; this
# only changes whether it exits on its own once it's actually done.
#
# Requires HERMES_SRC_DIR to point at a local NousResearch/hermes-agent
# clone, checked out to whatever commit you want built (see
# Dockerfile.hermes -- there is no separate pin inside this script).
#
# Config is read from a .env file next to this script (see .env.example),
# or from already-exported environment variables -- either works, and an
# exported variable overrides the same name in .env. Usage:
#   cp .env.example .env && edit it, then:
#   ./run-case.sh rdp-remote-file-write     # doc's chosen first spike case
#
# This script deliberately knows nothing about Hermes's own config schema
# (config.yaml, provider: custom, etc.) -- HERMES_CONFIG_DIR points at a
# directory you've already configured with Hermes's own `hermes setup` /
# `hermes model` (run natively, e.g. via `uv run` in HERMES_SRC_DIR; set
# HERMES_HOME when doing so if you don't want to touch your real ~/.hermes).
# Switching dev (Modal) vs prod (on-prem) is maintaining two such
# directories and pointing this at whichever.
#
# The web dashboard (`hermes dashboard`, config/API-key/session management --
# NOT a live view of the chat session) always runs, no toggle. See
# .env.example for the auth variables it requires -- Hermes refuses to bind
# non-loopback without them.
#
# Every run's output (QUESTION_ANSWERS.md, a trace export -- see
# entrypoint.sh) lands in eval-harness/runs/<case-slug>/testrun_<agent
# id>_<case-slug>_<unix timestamp>/, gitignored, printed at the end of a
# run. Set AGENT_ID to label runs from a specific model/config; defaults
# to "hermes".
#
# Every check below runs before docker build/run -- nothing here starts a
# build only to fail on a bad input three steps in.

set -euo pipefail

fail() { echo "run-case.sh: $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ENV_FILE explicitly set to a bad path is a mistake worth failing on; the
# default simply not existing yet (first run, or relying on already-
# exported variables instead) is not.
ENV_FILE_WAS_EXPLICIT="${ENV_FILE:-}"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090,SC1091
  source "$ENV_FILE"
  set +a
elif [ -n "$ENV_FILE_WAS_EXPLICIT" ]; then
  fail "ENV_FILE=$ENV_FILE does not exist"
fi

# --- Case slug -------------------------------------------------------------
CASE_SLUG="${1:?usage: run-case.sh <case-slug>}"
if ! [[ "$CASE_SLUG" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  fail "case slug '$CASE_SLUG' doesn't look like one (expected lowercase letters/digits/hyphens, e.g. rdp-remote-file-write)"
fi
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CASE_DIR="$REPO_ROOT/forensic-agent-tests/cases/$CASE_SLUG"
if [ ! -d "$CASE_DIR" ]; then
  fail "no such case: $CASE_DIR"
fi

# --- Run output --------------------------------------------------------------
# eval-harness/runs/, not inside either forensic-agent-tests or
# forensic-agent-answers -- transcripts/output are an eval-harness concern,
# not case content, and forensic-agent-tests' own boundary ("evidence +
# task instructions only") stays untouched. AGENT_ID has no source of truth
# to pull from here (HERMES_CONFIG_DIR is an opaque directory to this
# script by design -- see the header), so it's a plain override with a
# generic default, not something auto-detected.
AGENT_ID="${AGENT_ID:-hermes}"
TESTRUN_ID="testrun_${AGENT_ID}_${CASE_SLUG}_$(date +%s)"
RUN_DIR="$REPO_ROOT/eval-harness/runs/$CASE_SLUG/$TESTRUN_ID"
mkdir -p "$RUN_DIR"
# World-writable, deliberately: this container's own user (fixed at
# hermes:1000 in the image) or a completely different host UID if docker
# itself runs under sudo -- see entrypoint.sh's comment on why this is
# simpler and more robust than trying to match UIDs across that boundary.
chmod 777 "$RUN_DIR"

# --- Hermes source (for the image build) -----------------------------------
: "${HERMES_SRC_DIR:?set HERMES_SRC_DIR to a local NousResearch/hermes-agent clone}"
if [ ! -d "$HERMES_SRC_DIR" ]; then
  fail "HERMES_SRC_DIR does not exist: $HERMES_SRC_DIR"
fi
if [ ! -f "$HERMES_SRC_DIR/pyproject.toml" ]; then
  fail "HERMES_SRC_DIR ($HERMES_SRC_DIR) has no pyproject.toml at its root -- doesn't look like a hermes-agent checkout"
fi

# --- Hermes config -----------------------------------------------------------
# A directory you've already pointed at your dev or prod endpoint using
# Hermes's own tooling -- see the header comment. entrypoint.sh copies it
# into $HERMES_HOME read-write (the mount below stays read-only, your real
# directory is never modified) before Hermes starts.
: "${HERMES_CONFIG_DIR:?set HERMES_CONFIG_DIR to a directory configured via hermes setup / hermes model}"
if [ ! -d "$HERMES_CONFIG_DIR" ]; then
  fail "HERMES_CONFIG_DIR does not exist: $HERMES_CONFIG_DIR"
fi
if [ -z "$(ls -A "$HERMES_CONFIG_DIR" 2>/dev/null)" ]; then
  fail "HERMES_CONFIG_DIR is empty: $HERMES_CONFIG_DIR -- run hermes setup / hermes model against it first"
fi

# --- Skills -------------------------------------------------------------------
# A directory of skill folders (each with its own SKILL.md) to hand to
# Hermes as-is -- this script doesn't filter, curate, or care how many are
# in there. Whatever's present gets indexed by Hermes; populating the
# directory (e.g. copying specific skills out of a
# mukul975/anthropic-cybersecurity-skills clone -- independent community
# project, not Anthropic-affiliated despite the name, see
# forensic-agent-answers/doc/TEST_OBJECTIVES.md) is on you, same as
# HERMES_SRC_DIR's commit is on you.
: "${SKILLS_DIR:?set SKILLS_DIR to a directory of skill folders (see .env.example)}"
if [ ! -d "$SKILLS_DIR" ]; then
  fail "SKILLS_DIR does not exist: $SKILLS_DIR"
fi
if [ -z "$(ls -A "$SKILLS_DIR" 2>/dev/null)" ]; then
  fail "SKILLS_DIR is empty: $SKILLS_DIR"
fi

# --- Dashboard ---------------------------------------------------------------
# Confirmed against Hermes's own docs: real defaults are --host 127.0.0.1,
# --port 9119. A container's published port cannot reach a loopback-bound
# process at all (separate network namespace), so the entrypoint always
# passes --host 0.0.0.0 -- which means Hermes's fail-closed rule kicks in:
# "a non-loopback bind always requires an auth provider," and it refuses to
# start for any non-interactive caller (Docker has no TTY) without one
# configured. No on/off toggle: it always runs, so its three auth vars are
# required, not optional -- checked here rather than left to fail inside
# the container after a full build.
HERMES_DASHBOARD_PORT="${HERMES_DASHBOARD_PORT:-9119}"
if ! [[ "$HERMES_DASHBOARD_PORT" =~ ^[0-9]+$ ]] || [ "$HERMES_DASHBOARD_PORT" -lt 1 ] || [ "$HERMES_DASHBOARD_PORT" -gt 65535 ]; then
  fail "HERMES_DASHBOARD_PORT='$HERMES_DASHBOARD_PORT' is not a valid port (1-65535)"
fi
: "${HERMES_DASHBOARD_BASIC_AUTH_USERNAME:?set HERMES_DASHBOARD_BASIC_AUTH_USERNAME (see .env.example)}"
: "${HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH:?set HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH -- see \"how do I generate the password hash\"}"
: "${HERMES_DASHBOARD_BASIC_AUTH_SECRET:?set HERMES_DASHBOARD_BASIC_AUTH_SECRET (32+ random bytes; safe to generate locally, see .env.example)}"
# Exact shape confirmed from plugins/dashboard_auth/basic/__init__.py:
# `scrypt$n$r$p$<salt_b64>$<dk_b64>` -- anything else is a hash Hermes's own
# _verify_password will just reject at parse time, so catch it here instead.
if ! [[ "$HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH" =~ ^scrypt\$[0-9]+\$[0-9]+\$[0-9]+\$[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+$ ]]; then
  fail "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH doesn't match scrypt\$n\$r\$p\$salt\$hash -- see \"how do I generate the password hash\""
fi

# --- Tooling -----------------------------------------------------------------
command -v docker >/dev/null 2>&1 || fail "docker not found on PATH"

# --- Network -------------------------------------------------------------
# EVAL_SUITE_PLAN.md's non-negotiable rule: "Container network: the bridge
# only." Plain `docker run` below does NOT enforce that by itself -- it
# gives the container normal outbound access, restricted only by whatever
# the host's own network/firewall does (and, now, an inbound path for the
# dashboard port too). Tightening this (a dedicated no-internet Docker
# network plus an explicit route to host.docker.internal, or host firewall
# rules) is a follow-up, not solved here -- do not treat this script as
# satisfying that rule as-is.

docker build -f "$SCRIPT_DIR/Dockerfile.hermes" \
  --build-context hermes-src="$HERMES_SRC_DIR" \
  -t eval-harness/hermes:pinned \
  "$SCRIPT_DIR"

docker run -it --rm \
  --add-host=host.docker.internal:host-gateway \
  -e HERMES_DASHBOARD_PORT \
  -e HERMES_DASHBOARD_ARGS \
  -e HERMES_DASHBOARD_BASIC_AUTH_USERNAME \
  -e HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH \
  -e HERMES_DASHBOARD_BASIC_AUTH_SECRET \
  -p "${HERMES_DASHBOARD_PORT}:${HERMES_DASHBOARD_PORT}" \
  -v "$CASE_DIR:/case-src:ro" \
  -v "$HERMES_CONFIG_DIR:/hermes-config-src:ro" \
  -v "$SKILLS_DIR:/skills-src:ro" \
  -v "$RUN_DIR:/output" \
  eval-harness/hermes:pinned \
  hermes chat --yolo --toolsets terminal --oneshot \
    -q "Read AGENTS.md in your working directory."

echo "Run output: $RUN_DIR"
