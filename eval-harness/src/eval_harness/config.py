# (C) %COMPANY%
"""Judge configuration, read from environment variables (twelve-factor).

Getters exit the program if a value is missing or invalid: a misconfigured
run should die immediately. This is the one exception to the Go-style
error convention (see CODING_STANDARDS.md).
"""

import logging
import math
import os
import re
import strings
import sys

from dataclasses import dataclass
from typing import NoReturn
from urllib.parse import urlparse

# CONSTS
LOGGER = logging.getLogger(__name__)
EXIT_CONFIG_ERROR = 2
MODEL_NAME_PATTERN = re.compile(r"[A-Za-z0-9_\-./:]+")
ALLOWED_URL_SCHEMES = frozenset({"http", "https"})
K_MIN = 1
K_MAX = 3
TEMPERATURE_MIN = 0.0
TEMPERATURE_MAX = 1.0

# CONSTS: ENV VARS
ENV_MODEL_NAME = "JUDGE_MODEL_NAME"
ENV_PROVIDER_URL = "JUDGE_PROVIDER_URL"
ENV_MODEL_VERSION = "JUDGE_MODEL_VERSION"
ENV_K = "JUDGE_K"
ENV_TEMPERATURE = "JUDGE_TEMPERATURE"
ENV_API_KEY = "JUDGE_API_KEY"


# TYPES
@dataclass(frozen=True)
class JudgeConfig:
    """Every setting except the API key. Safe to log and to copy into reports."""

    model_name: str
    provider_url: str
    model_version: str
    k: int
    temperature: float


# PUBLIC FUNCTIONS
def load_config() -> JudgeConfig:
    """Read and validate every setting except the API key."""
    LOGGER.debug("load_config()")
    return JudgeConfig(
        model_name=get_model_name(),
        provider_url=get_provider_url(),
        model_version=get_model_version(),
        k=get_k(),
        temperature=get_temperature(),
    )


def assert_env_var_set(env_name: str) -> str:
    """Return the trimmed value of env_name. Exit the program if it's unset,
    empty or only whitespace.

    Never logs the value: this function also reads the API key.
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


def get_api_key() -> str:
    """Return the API key. Only the provider adapter calls this.

    Never log, print or store the result. It is deliberately not part of
    JudgeConfig.
    """
    LOGGER.debug("get_api_key()")
    return assert_env_var_set(ENV_API_KEY)


# PRIVATE FUNCTIONS
def _fatal(message: str, *args: object) -> NoReturn:
    """Log message as critical, then exit with EXIT_CONFIG_ERROR.

    message is a logging format string; args fill its %s placeholders.
    """
    LOGGER.critical(message, *args)
    sys.exit(EXIT_CONFIG_ERROR)
