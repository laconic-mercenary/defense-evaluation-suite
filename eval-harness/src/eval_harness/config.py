# (C) %COMPANY%
"""Judge configuration, read from environment variables (twelve-factor).

Getters exit the program if a value is missing or invalid: a misconfigured
run should die immediately. This is the one exception to the Go-style
error convention (see CODING_STANDARDS.md).
"""

import files
import logging
import math
import os
import re
import strings
import sys

from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlparse

# CONSTS
LOGGER = logging.getLogger(__name__)
EXIT_CONFIG_ERROR = 2
MODEL_NAME_PATTERN = re.compile(r"[A-Za-z0-9_\-./:]+")
ALLOWED_URL_SCHEMES = frozenset({"http", "https"})
K_MIN = 1
K_MAX = 3
MAX_TOKENS_MIN = 256
MAX_TOKENS_MAX = 32768
TEMPERATURE_MIN = 0.0
TEMPERATURE_MAX = 1.0

# CONSTS: HTTP HEADERS ("Name=value; Name=value")
HEADER_PAIR_SEPARATOR = ";"
HEADER_NAME_VALUE_SEPARATOR = "="
HEADER_NAME_PATTERN = re.compile(r"[A-Za-z0-9-]+")
HEADER_VALUE_FORBIDDEN = ("\r", "\n")  # a line break would inject extra headers
RESERVED_HEADERS = frozenset({"content-type"})  # set by the adapter; compared lower-case
FIRST_PAIR_NUMBER = 1

# CONSTS: .ENV FILE
DOTENV_FILENAME = ".env"
EVAL_HARNESS_DIR_DEPTH = 2  # config.py -> eval_harness/ -> src/ -> eval-harness/
EVAL_HARNESS_DIR = Path(__file__).resolve().parents[EVAL_HARNESS_DIR_DEPTH]
DOTENV_PATH = EVAL_HARNESS_DIR / DOTENV_FILENAME
DOTENV_COMMENT_PREFIX = "#"
DOTENV_SEPARATOR = "="
DOTENV_QUOTES = ('"', "'")
FIRST_LINE_NUMBER = 1

# CONSTS: ENV VARS
ENV_MODEL_NAME = "JUDGE_MODEL_NAME"
ENV_PROVIDER_URL = "JUDGE_PROVIDER_URL"
ENV_MODEL_VERSION = "JUDGE_MODEL_VERSION"
ENV_K = "JUDGE_K"
ENV_MAX_TOKENS = "JUDGE_MAX_TOKENS"
ENV_TEMPERATURE = "JUDGE_TEMPERATURE"
ENV_HTTP_HEADERS = "JUDGE_HTTP_HEADERS"


# TYPES
@dataclass(frozen=True)
class JudgeConfig:
    """Every setting except the HTTP headers (they may hold credentials). Safe
    to log and to copy into reports.
    """

    model_name: str
    provider_url: str
    model_version: str
    k: int
    max_tokens: int
    temperature: float


# PUBLIC FUNCTIONS
def load_config() -> JudgeConfig:
    """Load .env, then read and validate every setting. The HTTP headers are
    validated here, so a bad value fails at start-up, but kept out of
    JudgeConfig; only their names are logged.
    """
    LOGGER.debug("load_config()")
    load_dotenv()
    LOGGER.info("http headers: %s", [name for name, _ in get_http_headers()])
    return JudgeConfig(
        model_name=get_model_name(),
        provider_url=get_provider_url(),
        model_version=get_model_version(),
        k=get_k(),
        max_tokens=get_max_tokens(),
        temperature=get_temperature(),
    )


def load_dotenv(path: Path = DOTENV_PATH) -> None:
    """Load KEY=value lines from the .env file at path into the environment.

    Exits the program if the file is missing, unreadable or malformed. A
    variable already set in the environment wins over the file. Never logs
    values: the file holds credentials (JUDGE_HTTP_HEADERS).
    """
    LOGGER.debug("load_dotenv(%s)", path)
    text = _read_dotenv(path)
    for number, line in enumerate(text.splitlines(), start=FIRST_LINE_NUMBER):
        entry = _parse_dotenv_line(line)
        if isinstance(entry, Exception):
            _fatal("cannot load %s: line %s is not KEY=value (%s)", path, number, entry)
        if entry is not None:
            os.environ.setdefault(*entry)


