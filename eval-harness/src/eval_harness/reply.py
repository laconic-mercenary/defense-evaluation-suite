# (C) %COMPANY%
"""The judge model's reply: parsed and validated before anything uses it.

The reply is untrusted (it can echo the answer file). Never log its text:
error messages name the field that failed, not its content.
"""

import json
import logging
import rubric
import strings

from dataclasses import dataclass, fields as dataclass_fields

# CONSTS
LOGGER = logging.getLogger(__name__)
BAND_FULL = "full"
BAND_PARTIAL = "partial"
BAND_ZERO = "zero"
BANDS = frozenset({BAND_FULL, BAND_PARTIAL, BAND_ZERO})
CONFIDENCES = frozenset({"high", "med", "low"})
ZERO_DEFAULT = "Zero - default"
# Which rubric label must exist in the entry for each non-zero band.
BAND_LABELS = ((BAND_FULL, rubric.LABEL_FULL_CREDIT), (BAND_PARTIAL, rubric.LABEL_PARTIAL))


# TYPES
@dataclass(frozen=True)
class Reply:
    """A validated judge reply. Field order matches the prompt's."""

    rubric_quote: str
    answer_quote: str
    reasons: str
    band: str
    confidence: str



# PUBLIC FUNCTIONS
def parse_reply(raw: str, entry: rubric.RubricEntry, answer_text: str) -> Reply | Exception:
    """Return the model's raw reply as a validated Reply, or the error.

    Checks the JSON shape and values, that the band exists in the entry, and
    that both quotes are verbatim (or the allowed zero-band exceptions).
    """
    LOGGER.debug("parse_reply(Q%d, %d chars)", entry.number, len(raw))
    fields = _parse_json_object(raw)
    if isinstance(fields, Exception):
        LOGGER.error("cannot use the reply for Q%d: not a JSON object", entry.number)
        return fields
    reply = _to_reply(fields)
    if isinstance(reply, Exception):
        LOGGER.error("cannot use the reply for Q%d: wrong fields or values", entry.number)
        return reply
    checked = _check_reply(reply, entry, answer_text)
    if isinstance(checked, Exception):
        LOGGER.error("cannot use the reply for Q%d: it failed a check", entry.number)
        return checked
    return reply


# PRIVATE FUNCTIONS
def _parse_json_object(raw: str) -> dict[str, object] | Exception:
    """Return raw parsed as a JSON object, or the error (code fences included)."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as err:
        return err
    if not isinstance(value, dict):
        return ValueError("reply is JSON but not an object")
    return value


def _to_reply(fields: dict[str, object]) -> Reply | Exception:
    """Return fields as a Reply, or the error unless they are exactly Reply's
    fields, all strings, with an allowed band and confidence.
    """
    expected = tuple(field.name for field in dataclass_fields(Reply))
    if set(fields) != set(expected):
        return ValueError(f"reply must have exactly the fields {list(expected)}")
    if not all(isinstance(value, str) for value in fields.values()):
        return ValueError("every reply field must be a string")
    reply = Reply(**fields)
    if reply.band not in BANDS:
        return ValueError(f"band must be one of {sorted(BANDS)}")
    if reply.confidence not in CONFIDENCES:
        return ValueError(f"confidence must be one of {sorted(CONFIDENCES)}")
    return reply


def _check_reply(reply: Reply, entry: rubric.RubricEntry, answer_text: str) -> None | Exception:
    """Return the first failed check on reply, or None.

    Checks run one at a time and stop at the first failure: a later check
    can log (the empty-answer error), so it mustn't run after an earlier fail.
    """
    band = _check_band(reply, entry)
    if isinstance(band, Exception):
        return band
    rubric_quote = _check_rubric_quote(reply, entry)
    if isinstance(rubric_quote, Exception):
        return rubric_quote
    return _check_answer_quote(reply, entry, answer_text)


def _check_band(reply: Reply, entry: rubric.RubricEntry) -> None | Exception:
    """Return the error if reply's band isn't one the entry has. Zero always is."""
    for band, label in BAND_LABELS:
        if reply.band == band and label not in entry.text:
            return ValueError(f"band {band!r} isn't in rubric entry Q{entry.number}")
    return None


def _check_rubric_quote(reply: Reply, entry: rubric.RubricEntry) -> None | Exception:
    """Return the error unless rubric_quote is verbatim in the entry, or is
    ZERO_DEFAULT with band zero.
    """
    if reply.rubric_quote == ZERO_DEFAULT:
        if reply.band != BAND_ZERO:
            return ValueError(f"{ZERO_DEFAULT!r} is only allowed with band {BAND_ZERO!r}")
        return None
    if strings.is_empty(reply.rubric_quote) or reply.rubric_quote not in entry.text:
        return ValueError(f"rubric_quote isn't verbatim in rubric entry Q{entry.number}")
    return None


def _check_answer_quote(reply: Reply, entry: rubric.RubricEntry, answer_text: str) -> None | Exception:
    """Return the error unless answer_quote is verbatim in the answer file, or
    empty with band zero (no answer: logged as an error, but the run continues).
    """
    if strings.is_empty(reply.answer_quote):
        if reply.band != BAND_ZERO:
            return ValueError(f"an empty answer_quote is only allowed with band {BAND_ZERO!r}")
        LOGGER.error("Q%d: the judge found no answer and graded zero; check it", entry.number)
        return None
    if reply.answer_quote not in answer_text:
        return ValueError(f"answer_quote isn't verbatim in the answer file (Q{entry.number})")
    return None
