# (C) %COMPANY%
"""Tests for db.py."""

import db
import json
import os
import sqlite3
import tempfile
import unittest

# CONSTS
CREATE_SESSIONS_SQL = """CREATE TABLE sessions (
    id TEXT PRIMARY KEY, started_at REAL NOT NULL, ended_at REAL, message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0, input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0, cache_write_tokens INTEGER DEFAULT 0, reasoning_tokens INTEGER DEFAULT 0,
    api_call_count INTEGER DEFAULT 0, estimated_cost_usd REAL, actual_cost_usd REAL, model TEXT, cwd TEXT
)"""
CREATE_MESSAGES_SQL = """CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT,
    tool_calls TEXT, tool_name TEXT, tool_call_id TEXT, timestamp REAL NOT NULL, finish_reason TEXT
)"""
INSERT_SESSION_SQL = """INSERT INTO sessions (
    id, started_at, ended_at, message_count, tool_call_count, input_tokens, output_tokens,
    cache_read_tokens, cache_write_tokens, reasoning_tokens, api_call_count, estimated_cost_usd,
    actual_cost_usd, model, cwd
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
INSERT_MESSAGE_SQL = """INSERT INTO messages (
    session_id, role, content, tool_calls, tool_name, tool_call_id, timestamp, finish_reason
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
SESSION_ID = "session-1"
OTHER_SESSION_ID = "session-2"


# TYPES
class DbTestCase(unittest.TestCase):
    """Base class: builds a real, on-disk SQLite fixture with the real schema."""

    def setUp(self) -> None:
        """Create a temp db file with sessions/messages tables and one session."""
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        setup_conn = sqlite3.connect(self.path)
        setup_conn.execute(CREATE_SESSIONS_SQL)
        setup_conn.execute(CREATE_MESSAGES_SQL)
        setup_conn.execute(
            INSERT_SESSION_SQL,
            (SESSION_ID, 100.0, 200.0, 2, 1, 10, 20, 0, 0, 0, 2, 0.01, None, "test-model", "/case"),
        )
        setup_conn.commit()
        setup_conn.close()

    def tearDown(self) -> None:
        """Remove the temp db file."""
        os.unlink(self.path)


class OpenDbTest(DbTestCase):
    """Tests for open_db / close_db."""

    def test_open_existing_file(self) -> None:
        """A real file opens successfully, read-only."""
        conn = db.open_db(self.path)
        self.assertNotIsInstance(conn, Exception)
        db.close_db(conn)

    def test_open_missing_file(self) -> None:
        """mode=ro on a nonexistent file is an error, not a silently-created one."""
        result = db.open_db("/no/such/directory/missing.db")
        self.assertIsInstance(result, Exception)


class QuerySessionByIdTest(DbTestCase):
    """Tests for query_session_by_id."""

    def test_found(self) -> None:
        """An existing session id returns its row, unfiltered by time."""
        conn = db.open_db(self.path)
        row = db.query_session_by_id(conn, SESSION_ID)
        db.close_db(conn)
        self.assertEqual(row.id, SESSION_ID)
        self.assertEqual(row.input_tokens, 10)
        self.assertEqual(row.model, "test-model")

    def test_not_found(self) -> None:
        """An unknown session id returns None, not an error."""
        conn = db.open_db(self.path)
        row = db.query_session_by_id(conn, "no-such-session")
        db.close_db(conn)
        self.assertIsNone(row)


class QuerySessionsByWindowTest(DbTestCase):
    """Tests for query_sessions_by_window."""

    def test_one_match(self) -> None:
        """A window covering the fixture session returns exactly it."""
        conn = db.open_db(self.path)
        rows = db.query_sessions_by_window(conn, 50.0, 250.0)
        db.close_db(conn)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].id, SESSION_ID)

    def test_no_match(self) -> None:
        """A window that doesn't cover the fixture session returns empty."""
        conn = db.open_db(self.path)
        rows = db.query_sessions_by_window(conn, 1000.0, 2000.0)
        db.close_db(conn)
        self.assertEqual(rows, ())

    def test_multiple_matches(self) -> None:
        """Two sessions in the same window both come back."""
        conn = sqlite3.connect(self.path)
        conn.execute(
            INSERT_SESSION_SQL,
            (OTHER_SESSION_ID, 110.0, 190.0, 1, 0, 5, 5, 0, 0, 0, 1, None, None, "test-model", "/case"),
        )
        conn.commit()
        conn.close()
        conn = db.open_db(self.path)
        rows = db.query_sessions_by_window(conn, 50.0, 250.0)
        db.close_db(conn)
        self.assertEqual({row.id for row in rows}, {SESSION_ID, OTHER_SESSION_ID})

    def test_still_running_session_matches(self) -> None:
        """A session with no ended_at yet (still running, or ended without a
        clean finalize) is found, not silently excluded by a NULL comparison.
        Window chosen well after the base fixture's own ended_at (200) so
        only the still-running session overlaps it.
        """
        conn = sqlite3.connect(self.path)
        conn.execute(
            INSERT_SESSION_SQL,
            (OTHER_SESSION_ID, 210.0, None, 1, 0, 5, 5, 0, 0, 0, 1, None, None, "test-model", "/case"),
        )
        conn.commit()
        conn.close()
        conn = db.open_db(self.path)
        rows = db.query_sessions_by_window(conn, 215.0, 220.0)
        db.close_db(conn)
        self.assertEqual([row.id for row in rows], [OTHER_SESSION_ID])

    def test_still_running_session_started_after_window_does_not_match(self) -> None:
        """An open-ended session is still bounded by its own started_at --
        'open-ended' means no known end, not 'matches every window'.
        """
        conn = sqlite3.connect(self.path)
        conn.execute(
            INSERT_SESSION_SQL,
            (OTHER_SESSION_ID, 500.0, None, 1, 0, 5, 5, 0, 0, 0, 1, None, None, "test-model", "/case"),
        )
        conn.commit()
        conn.close()
        conn = db.open_db(self.path)
        rows = db.query_sessions_by_window(conn, 50.0, 250.0)
        db.close_db(conn)
        self.assertEqual([row.id for row in rows], [SESSION_ID])


