import typing

import loguru

if typing.TYPE_CHECKING:
    import pathlib

    import tests.fixtures.base

# Each record carries a timestamp, level, location and the message itself, so
# a few hundred of these comfortably clears a 1 KB sink without the test
# having to write a large payload.
FILLER = 'x' * 200


def log_until_rotated(count: int = 40) -> None:
    for i in range(count):
        loguru.logger.info(f'{i} {FILLER}')
    loguru.logger.complete()


def rolled(directory: pathlib.Path, suffix: str) -> list[pathlib.Path]:
    """Every file the sink owns: the live one plus any loguru rolled aside."""
    return sorted(p for p in directory.iterdir() if p.suffix == suffix or f'{suffix}.' in p.name)


def test_no_rotation_by_default_leaves_one_file_per_sink(capture: tests.fixtures.base.LogCapture) -> None:
    log_until_rotated()

    assert len(rolled(capture.directory, '.log')) == 1
    assert len(rolled(capture.directory, '.jsonl')) == 1


def test_rotation_rolls_both_file_sinks(setup: typing.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    capture = setup(rotation='1 KB')

    log_until_rotated()

    # The terminal sink has no file to roll, so only these two are affected.
    assert len(rolled(capture.directory, '.log')) > 1
    assert len(rolled(capture.directory, '.jsonl')) > 1


def test_retention_expires_rolled_files(setup: typing.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    capture = setup(rotation='1 KB', retention=1)

    log_until_rotated()

    # retention=1 keeps one rolled file per sink, alongside the live one.
    assert len(rolled(capture.directory, '.log')) <= 2
    assert len(rolled(capture.directory, '.jsonl')) <= 2


def test_rotation_does_not_lose_records(setup: typing.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    """A rolled sink is still an audit trail: the records are on disk, not dropped."""
    capture = setup(rotation='1 KB')

    log_until_rotated()

    written = ''.join(p.read_text() for p in rolled(capture.directory, '.log'))
    for i in range(40):
        assert f'{i} {FILLER}' in written
