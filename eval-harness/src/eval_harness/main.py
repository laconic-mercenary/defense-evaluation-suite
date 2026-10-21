# (C) %COMPANY%
"""Judge harness entry point: grade one QUESTION_ANSWERS.md against a case's rubric."""

import config
import inputs
import logging
import sys

# CONSTS
LOGGER = logging.getLogger(__name__)
LOG_FORMAT = "%(levelname)s - %(asctime)s: %(message)s"
EXIT_ERROR = 1


# PUBLIC FUNCTIONS
def main() -> None:
    """Run the harness. The only broad try in the program.

    Errors returned by run() are logged and exit with EXIT_ERROR. Exits from
    argparse and config.* pass straight through: SystemExit isn't an
    Exception, so the broad except doesn't catch it.
    """
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    LOGGER.debug("main()")
    try:
        error = run(sys.argv[1:])
    except Exception:
        LOGGER.exception("unexpected error")
        sys.exit(EXIT_ERROR)
    if isinstance(error, Exception):
        LOGGER.critical("run failed", exc_info=error)
        sys.exit(EXIT_ERROR)


def run(argv: list[str]) -> None | Exception:
    """Grade one run, given the command-line arguments (without the program name)."""
    LOGGER.debug("run()")
    LOGGER.info("starting up...")
    args = inputs.parse_args(argv)
    LOGGER.info("answer file: %s", args.answer_file)
    LOGGER.info("answers directory: %s", args.answers_dir)
    LOGGER.info("language: %s", args.lang)
    judge_config = config.load_config()
    LOGGER.info("config: %s", judge_config)
    return None


# INLINE RUN
if __name__ == "__main__":
    main()
