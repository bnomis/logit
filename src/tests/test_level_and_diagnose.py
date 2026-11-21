import typing

import loguru
import pytest

import tests.emitters.secrets

if typing.TYPE_CHECKING:
    import collections.abc

    import tests.fixtures.base


ALL_MESSAGES = ['a debug', 'a warning', 'an info']


def log_the_failure() -> None:
    try:
        tests.emitters.secrets.call_api()
    except RuntimeError:
        loguru.logger.exception('search failed')


def test_diagnose_is_off_by_default(setup: collections.abc.Callable[..., tests.fixtures.base.LogCapture]) -> None:
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


def test_diagnose_still_reports_the_exception(setup: collections.abc.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    """Turning diagnose off keeps the traceback and the exception type."""
    capture = setup()
    log_the_failure()
    capture.complete()

    stderr = capture.stderr()
    assert 'Traceback' in stderr
    assert 'RuntimeError' in stderr
    assert 'call_api' in stderr


def test_diagnose_can_be_turned_on(setup: collections.abc.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    """The old behaviour is available for local debugging when asked for."""
    capture = setup(diagnose=True)
    log_the_failure()
    capture.complete()

    assert tests.emitters.secrets.SECRET in capture.stderr()


@pytest.mark.parametrize(
    ('level', 'emitted', 'dropped'),
    [
        ('DEBUG', ALL_MESSAGES, []),
        ('INFO', ['a warning', 'an info'], ['a debug']),
        ('WARNING', ['a warning'], ['a debug', 'an info']),
        ('ERROR', [], ALL_MESSAGES),
    ],
)
def test_level_filters_every_sink(
    setup: collections.abc.Callable[..., tests.fixtures.base.LogCapture],
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


def test_level_defaults_to_debug(setup: collections.abc.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    """Omitting level keeps the previous behaviour of emitting everything."""
    capture = setup()
    loguru.logger.debug('a debug')
    capture.complete()

    assert 'a debug' in capture.messages()


class TestStderrLevel:
    """The terminal can be quieter than the files."""

    def test_stderr_level_defaults_to_level(self, setup: collections.abc.Callable[..., tests.fixtures.base.LogCapture]) -> None:
        """Omitting stderr_level keeps every sink on the same level."""
        capture = setup(level='WARNING')
        loguru.logger.info('an info')
        loguru.logger.warning('a warning')
        capture.complete()

        assert 'an info' not in capture.stderr()
        assert 'an info' not in capture.text()
        assert 'a warning' in capture.stderr()

    def test_files_can_record_more_than_the_terminal(self, setup: collections.abc.Callable[..., tests.fixtures.base.LogCapture]) -> None:
        """A quieter terminal still leaves a complete audit trail on disk."""
        capture = setup(level='DEBUG', stderr_level='INFO')
        loguru.logger.debug('a debug')
        loguru.logger.info('an info')
        capture.complete()

        assert 'a debug' not in capture.stderr()
        assert 'a debug' in capture.text()
        assert 'a debug' in capture.messages()
        assert 'an info' in capture.stderr()

    def test_an_exception_reaches_the_files_only(self, setup: collections.abc.Callable[..., tests.fixtures.base.LogCapture]) -> None:
        """A traceback logged below the terminal level is still recorded.

        This is what lets a CLI show a one-line error while keeping the full
        cause in the audit trail.
        """
        capture = setup(level='DEBUG', stderr_level='INFO')
        try:
            raise ValueError('the underlying cause')
        except ValueError:
            loguru.logger.opt(exception=True).debug('command failed')
        capture.complete()

        assert 'command failed' not in capture.stderr()
        assert 'the underlying cause' not in capture.stderr()
        assert 'the underlying cause' in capture.text()
