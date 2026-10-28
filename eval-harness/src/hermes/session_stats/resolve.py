# (C) %COMPANY%
"""Resolve exactly one session row from the given arguments, or the first error."""

import db
import inputs
import logging

# CONSTS
LOGGER = logging.getLogger(__name__)


# PUBLIC FUNCTIONS
def resolve_session(conn, args: inputs.Args) -> db.SessionRow | Exception:
    """Return the one session row matching args, or the first error.

    If args.session_id is given, looks it up directly and checks it falls
    inside [args.start_time, args.end_time] -- a session that exists but
    is outside the window is a different, distinctly reported error from
    one that doesn't exist at all. Otherwise searches the window and
    requires exactly one match: zero or more than one is an error, never
    a guess.
    """
    LOGGER.debug("resolve_session(%s)", args)
    if args.session_id is not None:
        return _resolve_by_id(conn, args)
    return _resolve_by_window(conn, args)


# PRIVATE FUNCTIONS
def _resolve_by_id(conn, args: inputs.Args) -> db.SessionRow | Exception:
    """Return the session named by args.session_id if it falls inside the
    window, or the first error.
    """
    row = db.query_session_by_id(conn, args.session_id)
    if isinstance(row, Exception):
        LOGGER.error("cannot resolve session %s", args.session_id)
        return row
    if row is None:
        LOGGER.error("session %s does not exist", args.session_id)
        return ValueError(f"no such session: {args.session_id}")
    if not _in_window(row, args):
        LOGGER.error("session %s is outside the given window", args.session_id)
        return ValueError(
            f"session {args.session_id} ({row.started_at}-{row.ended_at}) "
            f"is outside the window [{args.start_time}, {args.end_time}]"
        )
    return row


def _resolve_by_window(conn, args: inputs.Args) -> db.SessionRow | Exception:
    """Return the one session inside the window, or the first error."""
    rows = db.query_sessions_by_window(conn, args.start_time, args.end_time)
    if isinstance(rows, Exception):
        LOGGER.error("cannot resolve a session in window [%s, %s]", args.start_time, args.end_time)
        return rows
    if not rows:
        LOGGER.error("no session in window [%s, %s]", args.start_time, args.end_time)
        return ValueError(f"no session found in window [{args.start_time}, {args.end_time}]")
    if len(rows) > 1:
        ids = ", ".join(row.id for row in rows)
        LOGGER.error("%d sessions in window [%s, %s]: %s", len(rows), args.start_time, args.end_time, ids)
        return ValueError(f"{len(rows)} sessions in this window, specify --sessionid: {ids}")
    return rows[0]


def _in_window(row: db.SessionRow, args: inputs.Args) -> bool:
    """Return True if row's lifetime overlaps args's window at all. A
    still-running session (ended_at is None) is treated as open-ended, the
    same overlap rule db.query_sessions_by_window applies in SQL.
    """
    return row.started_at <= args.end_time and (row.ended_at is None or row.ended_at >= args.start_time)
