# (C) %COMPANY%
"""Provider adapter: one chat call to an OpenAI-compatible server.

The only module that sends the HTTP headers from JUDGE_HTTP_HEADERS. Never
log the request: its headers may carry credentials.
"""

import config
import files
import json
import logging
import urllib.error
import urllib.request

# CONSTS
LOGGER = logging.getLogger(__name__)
CHAT_COMPLETIONS_PATH = "/chat/completions"
URL_PATH_SEPARATOR = "/"
TIMEOUT_SECONDS = 300
HTTP_METHOD_POST = "POST"
HEADER_CONTENT_TYPE = "Content-Type"
CONTENT_TYPE_JSON = "application/json"
FIRST_CHOICE = 0
ERROR_BODY_MAX_CHARS = 500  # enough for a server's explanation; it could echo request text
DECODE_REPLACE = "replace"
NO_ERROR_BODY = ""

# CONSTS: OPENAI-COMPATIBLE PROTOCOL
FIELD_MODEL = "model"
FIELD_TEMPERATURE = "temperature"
FIELD_MAX_TOKENS = "max_tokens"
FIELD_MESSAGES = "messages"
FIELD_ROLE = "role"
FIELD_CONTENT = "content"
FIELD_CHOICES = "choices"
FIELD_MESSAGE = "message"
FIELD_FINISH_REASON = "finish_reason"
FINISH_REASON_LENGTH = "length"  # the server stopped because it hit max_tokens
ROLE_SYSTEM = "system"
ROLE_USER = "user"


# PUBLIC FUNCTIONS
def call_model(judge_config: config.JudgeConfig, system_message: str, user_message: str) -> str | Exception:
    """Send one system + user message pair and return the model's reply text,
    or the error (network failure, HTTP error, or a malformed response).
    """
    LOGGER.debug("call_model(%s)", judge_config.model_name)
    request = _build_request(judge_config, system_message, user_message)
    body = _post(request)
    if isinstance(body, Exception):
        LOGGER.error("cannot get a reply from the model at %s", judge_config.provider_url)
        return body
    content = _extract_content(body)
    if isinstance(content, Exception):
        LOGGER.error("cannot read the model's reply from %s", judge_config.provider_url)
        return content
    return content


# PRIVATE FUNCTIONS
def _build_request(judge_config: config.JudgeConfig, system_message: str, user_message: str) -> urllib.request.Request:
    """Return the HTTP request for one chat call: Content-Type plus the
    configured headers (which may carry credentials).
    """
    url = judge_config.provider_url.rstrip(URL_PATH_SEPARATOR) + CHAT_COMPLETIONS_PATH
    data = json.dumps(_payload(judge_config, system_message, user_message)).encode(files.UTF8)
    headers = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON, **dict(config.get_http_headers())}
    return urllib.request.Request(url, data=data, headers=headers, method=HTTP_METHOD_POST)


def _payload(judge_config: config.JudgeConfig, system_message: str, user_message: str) -> dict[str, object]:
    """Return the JSON body for one chat call (no secrets in it)."""
    return {
        FIELD_MODEL: judge_config.model_name,
        FIELD_TEMPERATURE: judge_config.temperature,
        FIELD_MAX_TOKENS: judge_config.max_tokens,
        FIELD_MESSAGES: [
            {FIELD_ROLE: ROLE_SYSTEM, FIELD_CONTENT: system_message},
            {FIELD_ROLE: ROLE_USER, FIELD_CONTENT: user_message},
        ],
    }


def _post(request: urllib.request.Request) -> bytes | Exception:
    """Return the response body, or the error. Never logs the request."""
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except urllib.error.HTTPError as err:
        # The server answered with an error status. Its body usually says why
        # (e.g. "model not found"); log the start of it, never the request.
        LOGGER.error("the model server returned HTTP %s: %s", err.code, _error_body(err), exc_info=err)
        return err
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        LOGGER.error("cannot reach the model server", exc_info=err)
        return err


def _error_body(err: urllib.error.HTTPError) -> str:
    """Return the first ERROR_BODY_MAX_CHARS of an HTTP error's body, or an
    empty string if it can't be read.
    """
    try:
        data = err.read()
    except OSError:
        return NO_ERROR_BODY
    return data.decode(files.UTF8, errors=DECODE_REPLACE)[:ERROR_BODY_MAX_CHARS]


def _extract_content(body: bytes) -> str | Exception:
    """Return the reply text from an OpenAI-compatible response body, or the
    error (malformed response, cut off at max_tokens, or not a string).
    """
    text = files.decode_utf8(body)
    if isinstance(text, Exception):
        return text
    choice = _first_choice(text)
    if isinstance(choice, Exception):
        return choice
    # Truncation check. At max_tokens the server stops mid-reply and still
    # returns HTTP 200, so the JSON would just look malformed later. Catch it
    # here, where finish_reason says why the reply ended, and say so plainly.
    if choice.get(FIELD_FINISH_REASON) == FINISH_REASON_LENGTH:
        LOGGER.error("cannot use the model's reply: it was cut off at max_tokens (raise %s)", config.ENV_MAX_TOKENS)
        return ValueError(f"the reply was cut off at max_tokens; raise {config.ENV_MAX_TOKENS}")
    content = choice[FIELD_MESSAGE][FIELD_CONTENT]
    if not isinstance(content, str):
        LOGGER.error("cannot use the model's response: its reply text isn't a string")
        return ValueError("the model's reply text isn't a string")
    return content


def _first_choice(text: str) -> dict[str, object] | Exception:
    """Return the first choice of a response, or the error unless it's a dict
    holding message.content.
    """
    try:
        choice = json.loads(text)[FIELD_CHOICES][FIRST_CHOICE]
        choice[FIELD_MESSAGE][FIELD_CONTENT]  # only checks the shape: raises if it's missing
    except (ValueError, KeyError, IndexError, TypeError) as err:
        LOGGER.error("cannot find the reply text in the model's response", exc_info=err)
        return err
    if not isinstance(choice, dict):
        LOGGER.error("cannot use the model's response: its first choice isn't an object")
        return ValueError("the model's first choice isn't an object")
    return choice
