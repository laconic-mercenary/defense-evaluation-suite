# (C) %COMPANY%
"""The session_stats report: a session summary plus one row per message."""

import db
import json
import logging

from dataclasses import asdict, dataclass

# CONSTS
LOGGER = logging.getLogger(__name__)
TOOL_ROLE = "tool"
FIRST_MESSAGE_INDEX = 0


# TYPES
@dataclass(frozen=True)
class SessionSummary:
    """The session-level totals -- the only granularity tokens and cost
    actually exist at (Hermes keeps no per-message ledger; confirmed
    against its own write path, not assumed).
    """

    session_id: str
    started_at: float
    ended_at: float | None
    duration_seconds: float | None
    model: str | None
    message_count: int
    tool_call_count: int
    api_call_count: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    reasoning_tokens: int
    estimated_cost_usd: float | None
    actual_cost_usd: float | None


@dataclass(frozen=True)
class MessageReportRow:
    """One reported message: identity, type, timing and content -- never
    tokens, which don't exist at this granularity.
    """

    message_id: int
    type: str
    is_tool_call: bool
    time_elapsed_seconds: float
    content: str


@dataclass(frozen=True)
class Report:
    """One session_stats run's full output."""

    summary: SessionSummary
    messages: tuple[MessageReportRow, ...]


# PUBLIC FUNCTIONS
def build_summary(session: db.SessionRow) -> SessionSummary:
    """Return session's session-level totals as a SessionSummary."""
    LOGGER.debug("build_summary(%s)", session.id)
    duration = session.ended_at - session.started_at if session.ended_at is not None else None
    return SessionSummary(
        session_id=session.id, started_at=session.started_at, ended_at=session.ended_at,
        duration_seconds=duration, model=session.model, message_count=session.message_count,
        tool_call_count=session.tool_call_count, api_call_count=session.api_call_count,
        input_tokens=session.input_tokens, output_tokens=session.output_tokens,
        cache_read_tokens=session.cache_read_tokens, cache_write_tokens=session.cache_write_tokens,
        reasoning_tokens=session.reasoning_tokens, estimated_cost_usd=session.estimated_cost_usd,
        actual_cost_usd=session.actual_cost_usd,
    )


def build_message_rows(messages: tuple[db.MessageRow, ...]) -> tuple[MessageReportRow, ...]:
    """Return messages as MessageReportRow, in order. time_elapsed_seconds is
    the gap since the previous message, or 0.0 for the first.
    """
    LOGGER.debug("build_message_rows(%d messages)", len(messages))
    return tuple(_message_row(messages, index) for index in range(len(messages)))


def build_report(session: db.SessionRow, messages: tuple[db.MessageRow, ...]) -> Report:
    """Return the full report for session and its messages."""
    LOGGER.debug("build_report(%s)", session.id)
    return Report(summary=build_summary(session), messages=build_message_rows(messages))


def emit(report: Report) -> None:
    """Print report to stdout as one JSON object."""
    LOGGER.debug("emit(%s)", report.summary.session_id)
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))


# PRIVATE FUNCTIONS
def _message_row(messages: tuple[db.MessageRow, ...], index: int) -> MessageReportRow:
    """Return messages[index] as a MessageReportRow."""
    message = messages[index]
    previous_timestamp = messages[index - 1].timestamp if index > FIRST_MESSAGE_INDEX else message.timestamp
    return MessageReportRow(
        message_id=message.id, type=message.role, is_tool_call=_is_tool_call(message),
        time_elapsed_seconds=message.timestamp - previous_timestamp, content=message.content,
    )


def _is_tool_call(message: db.MessageRow) -> bool:
    """Return True if message is a tool invocation or a tool's result."""
    return bool(message.tool_calls) or message.role == TOOL_ROLE
