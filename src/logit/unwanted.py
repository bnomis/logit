import logging
import sys
import warnings

logger = logging.getLogger(__name__)


def func():
    logger.debug('This is a debug message from unwanted.py')
    logger.info('This is an info message from unwanted.py')
    logger.warning('This is a warning message from unwanted.py')
    logger.error('This is an error message from unwanted.py')
    logger.critical('This is a critical message from unwanted.py')
    print('This is a print message from unwanted.py')
    print('This is a print message to stderr from unwanted.py', file=sys.stderr)
    warnings.warn('This is a warnings.warn message from unwanted.py', DeprecationWarning, stacklevel=0)
    warnings.showwarning('This is a warnings.showwarning message from unwanted.py', DeprecationWarning, 'unwanted.py', 19)
