"""Handle logging."""

import logging
import sys

logger = logging.getLogger('hyper-128t')


def to_string(*messages):
    """Convert list of messages at variable length to single string."""
    return ' '.join((map(str, messages)))


def set_log_level(level):
    """Set global log level."""
    logger.setLevel(level)
    # format messages nicely
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(sh)
    # avoid propagation of messages to root logger
    logger.propagate = False


def debug(*messages):
    """Log debug messages."""
    logger.debug(to_string(*messages))


def info(*messages):
    """Log info message."""
    logger.info(to_string(*messages))


def fatal(*messages):
    """Log fatal message and exit."""
    logger.fatal(to_string(*messages, 'Abort.'))
    sys.exit(1)
