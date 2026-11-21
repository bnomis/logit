import logging
import sys
import warnings

logger = logging.getLogger(__name__)


def func() -> None:
    logger.debug('This is a debug message from some_lib.py')
    logger.info('This is an info message from some_lib.py')
    logger.warning('This is a warning message from some_lib.py')
    logger.error('This is an error message from some_lib.py')
    logger.critical('This is a critical message from some_lib.py')
    print('This is a print message from some_lib.py')
    print('This is a print message to stderr from some_lib.py', file=sys.stderr)
    warnings.warn('This is a warnings.warn message from some_lib.py', DeprecationWarning, stacklevel=0)
    warnings.showwarning('This is a warnings.showwarning message from some_lib.py', DeprecationWarning, 'some_lib.py', 19)

    try:
        logger.info('Rasising an exception in some_lib.py')
        raise ValueError('This is a test exception from some_lib.py')
    except ValueError:
        logger.exception('Caught an exception in some_lib.py')
