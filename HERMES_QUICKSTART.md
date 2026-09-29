# Hermes Eval Harness — Quickstart

Get a single forensic case running against Hermes/Qwen in Docker. For the
full design/reasoning, read the comments in `eval-harness/docker/*.sh` —
this doc is deliberately just the steps.

## Prerequisites

- **Docker** (Desktop or Engine), running.
- **Python 3**, installed on your host — needed once, to generate the
  dashboard's password hash (see the Setup section below).

## Assumptions

This harness doesn't vendor or build anything from these — you point it at
directories you've already prepared:

1. **A local `NousResearch/hermes-agent` clone**, checked out to whatever
   commit you want to build. Nothing else required of it.
2. **A Hermes profile directory already configured to talk to your model
   endpoint** — run `hermes setup` / `hermes model` yourself (from inside
   the clone above) pointing at Modal (dev) or your on-prem endpoint
   (prod). This harness never runs that setup for you and never modifies
   the directory you point it at.
3. **(Optional) A directory of Hermes-format skill folders** (each a
   `<name>/SKILL.md`) to give the agent during investigations — e.g.
   hand-picked from [`mukul975/anthropic-cybersecurity-skills`](https://github.com/mukul975/anthropic-cybersecurity-skills)
   (an independent community project, not Anthropic-affiliated despite the
   name). Skip this and Hermes just runs with whatever's in its own
   profile.

## Setup

```bash
cd eval-harness/docker
cp .env.example .env
```

Edit `.env`:

| Variable | What it is |
|---|---|
| `HERMES_SRC_DIR` | Path to your hermes-agent clone (assumption 1) |
| `HERMES_CONFIG_DIR` | Path to your configured Hermes profile (assumption 2) |
| `SKILLS_DIR` | Path to a directory of skill folders (assumption 3) |
| `PROXY_ALLOWED_HOST` | Your model endpoint's **hostname only** (no `https://`, no path) — the container can reach nowhere else once running |
| `HERMES_DASHBOARD_PORT` | Defaults to `9119` |
| `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` | Dashboard login username |
| `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH` | See below |
| `HERMES_DASHBOARD_BASIC_AUTH_SECRET` | See below |

For a quick first run, these two are fine to paste in as-is:

```bash
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH='scrypt$16384$8$1$jgUNjsEnB0Hld+ddt/CtZw==$OFp1f0fUS0WeIAXlWCMS0FDOckuEUVq2uHd7qLJJ40w='
HERMES_DASHBOARD_BASIC_AUTH_SECRET=eac4f91078c33b0bc1eacfc981d14e65d8dbb9610f61bdcd4bba57ef4bdc2997
```

That hash is for the password `changeme`. **These are quickstart values,
not something to leave in place** — the dashboard's port is published to
your host, so anyone who can reach it knows this doc and can look up that
password too. Generate your own before anything beyond a local first run,
from inside `HERMES_SRC_DIR` (the hash import only resolves inside that
project's own environment, hence `uv run`):

```bash
# Password hash
uv run python -c "from plugins.dashboard_auth.basic import hash_password; print(hash_password('your-own-password'))"

# Secret (just random bytes, no format to match — plain Python is fine)
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Run a case

```bash
./run-case.sh rdp-remote-file-write
```

Builds the image (first run only takes a while), runs the case, and prints
where the output landed:

```
eval-harness/runs/<case-slug>/testrun_<agent-id>_<case-slug>_<timestamp>/
  QUESTION_ANSWERS.md
  trace.jsonl
```

The dashboard is reachable at `http://localhost:<HERMES_DASHBOARD_PORT>`
for the duration of the run.

## Something wrong? Stop it now

```bash
./killswitch.sh          # kill any running eval-harness container
./killswitch.sh --list   # see what's running first, without killing it
```

## What's already locked down, briefly

The container can only reach `PROXY_ALLOWED_HOST` — nothing else, enforced
by an in-container firewall the agent itself can never touch. Full
mechanism is documented in `eval-harness/docker/entrypoint.sh`.
