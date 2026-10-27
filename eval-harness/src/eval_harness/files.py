# (C) %COMPANY%
"""Generic file helpers. Knows nothing about this program.

read_bytes is the only function with a side effect (it touches the disk);
the others are pure and can be tested with plain bytes.
"""

import hashlib
import logging
import strings

from pathlib import Path

# CONSTS
LOGGER = logging.getLogger(__name__)
UTF8 = "utf-8"


# PUBLIC FUNCTIONS
def read_bytes(path: str) -> bytes | Exception:
    """Return the raw contents of the file at path, or the error."""
    LOGGER.debug("read_bytes(%s)", path)
    if strings.is_empty(path):
        LOGGER.error("cannot read a file: path is empty")
        return ValueError("path is empty")
    try:
        return Path(path).read_bytes()
    except OSError as err:
        LOGGER.error("cannot read file %s", path, exc_info=err)
        return err


def sha256_hex(data: bytes) -> str:
    """Return the SHA-256 hash of data as a hex string."""
    LOGGER.debug("sha256_hex(%d bytes)", len(data))
    return hashlib.sha256(data).hexdigest()


def decode_utf8(data: bytes) -> str | Exception:
    """Return data decoded as UTF-8, or the error if it isn't valid UTF-8."""
    LOGGER.debug("decode_utf8(%d bytes)", len(data))
    try:
        return data.decode(UTF8)
    except UnicodeDecodeError as err:
        LOGGER.error("cannot decode data as UTF-8", exc_info=err)
        return err
