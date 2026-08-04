import io
import os
import typing

import loguru
import pytest

import logit

if typing.TYPE_CHECKING:
    import pathlib

    import tests.fixtures.base


def test_record_reaches_all_three_sinks(capture: tests.fixtures.base.LogCapture) -> None:
    loguru.logger.info('to every sink')

    assert 'to every sink' in capture.messages()
    assert 'to every sink' in capture.text()
    assert 'to every sink' in capture.stderr()


def test_sinks_agree_on_level_and_location(capture: tests.fixtures.base.LogCapture) -> None:
    loguru.logger.warning('agreeing sinks')
    record = capture.find('agreeing sinks')

    assert record['level']['name'] == 'WARNING'
    assert record['file']['name'] == 'test_sinks.py'
    assert record['function'] == 'test_sinks_agree_on_level_and_location'

    location = f'{record["file"]["name"]}:{record["line"]}/{record["function"]}'
    assert location in capture.text()
    assert location in capture.stderr()
    assert 'WARNING' in capture.text()


def test_each_level_serialises_with_name_and_number(capture: tests.fixtures.base.LogCapture) -> None:
    levels = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40, 'CRITICAL': 50}
    for name in levels:
        loguru.logger.log(name, f'level {name}')

    for name, number in levels.items():
        record = capture.find(f'level {name}')
        assert record['level']['name'] == name
        assert record['level']['no'] == number


def test_text_sink_has_one_line_per_record(capture: tests.fixtures.base.LogCapture) -> None:
    for index in range(5):
        loguru.logger.info(f'line {index}')

    assert len(capture.records()) == 5
    assert len([line for line in capture.text().splitlines() if line.strip()]) == 5


def test_subprocess_mode_uses_per_pid_filenames(setup: typing.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    capture = setup(subprocess=True)
    loguru.logger.info('from a child')

    assert capture.messages() == ['from a child']

    log = logit.log_file(directory=capture.directory, subprocess=True)
    jsonl = logit.jsonl_file(directory=capture.directory, subprocess=True)
    assert log.name == f'log-{os.getpid()}.log'
    assert jsonl.name == f'log-{os.getpid()}.jsonl'
    assert log.exists() and jsonl.exists()
    assert not (capture.directory / 'log.log').exists()


def test_default_mode_uses_shared_filenames(capture: tests.fixtures.base.LogCapture) -> None:
    loguru.logger.info('from the parent')

    assert (capture.directory / 'log.log').exists()
    assert (capture.directory / 'log.jsonl').exists()


def test_failed_sink_registration_leaves_no_sinks_registered(tmp_path: pathlib.Path) -> None:
    """A mid-sequence OSError must roll back the stderr sink registered before it."""
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        pytest.skip('running as root, permissions are not enforced')

    unwritable = tmp_path / 'unwritable'
    unwritable.mkdir()
    unwritable.chmod(0o500)
    stderr = io.StringIO()

    try:
        with pytest.raises(OSError):
            logit.setup_logger(directory=unwritable, stderr=stderr)
        loguru.logger.info('should reach no sink')
        loguru.logger.complete()
        assert stderr.getvalue() == ''
    finally:
        unwritable.chmod(0o700)
        logit.reset()
