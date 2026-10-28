# (C) %COMPANY%
"""session_stats entry point: read session telemetry from a Hermes state.db."""

import db
import inputs
import logging
import report
import resolve
import sys

# CONSTS
LOGGER = logging.getLogger(__name__)
LOG_FORMAT = "%(levelname)s - %(asctime)s: %(message)s"
EXIT_ERROR = 1


# PUBLIC FUNCTIONS
def main() -> None:
    """Run session_stats. The only broad try in the program."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    LOGGER.debug("main()")
    try:
        error = run(sys.argv[1:])
    except Exception:
        LOGGER.exception("unexpected error")
        sys.exit(EXIT_ERROR)
    if isinstance(error, Exception):
        LOGGER.critical("run failed", exc_info=error)
        sys.exit(EXIT_ERROR)


def run(argv: list[str]) -> None | Exception:
    """Resolve one session from argv and print its report, or return the
    first error.
    """
    LOGGER.debug("run()")
    args = inputs.validate_args(inputs.parse_args(argv))
    if isinstance(args, Exception):
        LOGGER.error("cannot run: the arguments are invalid")
        return args
    conn = db.open_db(args.db_path)
    if isinstance(conn, Exception):
        LOGGER.error("cannot run: the database didn't open")
        return conn
    try:
        return _report_session(conn, args)
    finally:
        db.close_db(conn)


# PRIVATE FUNCTIONS
def _report_session(conn, args: inputs.Args) -> None | Exception:
    """Resolve args to one session, load its messages and print the report,
    or return the first error.
    """
    session = resolve.resolve_session(conn, args)
    if isinstance(session, Exception):
        LOGGER.error("cannot report: the session couldn't be resolved")
        return session
    messages = db.query_messages(conn, session.id)
    if isinstance(messages, Exception):
        LOGGER.error("cannot report: the messages couldn't be loaded")
        return messages
    report.emit(report.build_report(session, messages))
    LOGGER.info("reported session %s: %d messages", session.id, len(messages))
    return None


# INLINE RUN
if __name__ == "__main__":
    main()
