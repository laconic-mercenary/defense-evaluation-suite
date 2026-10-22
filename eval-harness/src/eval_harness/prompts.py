# (C) %COMPANY%
"""Prompt templates, read once from eval-harness/prompts/ and kept in memory."""

import config
import inputs
import logging
import rubric
import secrets

from dataclasses import dataclass
from pathlib import Path
from string import Template

# CONSTS
LOGGER = logging.getLogger(__name__)
PROMPTS_DIR = config.EVAL_HARNESS_DIR / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "system.md"
USER_PROMPT_PATH = PROMPTS_DIR / "user.md"

# CONSTS: RUN MARKERS (around the untrusted answer file)
NONCE_BYTES = 16  # 32 hex characters: unguessable, and never collides in practice
MARKER_START_FORMAT = "<<ANSWER-START-{nonce}>>"
MARKER_END_FORMAT = "<<ANSWER-END-{nonce}>>"

# CONSTS: PLACEHOLDERS (names used in the .md templates)
PLACEHOLDER_ANSWER_START = "answer_start"
PLACEHOLDER_ANSWER_END = "answer_end"
PLACEHOLDER_GRADER_INSTRUCTIONS = "grader_instructions"
PLACEHOLDER_BRIEFING = "briefing"
PLACEHOLDER_ANSWER_FILE = "answer_file"
PLACEHOLDER_RUBRIC_ENTRY = "rubric_entry"
PLACEHOLDER_QUESTION_NUMBER = "question_number"
SYSTEM_PROMPT_PLACEHOLDERS = frozenset({PLACEHOLDER_ANSWER_START, PLACEHOLDER_ANSWER_END})
USER_PROMPT_PLACEHOLDERS = frozenset({
    PLACEHOLDER_GRADER_INSTRUCTIONS,
    PLACEHOLDER_BRIEFING,
    PLACEHOLDER_ANSWER_START,
    PLACEHOLDER_ANSWER_FILE,
    PLACEHOLDER_ANSWER_END,
    PLACEHOLDER_RUBRIC_ENTRY,
    PLACEHOLDER_QUESTION_NUMBER,
})


# TYPES
@dataclass(frozen=True)
class PromptTemplate:
    """A prompt template read into memory once. sha256 is the hash of the
    file's exact bytes: the prompt version recorded with every grade (R9).
    """

    path: str
    template: Template
    sha256: str


@dataclass(frozen=True)
class Prompts:
    """Both prompt templates a run needs, loaded once at start-up."""

    system: PromptTemplate
    user: PromptTemplate


@dataclass(frozen=True)
class Markers:
    """The start and end markers around the answer file, one pair per run.
    Generated after the answer file was written, so the agent can't know them.
    """

    start: str
    end: str


# PUBLIC FUNCTIONS
def create_markers(answer_text: str) -> Markers | Exception:
    """Return a fresh pair of run markers, or the error if the answer file
    already contains their nonce (it would let the answer fake the boundary).
    """
    LOGGER.debug("create_markers(%d chars)", len(answer_text))
    nonce = secrets.token_hex(NONCE_BYTES)
    if nonce in answer_text:
        LOGGER.error("cannot use the run's markers: the answer file contains the nonce")
        return ValueError("the answer file contains the run's marker nonce")
    LOGGER.debug("run marker nonce %s", nonce)
    return Markers(start=MARKER_START_FORMAT.format(nonce=nonce), end=MARKER_END_FORMAT.format(nonce=nonce))


def load_prompts() -> Prompts | Exception:
    """Return the system and user templates from their default paths, or the
    first error.
    """
    LOGGER.debug("load_prompts()")
    system = load_system_prompt()
    if isinstance(system, Exception):
        LOGGER.error("cannot load the prompts")
        return system
    user = load_user_prompt()
    if isinstance(user, Exception):
        LOGGER.error("cannot load the prompts")
        return user
    return Prompts(system=system, user=user)


