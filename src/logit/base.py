import inspect
import logging
import logging.config
import os
import pathlib
import re
import sys
import typing
import warnings

from loguru import logger

showwarning_ = warnings.showwarning

# loguru's disable() is global and outlives logger.remove(), so track what we
# disabled in order to undo it in reset()
disabled_ = []

# dictConfig only touches loggers named in its 'loggers' key, so a logger
# disabled by an earlier config_logger_default() call stays disabled forever
# unless we explicitly restore it - track what we disabled to undo it
disabled_logging_ = []


# def showwarning_orig(message, *args, **kwargs):
#     # Find caller from where originated the logged message.
#     frame, depth = inspect.currentframe(), 0
#     while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
#         frame = frame.f_back
#         depth += 1

#     logger.opt(depth=depth).warning(message)
#     # logger.warning(message)
#     showwarning_(message, *args, **kwargs)


def internal_files() -> set[str]:
    """Files whose frames sit between the warning site and this hook.

    warnings.warn reaches showwarning via an internal _showwarnmsg frame, while
    a direct showwarning() call has none. Skipping these by filename keeps the
    reported location correct for both routes.
    """
    files = {logging.__file__, warnings.__file__}
    hook = getattr(warnings, '_showwarnmsg', None)
    if hook is not None:
        files.add(hook.__code__.co_filename)
    return files


def showwarning(message, category, filename, lineno, file=None, line=None):
    # Find caller from where originated the logged message.
    internal = internal_files()
    frame, depth = inspect.currentframe(), 0
    while frame and (depth == 0 or frame.f_code.co_filename in internal):
        frame = frame.f_back
        depth += 1

    msg = f'{category.__name__}: {message}'
    # from stdlib warnings.py
    if line is None and filename != 'sys':
        import linecache

        try:
            line = linecache.getline(filename, lineno)
        except OSError:
            logger.debug(f'could not read source line from {filename}')
            line = None

    if line:
        line = line.strip()

    logger.opt(depth=depth).warning(msg)
    if line:
        logger.opt(depth=depth).warning(f'  {line}')
    # logger.warning(message)
    # showwarning_(message, category, filename, lineno, file=file, line=line)


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


def reset_disabled_logging() -> None:
    """Undo the stdlib logging side of a previous `disabled` list.

    dictConfig only reconfigures loggers it is told about, so a logger
    disabled by a previous call is not restored just by leaving it out of the
    next one - it has to be reset directly.
    """
    while disabled_logging_:
        name = disabled_logging_.pop()
        log = logging.getLogger(name)
        log.handlers = []
        log.level = logging.NOTSET
        log.propagate = True


def config_logger_default(disabled: list[str] | None = None) -> None:
    reset_disabled_logging()
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
            name: {
                'handlers': null_handlers,
                'level': 'DEBUG',
                'propagate': False,
            }
            for name in disabled or []
        },
    }

    logging.config.dictConfig(config)
    disabled_logging_.extend(disabled or [])


class StreamToLogger:
    def __init__(self, level='DEBUG'):
        self.level = level

    def write(self, buffer):
        for line in buffer.rstrip().splitlines():
            logger.opt(depth=1).log(self.level, line.rstrip())

    def flush(self):
        pass


def take_over_logging(disabled: list[str] | None = None) -> None:
    config_logger_default(disabled=disabled)


def setup_warnings(disabled: list[str] | None = None) -> None:
    logging.captureWarnings(True)
    warnings.resetwarnings()
    warnings.showwarning = showwarning
    for name in disabled or []:
        # the filter's module is a regex matched against the emitting
        # module's dotted __name__, so the dots must not act as wildcards
        warnings.filterwarnings('ignore', module=re.escape(name))


def this_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent.absolute()


def log_dir() -> pathlib.Path:
    return this_dir().parent.parent / 'log'


def log_file(directory: pathlib.Path | None = None, subprocess: bool = False) -> pathlib.Path:
    directory = directory or log_dir()
    if subprocess:
        return directory / f'log-{os.getpid()}.log'
    return directory / 'log.log'


def jsonl_file(directory: pathlib.Path | None = None, subprocess: bool = False) -> pathlib.Path:
    directory = directory or log_dir()
    if subprocess:
        return directory / f'log-{os.getpid()}.jsonl'
    return directory / 'log.jsonl'


def re_enable_disabled() -> None:
    """Undo the loguru side of a previous `disabled` list."""
    while disabled_:
        logger.enable(disabled_.pop())


def reset() -> None:
    """Undo setup_logger: drop all sinks and restore the global state it mutated."""
    logger.remove()
    re_enable_disabled()
    reset_disabled_logging()
    warnings.showwarning = showwarning_
    warnings.resetwarnings()
    logging.captureWarnings(False)
    logging.config.dictConfig({'version': 1, 'disable_existing_loggers': False, 'root': {'handlers': []}})


def setup_logger(
    directory: pathlib.Path | None = None,
    stderr: typing.TextIO | None = None,
    disabled: list[str] | None = None,
    subprocess: bool = False,
) -> None:
    # remove all handlers
    logger.remove()
    re_enable_disabled()

    take_over_logging(disabled=disabled)
    setup_warnings(disabled=disabled)

    # dont need to take over stdout
    # logger.add(sys.__stdout__)
    # terminal/stderr
    logger.add(
        stderr if stderr is not None else sys.__stderr__,  # type: ignore
        format='{time:YYYY-MM-DDTHH:mm:ss!UTC} <level>{level: <8}</level> {process.id} {thread.id} {file}:{line}/{function} {message}',
        enqueue=True,
    )  # type: ignore
    # log to file
    logger.add(
        log_file(directory=directory, subprocess=subprocess),
        format='{time:YYYY-MM-DDTHH:mm:ss!UTC} {level: <8} {file}:{line}/{function} {message}',
        enqueue=True,
    )
    # log to jsonl
    logger.add(
        jsonl_file(directory=directory, subprocess=subprocess),
        format='{time:YYYY-MM-DDTHH:mm:ss!UTC} {level: <8} {file}:{line}/{function} {message}',
        serialize=True,
        enqueue=True,
    )
    # suppress loguru records (including print capture) from disabled modules
    for name in disabled or []:
        logger.disable(name)
        disabled_.append(name)
