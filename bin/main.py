#! /usr/bin/env python
from __future__ import annotations

import contextlib
import sys
import warnings

from loguru import logger

import logit.log
import logit.unwanted
import logit.wanted


def test_log_messages():
    logger.debug('This is a debug message from main.py')
    logger.info('This is an info message from main.py')
    logger.warning('This is a warning message from main.py')
    logger.error('This is an error message from main.py')
    logger.critical('This is a critical message from main.py')
    print('This is a print message from main.py')
    print('This is a print message to stderr from main.py', file=sys.stderr)
    warnings.warn('This is a warnings.warn message from main.py', DeprecationWarning, stacklevel=0)
    warnings.showwarning('This is a warnings.showwarning message from main.py', DeprecationWarning, 'main.py', 24)


def test_logger():
    stdout_stream = logit.log.StreamToLogger(level='INFO')
    stderr_stream = logit.log.StreamToLogger(level='ERROR')
    with contextlib.redirect_stdout(stdout_stream), contextlib.redirect_stderr(stderr_stream):
        test_log_messages()
        logit.wanted.func()
        logit.unwanted.func()


def main():
    logit.log.setup_logger()
    test_logger()


if __name__ == '__main__':
    main()
