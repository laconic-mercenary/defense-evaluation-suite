#!/usr/bin/env bash
# Phase 1 (root) of this container's startup. Copies three read-only mounts
# (bound `:ro` at `docker run` time) into plain writable, container-local
# directories, stands up an egress-lockdown proxy and firewall, then drops
# root and hands off to entrypoint-agent.sh (phase 2, unprivileged) to
# actually run the agent. See entrypoint-agent.sh for why the handoff is a
# separate file rather than a spot partway through this one.
#
#   /case-src           -> /case                case evidence (see run-case.sh)
#   /hermes-config-src   -> $HERMES_HOME          your own pre-configured ~/.hermes
#   /skills-src          -> $HERMES_HOME/skills   whatever skills you want indexed
# Same reason for all three: the case files tell the agent to write
# QUESTION_ANSWERS.md "in this directory," and Hermes needs to write its
# own session/runtime state (including installing/indexing skills) --
# neither works against a `:ro` mount. Neither host original is ever
# touched; this container is discarded after one run, so nothing written
# during it persists back.
#
# A fourth mount, /output, goes the other way -- read-write, so this run's
# QUESTION_ANSWERS.md and trace actually escape the container instead of
# being deleted with it (`docker run --rm`). See entrypoint-agent.sh.
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

# Every `cp -a` below is followed by an explicit `chown -R hermes:hermes` on
# its destination -- not belt-and-suspenders, a real fix for a real bug hit
# while building this. `cp -a src/. dest/` replicates SOURCE ownership/mode
# onto whatever it creates, not just the bytes -- confirmed directly (a
# 700 source directory copied over an existing 777 destination left the
# destination at 700 too). This script now runs this copy as root (needed
# below for the iptables setup), and these three sources are `:ro` bind
# mounts of host paths that show up owned by root inside this container
# (a Docker Desktop bind-mount artifact) -- so root copying them faithfully
# replicates that root ownership onto $HERMES_HOME and /case, locking the
# hermes user out of its own runtime state entirely. This was silently
# harmless before: when this script ran AS hermes (pre-egress-lockdown),
# a non-root `cp -a` can't actually chown to a different owner, so it
# quietly kept the copies hermes-owned by fallback, not by a decision made
# anywhere. Root can, so now it must be corrected explicitly.
if [ ! -d /case-src ]; then
  echo "entrypoint: /case-src not mounted -- run-case.sh should have passed -v <case dir>:/case-src:ro" >&2
  exit 1
fi
cp -a /case-src/. /case/
chown -R hermes:hermes /case

if [ ! -d /hermes-config-src ]; then
  echo "entrypoint: /hermes-config-src not mounted -- set HERMES_CONFIG_DIR (see .env.example)" >&2
  exit 1
fi
cp -a /hermes-config-src/. "${HERMES_HOME}/"
chown -R hermes:hermes "${HERMES_HOME}"
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
#
# The egress lockdown below (proxy + firewall) is a real, separate
# mitigation for the worst-case consequence of that same gap: even if a
# credential does leak into the model's context (e.g. a compromised
# skill's symlink trick defeating redaction by basename -- found and
# verified this session, not hypothetical), there is nowhere for it to be
# exfiltrated TO except the one allowed destination.

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
chown -R hermes:hermes "${HERMES_HOME}/skills"

# --- Egress lockdown ----------------------------------------------------------
# Everything below runs as root (this container no longer sets USER in the
# Dockerfile for exactly this reason) and is gone -- capability and all --
# before the --yolo agent's own code starts running. The design, verified
# live before being written here (not assumed):
#
#   1. Squid (bound to 127.0.0.1:3128 only) is started as root, and
#      immediately self-drops to the `proxy` user per squid.conf's
#      `cache_effective_user` -- squid's own standard behavior, not
#      something this script orchestrates.
#   2. iptables OUTPUT policy is set to DROP by default, with explicit
#      ACCEPT rules for: loopback, established/related connections, and
#      any outbound packet owned by the `proxy` UID (squid's own traffic,
#      via the `owner` match module) -- so squid itself can still reach
#      its one allowed destination, but nothing else on this container can
#      reach anywhere at all except through it.
#   3. `capsh --drop=cap_net_admin` removes NET_ADMIN from this process's
#      capability BOUNDING set -- not just the effective/permitted sets a
#      plain UID switch would drop, but the set that would otherwise let a
#      descendant process regain it by any means. Confirmed directly: a
#      capsh-dropped process attempting `iptables -F` while still
#      uid=0(root) fails with a kernel-level "Permission denied," not a
#      convention that trusts the agent to behave.
#   4. gosu switches to the unprivileged `hermes` user in the same step,
#      then execs entrypoint-agent.sh, which is what actually runs the
#      agent's commands from here on.
#
# PROXY_ALLOWED_HOST is the one destination this whole container can ever
# reach -- your model endpoint's hostname (Modal in dev, on-prem in prod;
# see run-case.sh). Hostname-based (Squid's dstdomain), not IP-based: the
# IP behind that hostname can rotate, the hostname is the actual contract.
: "${PROXY_ALLOWED_HOST:?set PROXY_ALLOWED_HOST -- see run-case.sh / .env.example}"
envsubst '${PROXY_ALLOWED_HOST}' < /etc/squid/squid.conf.template > /etc/squid/squid.conf
mkdir -p /var/log/squid
squid -f /etc/squid/squid.conf

# Squid forks and returns almost immediately, but "listening" and "returned"
# aren't the same moment -- poll instead of a fixed sleep, since how long
# that gap actually is isn't something to guess at and hard-code.
for _ in $(seq 1 50); do
  if (exec 3<>/dev/tcp/127.0.0.1/3128) 2>/dev/null; then
    exec 3>&-
    break
  fi
  sleep 0.1
done

iptables -P OUTPUT DROP
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
# Keyed off the same `proxy` UID squid.conf.template's cache_effective_user
# sets -- the two have to stay in sync if either ever changes.
iptables -A OUTPUT -m owner --uid-owner proxy -j ACCEPT

export HTTPS_PROXY="http://127.0.0.1:3128"
export HTTP_PROXY="http://127.0.0.1:3128"
export NO_PROXY="localhost,127.0.0.1"

# The quoting here is deliberate and tested, not incidental: `"$@"` inside
# the single-quoted -c string is passed through LITERALLY (capsh's shell
# resolves it against ITS OWN positional params, populated from whatever
# follows `-c '...' --`), so the original hermes-chat arguments survive
# capsh -> gosu -> entrypoint-agent.sh byte-for-byte, spaces and embedded
# quotes included -- verified directly with an adversarial test argument
# before this was written, not assumed safe.
exec capsh --drop=cap_net_admin -- -c "exec gosu hermes /usr/local/bin/entrypoint-agent.sh \"\$@\"" -- "$@"
