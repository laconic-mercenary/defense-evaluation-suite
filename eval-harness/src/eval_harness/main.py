# (C) %COMPANY%
"""Judge harness entry point: grade one QUESTION_ANSWERS.md against a case's rubric."""

import config
import evidence
import inputs
import logging
import model
import prompts
import reply
import report
import rubric
import secrets
import sys

from dataclasses import dataclass
from datetime import datetime, timezone

# CONSTS
LOGGER = logging.getLogger(__name__)
LOG_FORMAT = "%(levelname)s - %(asctime)s: %(message)s"
EXIT_ERROR = 1
FIRST_REPEAT = 1
RUN_ID_TIME_FORMAT = "%Y%m%dT%H%M%SZ"
RUN_ID_FORMAT = "{time}-{suffix}"
RUN_ID_SUFFIX_BYTES = 3


# TYPES
@dataclass(frozen=True)
class RunContext:
    """Everything one run needs, loaded and validated before any grading."""

    judge_config: config.JudgeConfig
    templates: prompts.Prompts
    run_files: inputs.RunFiles
    entries: tuple[rubric.RubricEntry, ...]


@dataclass(frozen=True)
class Session:
    """A prepared run plus what's fixed for all its calls: the markers, the
    system message (identical every call, for prefix caching) and RunInfo.
    """

    context: RunContext
    markers: prompts.Markers
    system_message: str
    run_info: report.RunInfo


# PUBLIC FUNCTIONS
def main() -> None:
    """Run the harness. The only broad try in the program.

    Errors returned by run() are logged and exit with EXIT_ERROR. Exits from
    argparse and config.* pass straight through: SystemExit isn't an
    Exception, so the broad except doesn't catch it.
    """
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
    """Grade one run, given the command-line arguments (without the program name)."""
    LOGGER.debug("run()")
    args = inputs.parse_args(argv)
    logging.getLogger().setLevel(args.log_level.upper())
    LOGGER.info("answer file: %s | answers directory: %s | language: %s", args.answer_file, args.answers_dir, args.lang)
    judge_config = config.load_config()
    LOGGER.info("config: %s", judge_config)
    context = _prepare(args, judge_config)
    if isinstance(context, Exception):
        LOGGER.error("cannot grade: the run couldn't be prepared")
        return context
    session = _start_session(context)
    if isinstance(session, Exception):
        LOGGER.error("cannot grade: the session couldn't start")
        return session
    return _grade_entries(session)


# PRIVATE FUNCTIONS
def _prepare(args: inputs.Args, judge_config: config.JudgeConfig) -> RunContext | Exception:
    """Load the prompt templates, the run's files and the rubric entries, or
    return the first error.
    """
    templates = prompts.load_prompts()
    if isinstance(templates, Exception):
        LOGGER.error("cannot prepare the run: the prompt templates didn't load")
        return templates
    run_files = inputs.load_run_files(args)
    if isinstance(run_files, Exception):
        LOGGER.error("cannot prepare the run: the run's files didn't load")
        return run_files
    entries = rubric.read_rubric_entries_as_list(run_files.rubric.text)
    if isinstance(entries, Exception):
        LOGGER.error("cannot prepare the run: the rubric didn't parse")
        return entries
    LOGGER.info("rubric: %d entries, %d points in total", len(entries), sum(e.points for e in entries))
    return RunContext(judge_config=judge_config, templates=templates, run_files=run_files, entries=entries)


def _start_session(context: RunContext) -> Session | Exception:
    """Create the run's markers, render the system message, open the evidence
    log and fix the run's ID, or return the first error.
    """
    markers = prompts.create_markers(context.run_files.answer.text)
    if isinstance(markers, Exception):
        LOGGER.error("cannot start the session: the run's markers couldn't be created")
        return markers
    system_message = prompts.render_system(context.templates.system, markers)
    if isinstance(system_message, Exception):
        LOGGER.error("cannot start the session: the system message didn't render")
        return system_message
    opened = evidence.open_evidence_log()
    if isinstance(opened, Exception):
        LOGGER.error("cannot start the session: the evidence log didn't open")
        return opened
    run_info = report.build_run_info(_new_run_id(), context.judge_config, context.templates, context.run_files)
    LOGGER.info("run id: %s", run_info.run_id)
    return Session(context=context, markers=markers, system_message=system_message, run_info=run_info)


def _grade_entries(session: Session) -> None | Exception:
    """Grade every rubric entry K times, in order. Stops at the first error."""
    repeats = range(FIRST_REPEAT, session.context.judge_config.k + FIRST_REPEAT)
    for entry in session.context.entries:
        for repeat in repeats:
            LOGGER.info("grading Q%d (%d pts), repeat %d", entry.number, entry.points, repeat)
            graded = _grade_once(session, entry, repeat)
            if isinstance(graded, Exception):
                LOGGER.error("cannot grade Q%d, repeat %d", entry.number, repeat)
                return graded
    LOGGER.info("run %s complete", session.run_info.run_id)
    return None


def _grade_once(session: Session, entry: rubric.RubricEntry, repeat: int) -> None | Exception:
    """Ask the model to grade entry once, validate the reply, and print the
    grade record, or return the first error.
    """
    raw = _ask_model(session, entry, repeat)
    if isinstance(raw, Exception):
        return raw
    judge_reply = reply.parse_reply(raw, entry, session.context.run_files.answer.text)
    if isinstance(judge_reply, Exception):
        return judge_reply
    report.emit(report.build_record(session.run_info, session.context.run_files, entry, repeat, judge_reply))
    LOGGER.info("Q%d, repeat %d: %s (confidence %s)", entry.number, repeat, judge_reply.band, judge_reply.confidence)
    return None


def _ask_model(session: Session, entry: rubric.RubricEntry, repeat: int) -> str | Exception:
    """Render entry's user message, call the model, and record the call in
    the evidence log, failed or not. Returns the raw reply, or the error.
    """
    context = session.context
    user_message = prompts.render_user(context.templates.user, session.markers, context.run_files, entry)
    if isinstance(user_message, Exception):
        return user_message
    raw = model.call_model(context.judge_config, session.system_message, user_message)
    failed = isinstance(raw, Exception)
    evidence.record_call(evidence.CallRecord(
        run_id=session.run_info.run_id, answer_file=context.run_files.answer.path,
        question=entry.number, repeat=repeat,
        system_message=session.system_message, user_message=user_message,
        raw_reply=None if failed else raw, error=repr(raw) if failed else None,
    ))
    return raw


def _new_run_id() -> str:
    """Return a new run ID: UTC start time plus a short random suffix."""
    time = datetime.now(timezone.utc).strftime(RUN_ID_TIME_FORMAT)
    return RUN_ID_FORMAT.format(time=time, suffix=secrets.token_hex(RUN_ID_SUFFIX_BYTES))


# INLINE RUN
if __name__ == "__main__":
    main()
