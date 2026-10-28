# (C) %COMPANY%
"""All SQLite access for session_stats: the only file that imports sqlite3."""

import json
import logging
import sqlite3

from dataclasses import dataclass

# CONSTS
LOGGER = logging.getLogger(__name__)
CONTENT_JSON_PREFIX = "\x00json:"  # Hermes's own sentinel (hermes_state.py); a null byte, not a bare string
READ_ONLY_URI_FORMAT = "file:{path}?mode=ro"
SESSION_COLUMNS = (
    "id", "started_at", "ended_at", "message_count", "tool_call_count",
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "reasoning_tokens",
    "api_call_count", "estimated_cost_usd", "actual_cost_usd", "model", "cwd",
)
MESSAGE_COLUMNS = ("id", "role", "content", "tool_calls", "tool_name", "tool_call_id", "timestamp", "finish_reason")
SELECT_SESSION_BY_ID_SQL = f"SELECT {', '.join(SESSION_COLUMNS)} FROM sessions WHERE id = ?"
# Overlap, not containment: `started_at <= end_time AND ended_at >= start_time`, with a NULL
# ended_at (session still running, or ended without a clean finalize) treated as open-ended
# rather than excluded -- plain "ended_at <= ?" would silently drop exactly those rows, since
# SQL's `NULL <= x` is NULL, not true.
SELECT_SESSIONS_BY_WINDOW_SQL = (
    f"SELECT {', '.join(SESSION_COLUMNS)} FROM sessions WHERE started_at <= ? AND (ended_at IS NULL OR ended_at >= ?)"
)
SELECT_MESSAGES_SQL = f"SELECT {', '.join(MESSAGE_COLUMNS)} FROM messages WHERE session_id = ? ORDER BY id"


# TYPES
@dataclass(frozen=True)
class SessionRow:
    """One row of the sessions table, the fields session_stats reports."""

    id: str
    started_at: float
    ended_at: float | None
    message_count: int
    tool_call_count: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    reasoning_tokens: int
    api_call_count: int
    estimated_cost_usd: float | None
    actual_cost_usd: float | None
    model: str | None
    cwd: str | None


@dataclass(frozen=True)
class MessageRow:
    """One row of the messages table, content decoded."""

    id: int
    role: str
    content: str
    tool_calls: str | None
    tool_name: str | None
    tool_call_id: str | None
    timestamp: float
    finish_reason: str | None


# PUBLIC FUNCTIONS
def open_db(path: str) -> sqlite3.Connection | Exception:
    """Return a read-only connection to the state.db at path, or the error.

    Read-only on purpose: this tool only ever reads telemetry after the
    fact and must never write to a database a live Hermes process might
    still hold open.
    """
    LOGGER.debug("open_db(%s)", path)
    try:
        return sqlite3.connect(READ_ONLY_URI_FORMAT.format(path=path), uri=True)
    except sqlite3.Error as e:
        LOGGER.error("cannot open database %s", path, exc_info=e)
        return e


def close_db(conn: sqlite3.Connection) -> None:
    """Close conn."""
    LOGGER.debug("close_db()")
    conn.close()


def query_session_by_id(conn: sqlite3.Connection, session_id: str) -> SessionRow | None | Exception:
    """Return the session row with id session_id, or None if it doesn't
    exist, or the error. Does not filter by time window -- see resolve.py.
    """
    LOGGER.debug("query_session_by_id(%s)", session_id)
    rows = _run_query(conn, SELECT_SESSION_BY_ID_SQL, (session_id,))
    if isinstance(rows, Exception):
        LOGGER.error("cannot query session %s", session_id)
        return rows
    return _row_to_session(rows[0]) if rows else None


def query_sessions_by_window(
    conn: sqlite3.Connection, start_time: float, end_time: float
) -> tuple[SessionRow, ...] | Exception:
    """Return every session row whose lifetime overlaps [start_time, end_time]
    at all, or the error. A session with no ended_at yet (still running, or
    ended without a clean finalize) counts as open-ended, not excluded.
    """
    LOGGER.debug("query_sessions_by_window(%s, %s)", start_time, end_time)
    rows = _run_query(conn, SELECT_SESSIONS_BY_WINDOW_SQL, (end_time, start_time))
    if isinstance(rows, Exception):
        LOGGER.error("cannot query sessions in window [%s, %s]", start_time, end_time)
        return rows
    return tuple(_row_to_session(row) for row in rows)


def query_messages(conn: sqlite3.Connection, session_id: str) -> tuple[MessageRow, ...] | Exception:
    """Return every message row for session_id, in order, or the error."""
    LOGGER.debug("query_messages(%s)", session_id)
    rows = _run_query(conn, SELECT_MESSAGES_SQL, (session_id,))
    if isinstance(rows, Exception):
        LOGGER.error("cannot query messages for session %s", session_id)
        return rows
    return tuple(_row_to_message(row) for row in rows)


def decode_content(raw: str | None) -> str:
    """Return raw with Hermes's JSON-content sentinel decoded, or "" for None.

    Plain text was stored as-is; multimodal content was stored JSON-encoded
    behind CONTENT_JSON_PREFIX. Falls back to the raw string if the JSON is
    malformed, matching Hermes's own decode behavior.
    """
    if raw is None:
        return ""
    if not raw.startswith(CONTENT_JSON_PREFIX):
        return raw
    try:
        return json.dumps(json.loads(raw[len(CONTENT_JSON_PREFIX):]), ensure_ascii=False)
    except (ValueError, TypeError) as e:
        LOGGER.warning("cannot decode JSON content, returning raw string", exc_info=e)
        return raw


# PRIVATE FUNCTIONS
def _run_query(conn: sqlite3.Connection, sql: str, params: tuple) -> list[tuple] | Exception:
    """Return every row from sql, or the error."""
    try:
        return conn.execute(sql, params).fetchall()
    except sqlite3.Error as e:
        LOGGER.error("query failed", exc_info=e)
        return e


def _row_to_session(row: tuple) -> SessionRow:
    """Return row (in SESSION_COLUMNS order) as a SessionRow."""
    return SessionRow(**dict(zip(SESSION_COLUMNS, row)))


def _row_to_message(row: tuple) -> MessageRow:
    """Return row (in MESSAGE_COLUMNS order) as a MessageRow, content decoded."""
    fields = dict(zip(MESSAGE_COLUMNS, row))
    fields["content"] = decode_content(fields["content"])
    return MessageRow(**fields)
