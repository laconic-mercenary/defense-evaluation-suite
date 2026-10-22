# (C) %COMPANY%
"""Scoring and the grade record printed to stdout (one JSON line per grade).

The model only picks the band; code turns it into points here. Each record
carries what produced it (R9): config, file and prompt hashes, reading-rules
version. Never the HTTP headers, which JudgeConfig doesn't hold.
"""

import config
import inputs
import json
import logging
import prompts
import reply
import rubric
import strings

from dataclasses import asdict, dataclass

# CONSTS
LOGGER = logging.getLogger(__name__)
READING_RULES_VERSION = "v1: points must be earned; strictest band wins; Partial = 50% (provisional)"
PROVISIONAL_PARTIAL_FRACTION = 0.5
NO_POINTS = 0.0
LOCATION_FORMAT = "{path}:{line}"
LINE_BREAK = "\n"
FIRST_LINE = 1
TEXT_START = 0
NOT_FOUND = -1


# TYPES
@dataclass(frozen=True)
class Hashes:
    """SHA-256 of every file that shaped a grade."""

    answer_file: str
    rubric: str
    briefing: str
    grader_agents: str
    system_prompt: str
    user_prompt: str


@dataclass(frozen=True)
class RunInfo:
    """What every grade in one run shares: built once per run."""

    run_id: str
    answer_file: str
    reading_rules_version: str
    judge_config: config.JudgeConfig
    hashes: Hashes


@dataclass(frozen=True)
class QuoteLocations:
    """Where each quote was found, as "path:line" (R5). None for the zero-band
    exceptions: "Zero - default" and an empty answer quote.
    """

    rubric_quote: str | None
    answer_quote: str | None


@dataclass(frozen=True)
class GradeRecord:
    """One grade: one rubric entry, one repeat. Printed as a JSON line."""

    run: RunInfo
    question: int
    heading: str
    max_points: int
    repeat: int
    points: float
    provisional: bool
    reply: reply.Reply
    quotes_at: QuoteLocations


# PUBLIC FUNCTIONS
def score(band: str, max_points: int) -> tuple[float, bool]:
    """Return (points, provisional) for band on a question worth max_points.

    Partial is provisionally half the points until case authors set values.
    """
    LOGGER.debug("score(%s, %d)", band, max_points)
    if band == reply.BAND_FULL:
        return float(max_points), False
    if band == reply.BAND_PARTIAL:
        return max_points * PROVISIONAL_PARTIAL_FRACTION, True
    return NO_POINTS, False


def build_run_info(
    run_id: str, judge_config: config.JudgeConfig, templates: prompts.Prompts, run_files: inputs.RunFiles
) -> RunInfo:
    """Return what every grade in this run shares."""
    LOGGER.debug("build_run_info(%s)", run_id)
    return RunInfo(
        run_id=run_id,
        answer_file=run_files.answer.path,
        reading_rules_version=READING_RULES_VERSION,
        judge_config=judge_config,
        hashes=_hashes(templates, run_files),
    )


def build_record(
    run_info: RunInfo, run_files: inputs.RunFiles, entry: rubric.RubricEntry, repeat: int, judge_reply: reply.Reply
) -> GradeRecord:
    """Return the grade record for one validated reply, with its quotes located."""
    LOGGER.debug("build_record(Q%d, repeat %d)", entry.number, repeat)
    points, provisional = score(judge_reply.band, entry.points)
    return GradeRecord(
        run=run_info,
        question=entry.number,
        heading=entry.heading,
        max_points=entry.points,
        repeat=repeat,
        points=points,
        provisional=provisional,
        reply=judge_reply,
        quotes_at=_quote_locations(run_files, entry, judge_reply),
    )


def quote_location(path: str, text: str, quote: str, start: int = TEXT_START) -> str | None:
    """Return "path:line" of quote's first occurrence in text at or after
    start, or None if quote is empty or not found.
    """
    LOGGER.debug("quote_location(%s)", path)
    if strings.is_empty(quote):
        return None
    index = text.find(quote, start)
    if index == NOT_FOUND:
        return None
    return LOCATION_FORMAT.format(path=path, line=text.count(LINE_BREAK, TEXT_START, index) + FIRST_LINE)


def emit(record: GradeRecord) -> None:
    """Print record to stdout as one JSON line."""
    LOGGER.debug("emit(Q%d, repeat %d)", record.question, record.repeat)
    print(json.dumps(asdict(record), ensure_ascii=False), flush=True)


# PRIVATE FUNCTIONS
def _quote_locations(run_files: inputs.RunFiles, entry: rubric.RubricEntry, judge_reply: reply.Reply) -> QuoteLocations:
    """Return where both quotes are. The rubric quote is searched from the
    start of this entry, so a phrase repeated in another entry isn't matched.
    """
    rubric_file = run_files.rubric
    entry_start = max(rubric_file.text.find(entry.text), TEXT_START)
    return QuoteLocations(
        rubric_quote=quote_location(rubric_file.path, rubric_file.text, judge_reply.rubric_quote, entry_start),
        answer_quote=quote_location(run_files.answer.path, run_files.answer.text, judge_reply.answer_quote),
    )


def _hashes(templates: prompts.Prompts, run_files: inputs.RunFiles) -> Hashes:
    """Return the hashes of every file that shapes a grade."""
    return Hashes(
        answer_file=run_files.answer.sha256,
        rubric=run_files.rubric.sha256,
        briefing=run_files.briefing.sha256,
        grader_agents=run_files.grader_agents.sha256,
        system_prompt=templates.system.sha256,
        user_prompt=templates.user.sha256,
    )
