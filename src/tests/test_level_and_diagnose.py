import typing

import loguru
import pytest

import tests.emitters.secrets

if typing.TYPE_CHECKING:
    import tests.fixtures.base


def log_the_failure() -> None:
    try:
        tests.emitters.secrets.call_api()
    except RuntimeError as e:
        loguru.logger.exception(f'search failed: {e}')


def test_diagnose_is_off_by_default(setup: typing.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    """Frame values are not rendered, so a secret on a traceback line is not logged.

    loguru defaults diagnose to True, which annotates the value of every
    expression on a traceback line. Those values include request parameters
    carrying API keys, and the file sinks persist them.
    """
    capture = setup()
    log_the_failure()
    capture.complete()

    assert tests.emitters.secrets.SECRET not in capture.stderr()
    assert tests.emitters.secrets.SECRET not in capture.text()
    assert tests.emitters.secrets.SECRET not in capture.jsonl_text()


def test_diagnose_still_reports_the_exception(setup: typing.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    """Turning diagnose off keeps the traceback and the exception type."""
    capture = setup()
    log_the_failure()
    capture.complete()

    stderr = capture.stderr()
    assert 'Traceback' in stderr
    assert 'RuntimeError' in stderr
    assert 'call_api' in stderr


def test_diagnose_can_be_turned_on(setup: typing.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    """The old behaviour is available for local debugging when asked for."""
    capture = setup(diagnose=True)
    log_the_failure()
    capture.complete()

    assert tests.emitters.secrets.SECRET in capture.stderr()


@pytest.mark.parametrize(
    ('level', 'emitted', 'dropped'),
    [
        ('DEBUG', ['a debug', 'an info', 'a warning'], []),
        ('INFO', ['an info', 'a warning'], ['a debug']),
        ('WARNING', ['a warning'], ['a debug', 'an info']),
        ('ERROR', [], ['a debug', 'an info', 'a warning']),
    ],
)
def test_level_filters_every_sink(
    setup: typing.Callable[..., tests.fixtures.base.LogCapture],
    level: str,
    emitted: list[str],
    dropped: list[str],
) -> None:
    """The configured level applies to stderr, the log file and the jsonl file."""
    capture = setup(level=level)

    loguru.logger.debug('a debug')
    loguru.logger.info('an info')
    loguru.logger.warning('a warning')
    capture.complete()

    messages = capture.messages()
    text = capture.text()
    stderr = capture.stderr()

    for message in emitted:
        assert message in messages
        assert message in text
        assert message in stderr

    for message in dropped:
        assert message not in messages
        assert message not in text
        assert message not in stderr


def test_level_defaults_to_debug(setup: typing.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    """Omitting level keeps the previous behaviour of emitting everything."""
    capture = setup()
    loguru.logger.debug('a debug')
    capture.complete()

    assert 'a debug' in capture.messages()