def assert_env_var_set(env_name: str) -> str:
    """Return the trimmed value of env_name. Exit the program if it's unset,
    empty or only whitespace.

    Never logs the value: this function also reads JUDGE_HTTP_HEADERS,
    which may hold credentials.
    """
    LOGGER.debug("assert_env_var_set(%s)", env_name)
    value = os.environ.get(env_name)
    if strings.is_empty(value):
        _fatal("required environment variable %s is not set", env_name)
    return strings.trim(value)


def get_model_name() -> str:
    """Return the judge model name. Exit the program if it has invalid characters.

    Allowed: letters, digits, and _ - . / : (e.g. "Qwen/Qwen3-8B").
    """
    LOGGER.debug("get_model_name()")
    value = assert_env_var_set(ENV_MODEL_NAME)
    if not strings.regex_matches(value, MODEL_NAME_PATTERN):
        _fatal("%s may only contain letters, digits, _ - . / :", ENV_MODEL_NAME)
    return value


def get_provider_url() -> str:
    """Return the model server's base URL. Exit the program unless it's an
    http(s) URL with a host (e.g. "http://10.0.0.5:8000/v1").
    """
    LOGGER.debug("get_provider_url()")
    value = assert_env_var_set(ENV_PROVIDER_URL)
    parsed = urlparse(value)
    if parsed.scheme not in ALLOWED_URL_SCHEMES or not parsed.netloc:
        _fatal("%s must be an http(s) URL with a host", ENV_PROVIDER_URL)
    return value


def get_model_version() -> str:
    """Return the judge model version. Exit the program if it has invalid
    characters (same rule as the model name).
    """
    LOGGER.debug("get_model_version()")
    value = assert_env_var_set(ENV_MODEL_VERSION)
    if not strings.regex_matches(value, MODEL_NAME_PATTERN):
        _fatal("%s may only contain letters, digits, _ - . / :", ENV_MODEL_VERSION)
    return value


def get_k() -> int:
    """Return K, the number of repeats per rubric entry. Exit the program
    unless it's an integer from K_MIN to K_MAX.
    """
    LOGGER.debug("get_k()")
    value = strings.parse_int(assert_env_var_set(ENV_K))
    if isinstance(value, Exception):
        _fatal("%s must be an integer", ENV_K)
    if not K_MIN <= value <= K_MAX:
        _fatal("%s must be from %s to %s", ENV_K, K_MIN, K_MAX)
    return value


def get_max_tokens() -> int:
    """Return the cap on how many tokens the model may write per reply. Exit
    the program unless it's an integer from MAX_TOKENS_MIN to MAX_TOKENS_MAX.

    Reasoning models' hidden thinking usually counts toward it: they need far
    more than the ~400 tokens a plain JSON reply takes.
    """
    LOGGER.debug("get_max_tokens()")
    value = strings.parse_int(assert_env_var_set(ENV_MAX_TOKENS))
    if isinstance(value, Exception):
        _fatal("%s must be an integer", ENV_MAX_TOKENS)
    if not MAX_TOKENS_MIN <= value <= MAX_TOKENS_MAX:
        _fatal("%s must be from %s to %s", ENV_MAX_TOKENS, MAX_TOKENS_MIN, MAX_TOKENS_MAX)
    return value


def get_temperature() -> float:
    """Return the sampling temperature. Exit the program unless it's a number
    from TEMPERATURE_MIN to TEMPERATURE_MAX.
    """
    LOGGER.debug("get_temperature()")
    value = strings.parse_float(assert_env_var_set(ENV_TEMPERATURE))
    if isinstance(value, Exception):
        _fatal("%s must be a number", ENV_TEMPERATURE)
    if math.isnan(value) or not TEMPERATURE_MIN <= value <= TEMPERATURE_MAX:
        _fatal("%s must be from %s to %s", ENV_TEMPERATURE, TEMPERATURE_MIN, TEMPERATURE_MAX)
    return value


