#!/usr/bin/env bash
# Emergency stop for any running eval-harness Hermes container(s).
#
# Uses `docker kill` (immediate SIGKILL), not `docker stop` -- verified
# directly this costs nothing here, not chosen for speed alone: this
# container's PID 1 is a plain bash process (entrypoint.sh execs through
# entrypoint-agent.sh) with no SIGTERM trap installed, and PID 1 gets
# special kernel signal-disposition treatment -- SIGTERM's default action
# is ignored for PID 1 unless a handler is explicitly installed. Confirmed
# live: `docker stop -t 3` against an equivalent plain-bash-as-PID-1
# container burned the entire 3s grace period doing nothing, then fell
# back to SIGKILL anyway (exit 137). There is no gentler option actually
# available against this container's current process structure -- waiting
# for one that doesn't exist would only slow down the one script whose
# entire point is speed.
#
# A real, unavoidable consequence of that: whatever the agent hadn't
# already written to /output at the moment this runs is lost.
# entrypoint-agent.sh's QUESTION_ANSWERS.md/trace copy only runs on a
# NORMAL exit (hermes chat returning on its own) -- a kill skips it
# entirely, same as any SIGKILL would. This is a stop switch, not a
# save-and-stop switch.
#
# Targets every currently-running container built from the
# eval-harness/hermes:pinned image tag, not one specific container ID --
# run-case.sh doesn't name or label its containers, and this harness is
# meant to run one investigation at a time anyway. Deliberately doesn't
# read .env or anything else run-case.sh needs, so it still works even if
# something else about the setup is broken.
#
# Usage:
#   ./killswitch.sh          # kill every running eval-harness container
#   ./killswitch.sh --list   # show what's running; kill nothing

set -euo pipefail

command -v docker >/dev/null 2>&1 || { echo "killswitch: docker not found on PATH" >&2; exit 1; }

IMAGE="eval-harness/hermes:pinned"

containers=()
while IFS= read -r line; do
  [ -n "$line" ] && containers+=("$line")
done < <(docker ps --filter "ancestor=$IMAGE" --format '{{.ID}} {{.RunningFor}} {{.Status}}')

if [ "${#containers[@]}" -eq 0 ]; then
  echo "killswitch: no running containers from $IMAGE"
  exit 0
fi

echo "killswitch: found ${#containers[@]} running container(s) from $IMAGE:"
printf '  %s\n' "${containers[@]}"

if [ "${1:-}" = "--list" ] || [ "${1:-}" = "-l" ]; then
  echo "killswitch: --list given, not killing anything"
  exit 0
fi

ids=()
for line in "${containers[@]}"; do
  ids+=("${line%% *}")
done

docker kill "${ids[@]}"
echo "killswitch: killed ${#ids[@]} container(s)"
