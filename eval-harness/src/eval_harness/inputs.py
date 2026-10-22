# (C) %COMPANY%
"""Program inputs: command-line arguments, and the files they point to."""

import argparse
import files
import iso
import logging
import strings

from dataclasses import dataclass
from pathlib import Path

# CONSTS
LOGGER = logging.getLogger(__name__)
MD_EXTENSION = ".md"
RUBRIC_FILENAME = "grading_schema.md"
BRIEFING_FILENAME = "BRIEFING.md"
GRADER_AGENTS_FILENAME = "AGENTS.md"
CASE_FILENAMES = (RUBRIC_FILENAME, BRIEFING_FILENAME, GRADER_AGENTS_FILENAME)
ARG_ANSWER_FILE = "answer_file"
ARG_ANSWERS_DIR = "answers_dir"
ARG_LANG_FLAG = "--lang"
ARG_LANG = "lang"
ARG_LOG_LEVEL_FLAG = "--log-level"
ARG_LOG_LEVEL = "log_level"
LOG_LEVELS = ("debug", "info", "warning", "error")
DEFAULT_LOG_LEVEL = "info"


# TYPES
@dataclass(frozen=True)
class Args:
    """The program's command-line arguments, as given (paths not yet validated)."""

    answer_file: str
    answers_dir: str
    lang: str
    log_level: str


@dataclass(frozen=True)
class CaseFilePaths:
    """Validated paths to the three answer-bundle files the judge reads."""

    rubric: str
    briefing: str
    grader_agents: str


@dataclass(frozen=True)
class InputFile:
    """A file read into memory once. sha256 is the hash of its exact bytes,
    logged for the run and recorded as its version (R9).
    """

    path: str
    text: str
    sha256: str


@dataclass(frozen=True)
class RunFiles:
    """The four files one judge run reads, each read into memory and hashed."""

    answer: InputFile
    rubric: InputFile
    briefing: InputFile
    grader_agents: InputFile


# PUBLIC FUNCTIONS
def parse_args(argv: list[str]) -> Args:
    """Parse argv (without the program name) into Args.

    Two passes: --lang is read first, so the full parser's help text can be
    built in that language. argparse exits the program itself on bad
    arguments, the same way the config getters do. Its own built-in words
    ("usage:", error messages) stay English.
    """
    LOGGER.debug("parse_args(%s)", argv)
    lang = _read_lang(argv)
    namespace = _build_parser(lang).parse_args(argv)
    args = Args(
        answer_file=getattr(namespace, ARG_ANSWER_FILE),
        answers_dir=getattr(namespace, ARG_ANSWERS_DIR),
        lang=getattr(namespace, ARG_LANG),
        log_level=getattr(namespace, ARG_LOG_LEVEL),
    )
    return args


def load_run_files(args: Args) -> RunFiles | Exception:
    """Return the answer file and the three case files from args, each read
    into memory and hashed, or the first error. Logs each file's hash.
    """
    LOGGER.debug("load_run_files()")
    case_paths = get_case_file_paths(args)
    if isinstance(case_paths, Exception):
        LOGGER.error("cannot load the run's files")
        return case_paths
    paths = (args.answer_file, case_paths.rubric, case_paths.briefing, case_paths.grader_agents)
    read_files = read_input_files(paths)
    if isinstance(read_files, Exception):
        LOGGER.error("cannot load the run's files")
        return read_files
    answer, rubric, briefing, grader_agents = read_files
    return RunFiles(answer=answer, rubric=rubric, briefing=briefing, grader_agents=grader_agents)


def read_input_files(paths: tuple[str, ...]) -> tuple[InputFile, ...] | Exception:
    """Return each file in paths read into memory and hashed, in order, or the
    first error. Logs each file's hash.
    """
    LOGGER.debug("read_input_files(%d paths)", len(paths))
    read_files = []
    for path in paths:
        read_file = read_input_file(path)
        if isinstance(read_file, Exception):
            LOGGER.error("cannot read input files")
            return read_file
        LOGGER.info("input file %s sha256=%s", read_file.path, read_file.sha256)
        read_files.append(read_file)
    return tuple(read_files)


def get_case_file_paths(args: Args) -> CaseFilePaths | Exception:
    """Return the validated rubric, briefing and grader AGENTS.md paths from
    the answers directory in args, or the first error.
    """
    LOGGER.debug("get_case_file_paths(%s)", args.answers_dir)
    answers_dir = validate_dir_path(args.answers_dir)
    if isinstance(answers_dir, Exception):
        LOGGER.error("cannot get case file paths from %s", args.answers_dir)
        return answers_dir
    paths = []
    for filename in CASE_FILENAMES:
        path = _case_file_path(answers_dir, filename)
        if isinstance(path, Exception):
            LOGGER.error("cannot get case file paths from %s", answers_dir)
            return path
        paths.append(path)
    rubric, briefing, grader_agents = paths
    return CaseFilePaths(rubric=rubric, briefing=briefing, grader_agents=grader_agents)