class QueryMessagesTest(DbTestCase):
    """Tests for query_messages."""

    def test_messages_in_order_with_content_decoded(self) -> None:
        """Messages come back in id order, with JSON-sentinel content decoded."""
        conn = sqlite3.connect(self.path)
        conn.execute(INSERT_MESSAGE_SQL, (SESSION_ID, "user", "hello", None, None, None, 101.0, None))
        encoded = db.CONTENT_JSON_PREFIX + json.dumps([{"type": "text", "text": "hi"}])
        conn.execute(INSERT_MESSAGE_SQL, (SESSION_ID, "assistant", encoded, None, None, None, 102.0, "stop"))
        conn.commit()
        conn.close()
        conn = db.open_db(self.path)
        rows = db.query_messages(conn, SESSION_ID)
        db.close_db(conn)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].content, "hello")
        self.assertEqual(json.loads(rows[1].content), [{"type": "text", "text": "hi"}])


class DecodeContentTest(unittest.TestCase):
    """Tests for decode_content."""

    def test_none(self) -> None:
        """None decodes to an empty string."""
        self.assertEqual(db.decode_content(None), "")

    def test_plain_text(self) -> None:
        """Plain text passes through unchanged."""
        self.assertEqual(db.decode_content("hello"), "hello")

    def test_json_encoded(self) -> None:
        """Sentinel-prefixed JSON decodes to its structured form."""
        encoded = db.CONTENT_JSON_PREFIX + json.dumps({"a": 1})
        self.assertEqual(json.loads(db.decode_content(encoded)), {"a": 1})

    def test_malformed_json_falls_back_to_raw(self) -> None:
        """A sentinel prefix with invalid JSON after it returns the raw string."""
        broken = db.CONTENT_JSON_PREFIX + "{not valid json"
        self.assertEqual(db.decode_content(broken), broken)


# INLINE RUN
if __name__ == "__main__":
    unittest.main()
