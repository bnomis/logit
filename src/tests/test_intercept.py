import inspect
import logging  # auditme: accept[stdlib-logging] drives stdlib logging into the interceptor
import typing

import pytest

import tests.emitters.wanted

if typing.TYPE_CHECKING:
    import tests.fixtures.base

LEVELS = [
    ('debug', 'DEBUG'),
    ('info', 'INFO'),
    ('warning', 'WARNING'),
    ('error', 'ERROR'),
    ('critical', 'CRITICAL'),
]


@pytest.mark.parametrize(('method', 'level'), LEVELS)
def test_stdlib_level_maps_to_loguru_level(capture: tests.fixtures.base.LogCapture, method: str, level: str) -> None:
    logger = logging.getLogger('tests.emitters.wanted')
    getattr(logger, method)(f'stdlib {method}')

    assert capture.find(f'stdlib {method}')['level']['name'] == level


def test_record_is_attributed_to_the_emitting_module(capture: tests.fixtures.base.LogCapture) -> None:
    tests.emitters.wanted.func()

    record = capture.find('This is an info message from wanted.py')
    assert record['name'] == 'tests.emitters.wanted'
    assert record['module'] == 'wanted'


def test_source_location_is_the_caller_not_the_interceptor(capture: tests.fixtures.base.LogCapture) -> None:
    """The frame-depth walk in InterceptHandler.emit is what this protects."""
    logger = logging.getLogger('tests.emitters.wanted')
    expected_line = inspect.currentframe().f_lineno + 1
    logger.info('locate me')

    record = capture.find('locate me')
    assert record['file']['name'] == 'test_intercept.py'
    assert record['function'] == 'test_source_location_is_the_caller_not_the_interceptor'
    assert record['line'] == expected_line
    assert 'logging/__init__.py' not in record['file']['path']


def test_location_points_into_the_emitting_module(capture: tests.fixtures.base.LogCapture) -> None:
    tests.emitters.wanted.func()

    record = capture.find('This is a debug message from wanted.py')
    assert record['file']['name'] == 'wanted.py'
    assert record['function'] == 'func'


def test_exception_info_is_carried_through(capture: tests.fixtures.base.LogCapture) -> None:
    logger = logging.getLogger('tests.emitters.wanted')
    try:
        raise ValueError('boom')
    except ValueError:
        logger.exception('caught it')

    record = capture.find('caught it')
    assert record['level']['name'] == 'ERROR'
    assert record['exception'] is not None
    assert 'ValueError' in capture.text()
    assert 'boom' in capture.text()


def test_unknown_level_falls_back_to_the_numeric_level(capture: tests.fixtures.base.LogCapture) -> None:
    """logger.level() raises for unregistered names, so emit() uses levelno."""
    logging.addLevelName(25, 'NOTICE')
    logger = logging.getLogger('tests.emitters.wanted')
    logger.log(25, 'custom level')

    record = capture.find('custom level')
    assert record['level']['no'] == 25


def test_root_logger_is_intercepted(capture: tests.fixtures.base.LogCapture) -> None:
    logging.getLogger('some.third.party').info('from a library')

    record = capture.find('from a library')
    assert record['level']['name'] == 'INFO'


def test_stdlib_formatting_args_are_resolved(capture: tests.fixtures.base.LogCapture) -> None:
    logging.getLogger('tests.emitters.wanted').info('value is %s and %d', 'x', 7)

    assert capture.find('value is x and 7')
