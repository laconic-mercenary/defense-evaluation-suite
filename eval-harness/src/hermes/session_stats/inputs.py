# (C) %COMPANY%
"""Program inputs: command-line arguments for session_stats."""

import argparse
import logging

from dataclasses import dataclass
from pathlib import Path

# CONSTS
LOGGER = logging.getLogger(__name__)
PROG_DESCRIPTION = "Read session telemetry (tokens, tool counts, timestamps, content) from a Hermes state.db."
ARG_DB_PATH = "db_path"
ARG_DB_PATH_HELP = "Path to Hermes's state.db"
ARG_SESSION_ID_FLAG = "--sessionid"
ARG_SESSION_ID = "session_id"
ARG_SESSION_ID_HELP = "Session ID to narrow the search to (optional; the time window is still required)"
ARG_START_TIME_FLAG = "--starttime"
ARG_START_TIME = "start_time"
ARG_START_TIME_HELP = "Start of the search window, as epoch seconds"
ARG_END_TIME_FLAG = "--endtime"
ARG_END_TIME = "end_time"
ARG_END_TIME_HELP = "End of the search window, as epoch seconds"


# TYPES
@dataclass(frozen=True)
class Args:
    """The program's command-line arguments, as given (not yet validated)."""

    db_path: str
    session_id: str | None
    start_time: float
    end_time: float


# PUBLIC FUNCTIONS
def parse_args(argv: list[str]) -> Args:
    """Parse argv (without the program name) into Args."""
    LOGGER.debug("parse_args(%s)", argv)
    namespace = _build_parser().parse_args(argv)
    return Args(
        db_path=getattr(namespace, ARG_DB_PATH),
        session_id=getattr(namespace, ARG_SESSION_ID),
        start_time=getattr(namespace, ARG_START_TIME),
        end_time=getattr(namespace, ARG_END_TIME),
    )


def validate_args(args: Args) -> Args | Exception:
    """Return args if db_path exists and start_time < end_time, or the first error."""
    LOGGER.debug("validate_args(%s)", args)
    problem = _args_problem(args)
    if problem is not None:
        LOGGER.error("cannot use these arguments: %s", problem)
        return ValueError(problem)
    return args


# PRIVATE FUNCTIONS
def _args_problem(args: Args) -> str | None:
    """Return why args is invalid, or None if it is valid."""
    db_file = Path(args.db_path)
    if not db_file.exists():
        return f"no such file: {args.db_path}"
    if not db_file.is_file():
        return f"not a regular file: {args.db_path}"
    if args.start_time >= args.end_time:
        return f"start_time ({args.start_time}) must be before end_time ({args.end_time})"
    return None


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser."""
    parser = argparse.ArgumentParser(description=PROG_DESCRIPTION)
    parser.add_argument(ARG_DB_PATH, help=ARG_DB_PATH_HELP)
    parser.add_argument(ARG_SESSION_ID_FLAG, dest=ARG_SESSION_ID, default=None, help=ARG_SESSION_ID_HELP)
    parser.add_argument(ARG_START_TIME_FLAG, dest=ARG_START_TIME, type=float, required=True, help=ARG_START_TIME_HELP)
    parser.add_argument(ARG_END_TIME_FLAG, dest=ARG_END_TIME, type=float, required=True, help=ARG_END_TIME_HELP)
    return parser
