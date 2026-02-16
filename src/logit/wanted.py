import logging
import sys
import warnings

logger = logging.getLogger(__name__)


def func():
    logger.debug('This is a debug message from wanted.py')
    logger.info('This is an info message from wanted.py')
    logger.warning('This is a warning message from wanted.py')
    logger.error('This is an error message from wanted.py')
    logger.critical('This is a critical message from wanted.py')
    print('This is a print message from wanted.py')
    print('This is a print message to stderr from wanted.py', file=sys.stderr)
    warnings.warn('This is a warnings.warn message from wanted.py', DeprecationWarning, stacklevel=0)
    warnings.showwarning('This is a warnings.showwarning message from wanted.py', DeprecationWarning, 'wanted.py', 19)
