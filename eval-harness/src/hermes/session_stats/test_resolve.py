# (C) %COMPANY%
"""Tests for resolve.py."""

import db
import inputs
import resolve
import unittest

from unittest.mock import patch

# CONSTS
SESSION_ID = "session-1"
OTHER_SESSION_ID = "session-2"


# PRIVATE FUNCTIONS
def _session_row(session_id: str, started_at: float, ended_at: float | None) -> db.SessionRow:
    """Return a minimal, otherwise-zeroed SessionRow for test fixtures."""
    return db.SessionRow(
        id=session_id, started_at=started_at, ended_at=ended_at, message_count=0, tool_call_count=0,
        input_tokens=0, output_tokens=0, cache_read_tokens=0, cache_write_tokens=0, reasoning_tokens=0,
        api_call_count=0, estimated_cost_usd=None, actual_cost_usd=None, model=None, cwd=None,
    )


# TYPES
class ResolveByIdTest(unittest.TestCase):
    """Tests for resolve_session when args.session_id is given."""

    def test_found_in_window(self) -> None:
        """A session that exists and falls inside the window is returned."""
        args = inputs.Args(db_path="x", session_id=SESSION_ID, start_time=50.0, end_time=250.0)
        row = _session_row(SESSION_ID, 100.0, 200.0)
        with patch.object(db, "query_session_by_id", return_value=row):
            result = resolve.resolve_session(None, args)
        self.assertEqual(result, row)

    def test_not_found(self) -> None:
        """A session id that doesn't exist is an error, not None passed through."""
        args = inputs.Args(db_path="x", session_id=SESSION_ID, start_time=50.0, end_time=250.0)
        with patch.object(db, "query_session_by_id", return_value=None):
            result = resolve.resolve_session(None, args)
        self.assertIsInstance(result, Exception)

    def test_still_running_session_matches(self) -> None:
        """A session with no ended_at yet is treated as open-ended, not
        excluded -- the NULL-ended_at bug this fix addresses.
        """
        args = inputs.Args(db_path="x", session_id=SESSION_ID, start_time=50.0, end_time=250.0)
        row = _session_row(SESSION_ID, 100.0, None)
        with patch.object(db, "query_session_by_id", return_value=row):
            result = resolve.resolve_session(None, args)
        self.assertEqual(result, row)

    def test_still_running_session_started_after_window_is_outside(self) -> None:
        """Open-ended still means bounded by started_at, not 'matches anything'."""
        args = inputs.Args(db_path="x", session_id=SESSION_ID, start_time=50.0, end_time=90.0)
        row = _session_row(SESSION_ID, 100.0, None)
        with patch.object(db, "query_session_by_id", return_value=row):
            result = resolve.resolve_session(None, args)
        self.assertIsInstance(result, Exception)

    def test_outside_window(self) -> None:
        """A session that exists but falls outside the window is a distinct error."""
        args = inputs.Args(db_path="x", session_id=SESSION_ID, start_time=1000.0, end_time=2000.0)
        row = _session_row(SESSION_ID, 100.0, 200.0)
        with patch.object(db, "query_session_by_id", return_value=row):
            result = resolve.resolve_session(None, args)
        self.assertIsInstance(result, Exception)

    def test_query_error_propagates(self) -> None:
        """A db error is returned as-is, not swallowed."""
        args = inputs.Args(db_path="x", session_id=SESSION_ID, start_time=50.0, end_time=250.0)
        error = RuntimeError("boom")
        with patch.object(db, "query_session_by_id", return_value=error):
            result = resolve.resolve_session(None, args)
        self.assertIs(result, error)


class ResolveByWindowTest(unittest.TestCase):
    """Tests for resolve_session when args.session_id is None."""

    def test_exactly_one_match(self) -> None:
        """Exactly one session in the window is returned."""
        args = inputs.Args(db_path="x", session_id=None, start_time=50.0, end_time=250.0)
        row = _session_row(SESSION_ID, 100.0, 200.0)
        with patch.object(db, "query_sessions_by_window", return_value=(row,)):
            result = resolve.resolve_session(None, args)
        self.assertEqual(result, row)

    def test_no_match(self) -> None:
        """Zero sessions in the window is an error, not a crash."""
        args = inputs.Args(db_path="x", session_id=None, start_time=50.0, end_time=250.0)
        with patch.object(db, "query_sessions_by_window", return_value=()):
            result = resolve.resolve_session(None, args)
        self.assertIsInstance(result, Exception)

    def test_ambiguous_match(self) -> None:
        """More than one session in the window is an error -- never a guess."""
        args = inputs.Args(db_path="x", session_id=None, start_time=50.0, end_time=250.0)
        rows = (_session_row(SESSION_ID, 100.0, 150.0), _session_row(OTHER_SESSION_ID, 160.0, 200.0))
        with patch.object(db, "query_sessions_by_window", return_value=rows):
            result = resolve.resolve_session(None, args)
        self.assertIsInstance(result, Exception)
        self.assertIn(SESSION_ID, str(result))
        self.assertIn(OTHER_SESSION_ID, str(result))


# INLINE RUN
if __name__ == "__main__":
    unittest.main()