def get_http_headers() -> tuple[tuple[str, str], ...]:
    """Return the extra HTTP headers as (name, value) pairs, parsed from
    JUDGE_HTTP_HEADERS ("Name=value; Name=value"). Exit the program if the
    value is invalid. Only the provider adapter sends them.

    Never log, print or store the values: they may hold credentials.
    """
    LOGGER.debug("get_http_headers()")
    headers = _parse_headers(assert_env_var_set(ENV_HTTP_HEADERS))
    if isinstance(headers, Exception):
        _fatal("%s is invalid: %s", ENV_HTTP_HEADERS, headers)
    return headers


# PRIVATE FUNCTIONS
def _read_dotenv(path: Path) -> str:
    """Return the text of the .env file at path. Exit the program if it's
    missing, unreadable or not UTF-8.
    """
    if not path.is_file():
        _fatal("cannot load configuration: %s not found", path)
    data = files.read_bytes(str(path))
    if isinstance(data, Exception):
        _fatal("cannot load configuration: %s is unreadable", path)
    text = files.decode_utf8(data)
    if isinstance(text, Exception):
        _fatal("cannot load configuration: %s is not UTF-8", path)
    return text


def _parse_dotenv_line(line: str) -> tuple[str, str] | None | Exception:
    """Return (key, value) for a KEY=value line, None for a blank or comment
    line, or the error if the line is malformed.
    """
    stripped = strings.trim(line)
    if strings.is_empty(stripped) or stripped.startswith(DOTENV_COMMENT_PREFIX):
        return None
    if DOTENV_SEPARATOR not in stripped:
        return ValueError("missing =")
    key, _, value = stripped.partition(DOTENV_SEPARATOR)
    if strings.is_empty(key):
        return ValueError("empty key")
    return strings.trim(key), _unquote(strings.trim(value))


def _unquote(value: str) -> str:
    """Return value without one pair of matching surrounding quotes, if any."""
    for quote in DOTENV_QUOTES:
        if len(value) > len(quote) and value.startswith(quote) and value.endswith(quote):
            return value[len(quote):-len(quote)]
    return value


def _parse_headers(text: str) -> tuple[tuple[str, str], ...] | Exception:
    """Return text's "Name=value" pairs, split on ";" with empty pairs skipped,
    or the error. Error messages never contain header values.
    """
    headers = []
    seen = set()
    for number, pair in enumerate(text.split(HEADER_PAIR_SEPARATOR), start=FIRST_PAIR_NUMBER):
        if strings.is_empty(pair):
            continue
        header = _parse_header(pair, number)
        if isinstance(header, Exception):
            return header
        name, _ = header
        if name.lower() in seen:
            return ValueError(f"header {name} is given twice")
        seen.add(name.lower())
        headers.append(header)
    return tuple(headers) if headers else ValueError("no headers given")


def _parse_header(pair: str, number: int) -> tuple[str, str] | Exception:
    """Return one "Name=value" pair as (name, value), split on the first "=",
    or the error. Error messages name the pair or header, never the value.
    """
    if HEADER_NAME_VALUE_SEPARATOR not in pair:
        return ValueError(f"pair {number} has no {HEADER_NAME_VALUE_SEPARATOR}")
    name, _, value = pair.partition(HEADER_NAME_VALUE_SEPARATOR)
    name, value = strings.trim(name), strings.trim(value)
    if not strings.regex_matches(name, HEADER_NAME_PATTERN):
        return ValueError(f"pair {number}: header names may only contain letters, digits and -")
    if name.lower() in RESERVED_HEADERS:
        return ValueError(f"{name} is set by the harness")
    if strings.is_empty(value) or any(char in value for char in HEADER_VALUE_FORBIDDEN):
        return ValueError(f"{name} has an empty value or a line break in it")
    return name, value


def _fatal(message: str, *args: object) -> NoReturn:
    """Log message as critical, then exit with EXIT_CONFIG_ERROR.

    message is a logging format string; args fill its %s placeholders.
    """
    LOGGER.critical(message, *args)
    sys.exit(EXIT_CONFIG_ERROR)
