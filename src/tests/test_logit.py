#! /usr/bin/env python
import contextlib
import multiprocessing
import sys
import threading
import warnings

import joblib
import loguru

import logit.base
import tests.src.some_lib
import tests.src.unwanted
import tests.src.wanted


def test_log_messages():
    loguru.logger.debug('This is a debug message from main.py')
    loguru.logger.info('This is an info message from main.py')
    loguru.logger.warning('This is a warning message from main.py')
    loguru.logger.error('This is an error message from main.py')
    loguru.logger.critical('This is a critical message from main.py')
    print('This is a print message from main.py')
    print('This is a print message to stderr from main.py', file=sys.stderr)
    warnings.warn('This is a warnings.warn message from main.py', DeprecationWarning, stacklevel=0)
    warnings.showwarning('This is a warnings.showwarning message from main.py', DeprecationWarning, 'main.py', 24)

    try:
        loguru.logger.info('Rasising an exception in main.py')
        raise ValueError('This is a test exception from main.py')
    except ValueError as e:
        loguru.logger.exception(f'Caught an exception in main.py: {e}')


def subprocess_entrypoint():
    logit.base.setup_logger(subprocess=True)
    stdout_stream = logit.base.StreamToLogger(level='INFO')
    stderr_stream = logit.base.StreamToLogger(level='ERROR')
    with contextlib.redirect_stdout(stdout_stream), contextlib.redirect_stderr(stderr_stream):
        test_logs()
    loguru.logger.complete()


def test_joblib():
    loguru.logger.info('Testing subprocesses...')
    joblib.Parallel(n_jobs=2)(joblib.delayed(subprocess_entrypoint)() for _ in range(2))


def test_multiprocessing():
    loguru.logger.info('Testing multiprocessing subprocesses...')
    processes = []
    for _ in range(2):
        p = multiprocessing.Process(target=subprocess_entrypoint)
        p.start()
        processes.append(p)
    for p in processes:
        p.join()


def test_threads():
    loguru.logger.info('Testing threads...')
    threads = []
    for _ in range(2):
        t = threading.Thread(target=test_logs)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()


def test_logs():
    test_log_messages()
    tests.src.wanted.func()
    tests.src.unwanted.func()
    tests.src.some_lib.func()


def test_logger():
    stdout_stream = logit.base.StreamToLogger(level='INFO')
    stderr_stream = logit.base.StreamToLogger(level='ERROR')
    with contextlib.redirect_stdout(stdout_stream), contextlib.redirect_stderr(stderr_stream):
        test_logs()
        test_joblib()
        test_multiprocessing()
        test_threads()


def main():
    logit.base.setup_logger()
    test_logger()


if __name__ == '__main__':
    main()
