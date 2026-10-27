# Coding standards — eval-harness

For humans and agents writing code here. Design decisions live in
`judge/DESIGN.md`; this file is only about how code is written.

## Language and dependencies

- Python 3.11+.
- Prefer building in-house over adding a dependency when the problem is
  simple. Any dependency that is added is pinned.

## Structure

- Use functions. Classes only to hold data, as frozen dataclasses
  (`@dataclass(frozen=True)`), so instances can't change after creation.
  Fields use `tuple`, not `list`: frozen is shallow.
- Program entry is a `main()` function, called under
  `if __name__ == "__main__":`.
- A function longer than 15 lines of code is broken down into smaller,
  publicly reusable functions.
- Every function has a docstring.
- Every function signature has type hints. No type checker is run.
- Every `.py` file starts with a `(C) %COMPANY%` header.
- Pure functions (input in, output out) unless an external data source is
  required. Side effects (files, network) stay in small boundary functions.
- PEP 8 naming: `snake_case` for functions and variables, `UPPER_CASE` for
  constants.

## File layout

Every `.py` file follows this order. Omit a section comment if the
section is empty.

```python
# (C) %COMPANY%
"""Module docstring."""

import ...

# CONSTS            (includes LOGGER = logging.getLogger(__name__))
# TYPES             (dataclasses and other user-defined types)
# PUBLIC FUNCTIONS
# PRIVATE FUNCTIONS (names start with _)
# INLINE RUN        (if __name__ == "__main__":)
```

## Imports

- Two groups, separated by a blank line: all `import x` statements first,
  then all `from x import y` statements.
- Alphabetical within each group.

## Constants and state

- No magic strings or numbers: every literal value is a named constant.
  Exception: logging message strings. Exit codes are constants too.
- No globals. Module level holds constants only.
- Constant collections use `tuple` or `frozenset`, never `list` or `dict`
  (those can be changed in place). Exception: the string table
  (`iso.STRINGS`) is a `dict`.
- User-facing text comes from the string table in `iso.py`, keyed by ISO
  639-1 code (`en`, `ja`). A message missing in one language falls back to
  English.

## External data

- All data from external sources (files, environment, model replies) is
  untrusted. Validate it before persisting it or acting on it.
- Open every file with `encoding="utf-8"`.

## Errors (Go convention)

- A function that can fail returns `T | Exception`; it doesn't raise.
- Validate inputs first and fail fast: return an `Exception` before doing
  any work.
- Check every returned error right after the call, error case first:
  `if isinstance(ret, Exception): return ret`. The happy path follows
  without an `else`. Never ignore an error: `pass` on one is a bug.
- Library calls that raise (files, environment, HTTP, parsing) are wrapped
  at the boundary: catch there, return the error.
- No nested `try`/`except`. Errors propagate up by return.
- The only broad `try` is in `main()`: it logs the error, then exits
  non-zero.
- **Exception: configuration.** `config.*` getters exit the program
  directly (log, then `sys.exit`) if a value is missing or invalid.
  Misconfiguration should die immediately. Note: `logging.fatal()` only
  logs; it does not exit.

## Configuration and secrets

- All configuration is twelve-factor: it comes from environment variables,
  loaded from `.env` (gitignored; `.env.example` committed).
- Config getters return the parsed primitive type (e.g.
  `get_model_temperature() -> float`) and enforce ranges.
- `JUDGE_HTTP_HEADERS` may hold credentials. Never log, print or write
  its values, not even redacted; header names are fine.
- The headers stay out of the configuration object. Only the provider
  adapter sends them.

## Logging

- Call `logging.basicConfig()` once, in `main()`.
- Modules use `logging.getLogger(__name__)`.
- Levels:
  - `debug()`: first line of every public function (Python has no
    `trace()`).
  - `info()`: key facts on the critical path (case by case).
  - `warning()` (not the deprecated `warn()`): something unusual, but
    execution continues.
  - `error()`: this function's flow is interrupted, i.e. it's returning an
    error.
  - `critical()`: the program is about to exit (`config._fatal`, `main()`).
- Log errors where they happen, even when they're propagated. Each
  message says what can't be done **at that level** ("cannot read input
  file X", "cannot get case file paths from Y"), so the log reads as a
  trail rather than repeats.
- Wrap and catch only code we don't own (standard library, third-party).
  Log caught exceptions with `exc_info=err` to keep the traceback.
- Never log file contents or untrusted text, only paths, sizes and hashes.

## Tests

- Unit tests use the standard library's `unittest`.
- Every parser, check and scoring function has tests.

## Division of labour

- The model makes the judgment (picks the band). Code does everything
  else: parsing, checks, arithmetic, reports.
