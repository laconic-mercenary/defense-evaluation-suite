#!/usr/bin/env bash
# Phase 2 of the container's startup -- see entrypoint.sh for phase 1.
#
# entrypoint.sh (root) copies in evidence/config/skills, stands up the
# egress-lockdown proxy and its iptables rules, then irreversibly drops
# cap_net_admin from the process's capability bounding set and hands off
# here via `capsh --drop=... -- -c 'exec gosu hermes entrypoint-agent.sh
# "$@"'`. By the time this script's first line runs, the process is
# already the unprivileged `hermes` user with no path back to touching
# those rules -- verified directly (capsh-dropped root attempting
# `iptables -F` fails with a kernel-level permission error, not just a
# convention). This is deliberately the phase that runs the actual --yolo
# agent, so it must never be the phase capable of undoing the lockdown.
set -euo pipefail

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
    echo "entrypoint-agent: /case/QUESTION_ANSWERS.md missing at exit (exit code $HERMES_EXIT_CODE) -- nothing to copy out" >&2
  fi
  # --format trace (a "Claude Code JSONL trace export," confirmed in
  # hermes_cli/sessions_cmd.py) with no --session-id resolves to "the last
  # thing I did" -- the most recently active session -- which in this
  # single-use, single-session container is always the run above. Failure
  # here shouldn't mask a real hermes chat failure, so it's logged, not
  # fatal.
  if ! hermes sessions export --format trace /output/trace.jsonl; then
    echo "entrypoint-agent: hermes sessions export failed -- no trace captured for this run" >&2
  fi
else
  echo "entrypoint-agent: /output not mounted -- QUESTION_ANSWERS.md and the trace stay trapped in this container. Set up RUN_DIR in run-case.sh." >&2
fi

exit "$HERMES_EXIT_CODE"
