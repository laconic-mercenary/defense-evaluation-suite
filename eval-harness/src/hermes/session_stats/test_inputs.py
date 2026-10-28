# (C) %COMPANY%
"""Tests for inputs.py."""

import inputs
import tempfile
import unittest

from pathlib import Path

# CONSTS
DB_PATH = "db_path"
SESSION_ID = "20261028_120000_abc123"


# TYPES
class ParseArgsTest(unittest.TestCase):
    """Tests for parse_args."""

    def test_minimal(self) -> None:
        """Only the required arguments: db_path, starttime, endtime."""
        args = inputs.parse_args([DB_PATH, "--starttime=100", "--endtime=200"])
        self.assertEqual(args.db_path, DB_PATH)
        self.assertIsNone(args.session_id)
        self.assertEqual(args.start_time, 100.0)
        self.assertEqual(args.end_time, 200.0)

    def test_with_session_id(self) -> None:
        """--sessionid is accepted and carried through."""
        args = inputs.parse_args([DB_PATH, f"--sessionid={SESSION_ID}", "--starttime=100", "--endtime=200"])
        self.assertEqual(args.session_id, SESSION_ID)


class ValidateArgsTest(unittest.TestCase):
    """Tests for validate_args."""

    def setUp(self) -> None:
        """Create a real, empty file to use as a valid db_path."""
        self._tmp = tempfile.NamedTemporaryFile(delete=False)
        self._tmp.close()

    def tearDown(self) -> None:
        """Remove the file created in setUp."""
        Path(self._tmp.name).unlink(missing_ok=True)

    def test_valid(self) -> None:
        """A real file and start_time < end_time passes through unchanged."""
        args = inputs.Args(db_path=self._tmp.name, session_id=None, start_time=100.0, end_time=200.0)
        self.assertEqual(inputs.validate_args(args), args)

    def test_missing_file(self) -> None:
        """A db_path that doesn't exist is an error."""
        args = inputs.Args(db_path="/no/such/file.db", session_id=None, start_time=100.0, end_time=200.0)
        result = inputs.validate_args(args)
        self.assertIsInstance(result, Exception)

    def test_directory_not_a_file(self) -> None:
        """A db_path naming a directory is an error."""
        args = inputs.Args(db_path=str(Path(self._tmp.name).parent), session_id=None, start_time=100.0, end_time=200.0)
        result = inputs.validate_args(args)
        self.assertIsInstance(result, Exception)

    def test_start_not_before_end(self) -> None:
        """start_time >= end_time is an error."""
        args = inputs.Args(db_path=self._tmp.name, session_id=None, start_time=200.0, end_time=100.0)
        result = inputs.validate_args(args)
        self.assertIsInstance(result, Exception)


# INLINE RUN
if __name__ == "__main__":
    unittest.main()
