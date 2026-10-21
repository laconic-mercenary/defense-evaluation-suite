# (C) %COMPANY%
"""User-facing string table, keyed by ISO 639-1 language code.

STRINGS is a dict by exception to the no-dict-constants rule (see
CODING_STANDARDS.md). A message missing from a language falls back to
English, so Japanese can be added one message at a time.
"""

import logging

# CONSTS
LOGGER = logging.getLogger(__name__)
LANG_EN = "en"
LANG_JA = "ja"
SUPPORTED_LANGS = (LANG_EN, LANG_JA)
DEFAULT_LANG = LANG_JA
FALLBACK_LANG = LANG_EN

# CONSTS: MESSAGE IDS
MSG_PROG_DESCRIPTION = "prog_description"
MSG_ARG_ANSWER_FILE_HELP = "arg_answer_file_help"
MSG_ARG_ANSWERS_DIR_HELP = "arg_answers_dir_help"
MSG_ARG_LANG_HELP = "arg_lang_help"

# CONSTS: STRING TABLE
STRINGS: dict[str, dict[str, str]] = {
    LANG_EN: {
        MSG_PROG_DESCRIPTION: "Grade an agent's QUESTION_ANSWERS.md against a case's rubric.",
        MSG_ARG_ANSWER_FILE_HELP: "path to the agent's QUESTION_ANSWERS.md",
        MSG_ARG_ANSWERS_DIR_HELP: "path to the case's answer directory (forensic-agent-answers/case-<slug>/)",
        MSG_ARG_LANG_HELP: "language for help and messages: en or ja (default: ja)",
    },
    LANG_JA: {
        MSG_PROG_DESCRIPTION: "エージェントの QUESTION_ANSWERS.md を、ケースの採点基準に照らして採点します。",
        MSG_ARG_ANSWER_FILE_HELP: "エージェントの QUESTION_ANSWERS.md へのパス",
        MSG_ARG_ANSWERS_DIR_HELP: "ケースの解答ディレクトリへのパス(forensic-agent-answers/case-<slug>/)",
        MSG_ARG_LANG_HELP: "ヘルプとメッセージの言語:en または ja(既定値:ja)",
    },
}


# PUBLIC FUNCTIONS
def get_string(lang: str, msg_id: str) -> str:
    """Return message msg_id in lang, falling back to English if lang lacks it."""
    LOGGER.debug("get_string()")
    return STRINGS.get(lang, {}).get(msg_id, STRINGS[FALLBACK_LANG][msg_id])