def read_input_file(path: str) -> InputFile | Exception:
    """Return the .md file at path read into memory and hashed, or the error.

    Fails if the path isn't a valid .md file, isn't UTF-8, or is empty.
    """
    LOGGER.debug("read_input_file(%s)", path)
    valid_path = validate_md_path(path)
    if isinstance(valid_path, Exception):
        LOGGER.error("cannot read input file %s", path)
        return valid_path
    data = files.read_bytes(valid_path)
    if isinstance(data, Exception):
        LOGGER.error("cannot read input file %s", path)
        return data
    text = _decode_non_empty(valid_path, data)
    if isinstance(text, Exception):
        LOGGER.error("cannot read input file %s", path)
        return text
    return InputFile(path=valid_path, text=text, sha256=files.sha256_hex(data))


def validate_dir_path(path: str) -> str | Exception:
    """Return path if it names an existing directory, or the error."""
    LOGGER.debug("validate_dir_path(%s)", path)
    problem = _dir_path_problem(path)
    if problem is not None:
        LOGGER.error("cannot use directory %r: %s", path, problem)
        return ValueError(f"{problem}: {path!r}")
    return path


def validate_md_path(path: str) -> str | Exception:
    """Return path if it names an existing, regular .md file, or the error.

    Shared by the answer file and the answer-bundle files.
    """
    LOGGER.debug("validate_md_path(%s)", path)
    problem = _md_path_problem(path)
    if problem is not None:
        LOGGER.error("cannot use file %r: %s", path, problem)
        return ValueError(f"{problem}: {path!r}")
    return path


# PRIVATE FUNCTIONS
def _md_path_problem(path: str) -> str | None:
    """Return why path isn't an existing, regular .md file, or None if it is."""
    if strings.is_empty(path):
        return "path is empty"
    file = Path(path)
    if not file.exists():
        return "no such file"
    if not file.is_file():
        return "not a regular file"
    if file.suffix != MD_EXTENSION:
        return f"not a {MD_EXTENSION} file"
    return None


def _dir_path_problem(path: str) -> str | None:
    """Return why path isn't an existing directory, or None if it is."""
    if strings.is_empty(path):
        return "path is empty"
    directory = Path(path)
    if not directory.exists():
        return "no such directory"
    if not directory.is_dir():
        return "not a directory"
    return None


def _decode_non_empty(path: str, data: bytes) -> str | Exception:
    """Return data decoded as UTF-8, or the error if it isn't UTF-8 or is empty."""
    text = files.decode_utf8(data)
    if isinstance(text, Exception):
        return text
    if strings.is_empty(text):
        LOGGER.error("cannot use file %s: it is empty", path)
        return ValueError(f"file is empty: {path}")
    return text


def _case_file_path(answers_dir: str, filename: str) -> str | Exception:
    """Return the validated path of filename inside answers_dir, or the error."""
    return validate_md_path(str(Path(answers_dir) / filename))


def _read_lang(argv: list[str]) -> str:
    """First pass: return the --lang value, ignoring every other argument."""
    parser = argparse.ArgumentParser(add_help=False)
    _add_lang_argument(parser, iso.DEFAULT_LANG)
    namespace, _ = parser.parse_known_args(argv)
    return getattr(namespace, ARG_LANG)


def _build_parser(lang: str) -> argparse.ArgumentParser:
    """Second pass: return the full parser, with help text in lang."""
    parser = argparse.ArgumentParser(description=iso.get_string(lang, iso.MSG_PROG_DESCRIPTION))
    parser.add_argument(ARG_ANSWER_FILE, help=iso.get_string(lang, iso.MSG_ARG_ANSWER_FILE_HELP))
    parser.add_argument(ARG_ANSWERS_DIR, help=iso.get_string(lang, iso.MSG_ARG_ANSWERS_DIR_HELP))
    _add_lang_argument(parser, lang)
    parser.add_argument(
        ARG_LOG_LEVEL_FLAG,
        dest=ARG_LOG_LEVEL,
        choices=LOG_LEVELS,
        default=DEFAULT_LOG_LEVEL,
        help=iso.get_string(lang, iso.MSG_ARG_LOG_LEVEL_HELP),
    )
    return parser


def _add_lang_argument(parser: argparse.ArgumentParser, lang: str) -> None:
    """Add the --lang option, with its help text in lang."""
    parser.add_argument(
        ARG_LANG_FLAG,
        dest=ARG_LANG,
        choices=iso.SUPPORTED_LANGS,
        default=iso.DEFAULT_LANG,
        help=iso.get_string(lang, iso.MSG_ARG_LANG_HELP),
    )
