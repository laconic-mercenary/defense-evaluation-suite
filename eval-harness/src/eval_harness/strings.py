# (C) %COMPANY%
"""Small string helpers shared across the harness."""

import logging
import re

# CONSTS
LOGGER = logging.getLogger(__name__)


# PUBLIC FUNCTIONS
def trim(value: str) -> str:
    """Return value without leading or trailing whitespace."""
    LOGGER.debug("trim()")
    return value.strip()


def is_empty(value: str | None) -> bool:
    """Return True if value is None, empty, or only whitespace."""
    LOGGER.debug("is_empty()")
    if value is None:
        return True
    return len(trim(value)) == 0


def parse_int(text: str) -> int | Exception:
    """Return text parsed as an integer, or the error if it isn't one."""
    LOGGER.debug("parse_int()")
    try:
        return int(text)
    except ValueError as err:
        LOGGER.error("cannot parse text as an integer: %s", err)
        return err


def parse_float(text: str) -> float | Exception:
    """Return text parsed as a float, or the error if it isn't one."""
    LOGGER.debug("parse_float()")
    try:
        return float(text)
    except ValueError as err:
        LOGGER.error("cannot parse text as a number: %s", err)
        return err


def regex_matches(text: str, pattern: re.Pattern[str]) -> bool:
    """Return True if the whole of text matches pattern.

    Uses fullmatch: re.match only anchors at the start, so "abc$" would
    pass a pattern for "abc".
    """
    LOGGER.debug("regex_matches(pattern=%s)", pattern.pattern)
    return pattern.fullmatch(text) is not None
