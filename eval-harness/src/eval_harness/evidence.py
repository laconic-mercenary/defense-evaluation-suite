# (C) %COMPANY%
"""Evidence log: every prompt sent to the model and every raw reply.

A separate logger that appends JSON Lines to one running file, kept across
runs. Nothing here reaches the normal log (propagate is off). The file holds
answer keys (rubric entries, briefings): protect it like forensic-agent-answers/.
"""

import config
import files
import json
import logging

from dataclasses import asdict, dataclass
from pathlib import Path

# CONSTS
LOGGER = logging.getLogger(__name__)
# Must differ from this module's own name ("evidence"): getLogger returns the
# same logger for the same name, so status lines would land in the file.
EVIDENCE_LOGGER = logging.getLogger("judge_evidence_calls")
EVIDENCE_PATH = config.EVAL_HARNESS_DIR / "logs" / "judge-evidence.jsonl"
EVIDENCE_FORMAT = "%(message)s"


# TYPES
@dataclass(frozen=True)
class CallRecord:
    """One model call. raw_reply is None if the call failed; error says why."""

    run_id: str
    answer_file: str
    question: int
    repeat: int
    system_message: str
    user_message: str
    raw_reply: str | None
    error: str | None


# PUBLIC FUNCTIONS
def open_evidence_log(path: Path = EVIDENCE_PATH) -> None | Exception:
    """Attach the evidence file at path to the evidence logger, creating its
    directory if needed, or return the error. Safe to call more than once.
    """
    LOGGER.debug("open_evidence_log(%s)", path)
    if EVIDENCE_LOGGER.handlers:
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding=files.UTF8)
    except OSError as err:
        LOGGER.error("cannot open the evidence log %s", path, exc_info=err)
        return err
    handler.setFormatter(logging.Formatter(EVIDENCE_FORMAT))
    EVIDENCE_LOGGER.addHandler(handler)
    EVIDENCE_LOGGER.setLevel(logging.INFO)
    EVIDENCE_LOGGER.propagate = False
    LOGGER.info("evidence log: %s", path)
    return None


def record_call(record: CallRecord) -> None:
    """Append one model call to the evidence log as a JSON line."""
    LOGGER.debug("record_call(Q%d, repeat %d)", record.question, record.repeat)
    EVIDENCE_LOGGER.info(json.dumps(asdict(record), ensure_ascii=False))
