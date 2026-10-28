# (C) %COMPANY%
"""Tests for report.py."""

import db
import report
import unittest

# CONSTS
SESSION_ID = "session-1"


# PRIVATE FUNCTIONS
def _session_row(ended_at: float | None) -> db.SessionRow:
    """Return a SessionRow with every count set to a distinct, checkable value."""
    return db.SessionRow(
        id=SESSION_ID, started_at=100.0, ended_at=ended_at, message_count=3, tool_call_count=1,
        input_tokens=10, output_tokens=20, cache_read_tokens=1, cache_write_tokens=2, reasoning_tokens=3,
        api_call_count=2, estimated_cost_usd=0.01, actual_cost_usd=0.02, model="test-model", cwd="/case",
    )


def _message_row(
    message_id: int, role: str, timestamp: float, content: str = "", tool_calls: str | None = None
) -> db.MessageRow:
    """Return a MessageRow with only the fields a given test cares about set."""
    return db.MessageRow(
        id=message_id, role=role, content=content, tool_calls=tool_calls, tool_name=None,
        tool_call_id=None, timestamp=timestamp, finish_reason=None,
    )


# TYPES
class BuildSummaryTest(unittest.TestCase):
    """Tests for build_summary."""

    def test_fields_carry_through(self) -> None:
        """Every session-level field maps straight into the summary."""
        summary = report.build_summary(_session_row(ended_at=200.0))
        self.assertEqual(summary.session_id, SESSION_ID)
        self.assertEqual(summary.input_tokens, 10)
        self.assertEqual(summary.output_tokens, 20)
        self.assertEqual(summary.tool_call_count, 1)
        self.assertEqual(summary.message_count, 3)
        self.assertEqual(summary.duration_seconds, 100.0)

    def test_duration_none_when_not_ended(self) -> None:
        """A session with no ended_at reports no duration, not a wrong number."""
        summary = report.build_summary(_session_row(ended_at=None))
        self.assertIsNone(summary.duration_seconds)


class IsToolCallTest(unittest.TestCase):
    """Tests for _is_tool_call."""

    def test_user_message_is_not_a_tool_call(self) -> None:
        """A plain user message is not a tool call."""
        self.assertFalse(report._is_tool_call(_message_row(1, "user", 100.0)))

    def test_assistant_text_is_not_a_tool_call(self) -> None:
        """An assistant text reply with no tool_calls is not a tool call."""
        self.assertFalse(report._is_tool_call(_message_row(1, "assistant", 100.0)))

    def test_assistant_with_tool_calls_is_a_tool_call(self) -> None:
        """An assistant message carrying tool_calls is a tool call."""
        self.assertTrue(report._is_tool_call(_message_row(1, "assistant", 100.0, tool_calls="[...]")))

    def test_tool_role_is_a_tool_call(self) -> None:
        """A tool-result message is a tool call, even with no tool_calls column."""
        self.assertTrue(report._is_tool_call(_message_row(1, "tool", 100.0)))


class BuildMessageRowsTest(unittest.TestCase):
    """Tests for build_message_rows."""

    def test_first_message_has_zero_elapsed(self) -> None:
        """The first message's elapsed time is 0.0, not measured against nothing."""
        rows = report.build_message_rows((_message_row(1, "user", 100.0),))
        self.assertEqual(rows[0].time_elapsed_seconds, 0.0)

    def test_elapsed_is_gap_since_previous(self) -> None:
        """Each later row's elapsed time is the gap since the row before it."""
        messages = (_message_row(1, "user", 100.0), _message_row(2, "assistant", 107.5))
        rows = report.build_message_rows(messages)
        self.assertEqual(rows[1].time_elapsed_seconds, 7.5)

    def test_content_and_identity_carry_through(self) -> None:
        """message_id, type and content map straight from the source row."""
        rows = report.build_message_rows((_message_row(42, "user", 100.0, content="hello"),))
        self.assertEqual(rows[0].message_id, 42)
        self.assertEqual(rows[0].type, "user")
        self.assertEqual(rows[0].content, "hello")


class BuildReportTest(unittest.TestCase):
    """Tests for build_report."""

    def test_combines_summary_and_messages(self) -> None:
        """The report carries both the session summary and every message row."""
        messages = (_message_row(1, "user", 100.0), _message_row(2, "assistant", 105.0))
        built = report.build_report(_session_row(ended_at=200.0), messages)
        self.assertEqual(built.summary.session_id, SESSION_ID)
        self.assertEqual(len(built.messages), 2)


# INLINE RUN
if __name__ == "__main__":
    unittest.main()