def load_system_prompt(path: Path = SYSTEM_PROMPT_PATH) -> PromptTemplate | Exception:
    """Return the system prompt template at path, or the error."""
    LOGGER.debug("load_system_prompt(%s)", path)
    return _load_prompt(path, SYSTEM_PROMPT_PLACEHOLDERS)


def load_user_prompt(path: Path = USER_PROMPT_PATH) -> PromptTemplate | Exception:
    """Return the user message template at path, or the error."""
    LOGGER.debug("load_user_prompt(%s)", path)
    return _load_prompt(path, USER_PROMPT_PLACEHOLDERS)


def render_system(template: PromptTemplate, markers: Markers) -> str | Exception:
    """Return the system message: the template with the run's markers filled in."""
    LOGGER.debug("render_system()")
    values = {PLACEHOLDER_ANSWER_START: markers.start, PLACEHOLDER_ANSWER_END: markers.end}
    return _substitute(template, values)


def render_user(
    template: PromptTemplate, markers: Markers, run_files: inputs.RunFiles, entry: rubric.RubricEntry
) -> str | Exception:
    """Return the user message for one rubric entry: the template with the
    case files, the answer file inside the run's markers, and the entry.
    """
    LOGGER.debug("render_user(Q%d)", entry.number)
    return _substitute(template, _user_values(markers, run_files, entry))


# PRIVATE FUNCTIONS
def _user_values(markers: Markers, run_files: inputs.RunFiles, entry: rubric.RubricEntry) -> dict[str, str]:
    """Return the placeholder values for one rubric entry's user message."""
    return {
        PLACEHOLDER_GRADER_INSTRUCTIONS: run_files.grader_agents.text,
        PLACEHOLDER_BRIEFING: run_files.briefing.text,
        PLACEHOLDER_ANSWER_START: markers.start,
        PLACEHOLDER_ANSWER_FILE: run_files.answer.text,
        PLACEHOLDER_ANSWER_END: markers.end,
        PLACEHOLDER_RUBRIC_ENTRY: entry.text,
        PLACEHOLDER_QUESTION_NUMBER: str(entry.number),
    }


def _substitute(template: PromptTemplate, values: dict[str, str]) -> str | Exception:
    """Return template filled with values, or the error if a placeholder has
    no value. Placeholders in the values themselves are never parsed.
    """
    try:
        return template.template.substitute(values)
    except (KeyError, ValueError) as err:
        LOGGER.error("cannot render prompt template %s", template.path, exc_info=err)
        return err


def _load_prompt(path: Path, required: frozenset[str]) -> PromptTemplate | Exception:
    """Return the template at path, or the error.

    Fails if the file isn't a readable, non-empty UTF-8 .md file, or its
    placeholders fail _check_placeholders. Logs the hash.
    """
    prompt_file = inputs.read_input_file(str(path))
    if isinstance(prompt_file, Exception):
        LOGGER.error("cannot load the prompt template %s", path)
        return prompt_file
    template = Template(prompt_file.text)
    placeholders = _check_placeholders(template, required)
    if isinstance(placeholders, Exception):
        LOGGER.error("cannot load the prompt template %s", path)
        return placeholders
    LOGGER.info("prompt template %s sha256=%s", path, prompt_file.sha256)
    return PromptTemplate(path=prompt_file.path, template=template, sha256=prompt_file.sha256)


def _check_placeholders(template: Template, required: frozenset[str]) -> None | Exception:
    """Return the error if template has a malformed $ placeholder (a literal $
    must be written $$) or lacks any required placeholder, else None.
    """
    if not template.is_valid():
        LOGGER.error("malformed $ placeholder (write a literal $ as $$)")
        return ValueError("malformed $ placeholder")
    missing = required - set(template.get_identifiers())
    if missing:
        LOGGER.error("missing required placeholders: %s", sorted(missing))
        return ValueError(f"missing required placeholders: {sorted(missing)}")
    return None
