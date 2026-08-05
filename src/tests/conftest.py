import io
import logging
import sys
import typing

import pytest

import logit
import tests.fixtures.base

if typing.TYPE_CHECKING:
    import pathlib


@pytest.fixture
def capture(tmp_path: pathlib.Path) -> typing.Generator[tests.fixtures.base.LogCapture]:
    """Configure logit into a temp dir and hand back a reader for its sinks.

    loguru, stdlib logging and warnings are all process-global, so teardown has
    to be thorough or state leaks between tests.
    """
    stdout_, stderr_ = sys.stdout, sys.stderr
    handlers_ = logging.root.handlers[:]
    yield make_capture(tmp_path, io.StringIO())
    logit.reset()
    sys.stdout, sys.stderr = stdout_, stderr_
    logging.root.handlers[:] = handlers_


def make_capture(
    directory: pathlib.Path,
    stderr: io.StringIO,
    disabled: list[str] | None = None,
    subprocess: bool = False,
) -> tests.fixtures.base.LogCapture:
    logit.setup_logger(directory=directory, stderr=stderr, disabled=disabled, subprocess=subprocess)
    return tests.fixtures.base.LogCapture(directory, stderr, subprocess=subprocess)


@pytest.fixture
def setup(tmp_path: pathlib.Path) -> typing.Generator[typing.Callable[..., tests.fixtures.base.LogCapture]]:
    """Like `capture`, but lets a test choose `disabled` / `subprocess` itself."""
    stdout_, stderr_ = sys.stdout, sys.stderr
    handlers_ = logging.root.handlers[:]

    def build(disabled: list[str] | None = None, subprocess: bool = False) -> tests.fixtures.base.LogCapture:
        return make_capture(tmp_path, io.StringIO(), disabled=disabled, subprocess=subprocess)

    yield build
    logit.reset()
    sys.stdout, sys.stderr = stdout_, stderr_
    logging.root.handlers[:] = handlers_
