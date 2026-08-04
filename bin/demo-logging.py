#! /usr/bin/env python
"""Visual end-to-end demo of every capture path logit handles.

Writes to log/ in the repo. For assertions on this behaviour see src/tests/.
"""

import contextlib
import multiprocessing
import sys
import threading
import warnings

import joblib
import loguru

import logit.base
import tests.emitters.some_lib
import tests.emitters.unwanted
import tests.emitters.wanted

DISABLED = ['tests.emitters.unwanted']


def log_messages():
    loguru.logger.debug('This is a debug message from demo-logging.py')
    loguru.logger.info('This is an info message from demo-logging.py')
    loguru.logger.warning('This is a warning message from demo-logging.py')
    loguru.logger.error('This is an error message from demo-logging.py')
    loguru.logger.critical('This is a critical message from demo-logging.py')
    print('This is a print message from demo-logging.py')
    print('This is a print message to stderr from demo-logging.py', file=sys.stderr)
    warnings.warn('This is a warnings.warn message from demo-logging.py', DeprecationWarning, stacklevel=1)
    warnings.showwarning('This is a warnings.showwarning message from demo-logging.py', DeprecationWarning, __file__, 32)

    try:
        loguru.logger.info('Raising an exception in demo-logging.py')
        raise ValueError('This is a test exception from demo-logging.py')
    except ValueError as e:
        loguru.logger.exception(f'Caught an exception in demo-logging.py: {e}')


def emit_all():
    log_messages()
    tests.emitters.wanted.func()
    tests.emitters.unwanted.func()
    tests.emitters.some_lib.func()


def subprocess_entrypoint():
    logit.base.setup_logger(disabled=DISABLED, subprocess=True)
    stdout_stream = logit.base.StreamToLogger(level='INFO')
    stderr_stream = logit.base.StreamToLogger(level='ERROR')
    with contextlib.redirect_stdout(stdout_stream), contextlib.redirect_stderr(stderr_stream):
        emit_all()
    loguru.logger.complete()


def demo_joblib():
    loguru.logger.info('Testing subprocesses...')
    joblib.Parallel(n_jobs=2)(joblib.delayed(subprocess_entrypoint)() for _ in range(2))


def demo_multiprocessing():
    loguru.logger.info('Testing multiprocessing subprocesses...')
    processes = []
    for _ in range(2):
        p = multiprocessing.Process(target=subprocess_entrypoint)
        p.start()
        processes.append(p)
    for p in processes:
        p.join()


def demo_threads():
    loguru.logger.info('Testing threads...')
    threads = []
    for _ in range(2):
        t = threading.Thread(target=emit_all)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()


def main():
    logit.base.setup_logger(disabled=DISABLED)
    stdout_stream = logit.base.StreamToLogger(level='INFO')
    stderr_stream = logit.base.StreamToLogger(level='ERROR')
    with contextlib.redirect_stdout(stdout_stream), contextlib.redirect_stderr(stderr_stream):
        emit_all()
        demo_joblib()
        demo_multiprocessing()
        demo_threads()
    loguru.logger.complete()


if __name__ == '__main__':
    main()
