import inspect
import logging
import logging.config
import os
import pathlib
import sys
import warnings

from loguru import logger

showwarning_ = warnings.showwarning


def showwarning_orig(message, *args, **kwargs):
    # Find caller from where originated the logged message.
    frame, depth = inspect.currentframe(), 0
    while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
        frame = frame.f_back
        depth += 1

    logger.opt(depth=depth).warning(message)
    # logger.warning(message)
    showwarning_(message, *args, **kwargs)


def showwarning(message, category, filename, lineno, file=None, line=None):
    # Find caller from where originated the logged message.
    frame, depth = inspect.currentframe(), 0
    while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
        frame = frame.f_back
        depth += 1

    msg = f'{category.__name__}: {message}'
    # from stdlib warnings.py
    if line is None and filename != 'sys':
        try:
            import linecache

            line = linecache.getline(filename, lineno)
        except Exception:
            line = None
            linecache = None
    else:
        line = line

    if line:
        line = line.strip()
        depth += 1

    logger.opt(depth=depth).warning(msg)
    if line:
        logger.opt(depth=depth).warning(f'  {line}')
    # logger.warning(message)
    # showwarning_(message, category, filename, lineno, file=file, line=line)


class LoguruHandler(logging.Handler):
    def emit(self, record):
        logger.log(record.levelname, self.format(record))


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def config_logger_default() -> None:
    default_handlers = [
        'loguru',
    ]
    null_handlers = ['null']
    fmt = '%(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'datefmt': datefmt,
                'format': fmt,
            },
            'progress': {
                'format': '%(message)s',
            },
        },
        'handlers': {
            'loguru': {
                'class': InterceptHandler,
                'formatter': 'default',
                'level': 'DEBUG',
            },
            'null': {
                'class': 'logging.NullHandler',
            },
        },
        'root': {
            'handlers': default_handlers,
            'level': 'DEBUG',
        },
        'loggers': {
            'logit.wanted': {
                'handlers': default_handlers,
                'level': 'DEBUG',
                'propagate': False,
            },
            'logit.unwanted': {
                'handlers': null_handlers,
                'level': 'DEBUG',
                'propagate': False,
            },
        },
    }

    logging.config.dictConfig(config)


class StreamToLogger:
    def __init__(self, level='DEBUG'):
        self._level = level

    def write(self, buffer):
        for line in buffer.rstrip().splitlines():
            logger.opt(depth=1).log(self._level, line.rstrip())

    def flush(self):
        pass


def take_over_logging():
    config_logger_default()


def setup_warnings():
    logging.captureWarnings(True)
    warnings.resetwarnings()
    warnings.showwarning = showwarning
    warnings.filterwarnings('ignore', module='logit.unwanted')


def this_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent.absolute()


def log_dir() -> pathlib.Path:
    return this_dir().parent.parent / 'log'


def log_file(subprocess: bool = False) -> pathlib.Path:
    if subprocess:
        return log_dir() / f'log-{os.getpid()}.log'
    return log_dir() / 'log.log'


def jsonl_file(subprocess: bool = False) -> pathlib.Path:
    if subprocess:
        return log_dir() / f'log-{os.getpid()}.jsonl'
    return log_dir() / 'log.jsonl'


def setup_logger(subprocess: bool = False):
    # remove all handlers
    logger.remove()

    take_over_logging()
    setup_warnings()

    # dont need to take over stdout
    # logger.add(sys.__stdout__)
    # terminal/stderr
    logger.add(  # pyright: ignore[reportCallIssue]
        sys.__stderr__,
        format='{time:YYYY-MM-DDTHH:mm:ss!UTC} <level>{level: <8}</level> {process.id} {file}:{line}/{function} {message}',
        enqueue=True,
    )
    # log to file
    logger.add(
        log_file(subprocess=subprocess),
        format='{time:YYYY-MM-DDTHH:mm:ss!UTC} {level: <8} {file}:{line}/{function} {message}',
        enqueue=True,
    )
    # log to jsonl
    logger.add(
        jsonl_file(subprocess=subprocess),
        format='{time:YYYY-MM-DDTHH:mm:ss!UTC} {level: <8} {file}:{line}/{function} {message}',
        serialize=True,
        enqueue=True,
    )
    # disable print messages from unwanted.py
    logger.disable('logit.unwanted')
