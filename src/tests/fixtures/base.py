import contextlib
import io
import json
import logging
import sys
import typing

import loguru
import pytest

import logit
import logit.base

if typing.TYPE_CHECKING:
    import collections.abc
    import pathlib


class LogCapture:
    """Reads back what logit actually wrote, so tests can assert on routing.

    The jsonl sink is the oracle: it serialises the origin module, source
    location, level and process/thread identity for every record.
    """

    def __init__(self, directory: pathlib.Path, stderr: io.StringIO, subprocess: bool = False) -> None:
        self.directory = directory
        self.stderr_stream = stderr
        self.subprocess = subprocess
        self.records_cache: list[dict[str, typing.Any]] = []
        self.records_cache_stat: tuple[int, int] | None = None

    def jsonl_path(self) -> pathlib.Path:
        return logit.jsonl_file(directory=self.directory, subprocess=self.subprocess)

    def complete(self) -> None:
        # every sink uses enqueue=True and writes from a background thread
        loguru.logger.complete()

    def records(self) -> list[dict[str, typing.Any]]:
        self.complete()
        path = self.jsonl_path()
        if not path.exists():
            self.records_cache = []
            self.records_cache_stat = None
            return self.records_cache

        stat = path.stat()
        cache_stat = (stat.st_mtime_ns, stat.st_size)
        if cache_stat != self.records_cache_stat:
            self.records_cache = [json.loads(line)['record'] for line in path.read_text().splitlines() if line.strip()]
            self.records_cache_stat = cache_stat
        return self.records_cache

    def messages(self) -> list[str]:
        return [r['message'] for r in self.records()]

    def names(self) -> set[str]:
        return {r['name'] for r in self.records()}

    def find(self, message: str) -> dict[str, typing.Any]:
        records = self.records()
        matches = [r for r in records if r['message'] == message]
        if len(matches) != 1:
            messages = [r['message'] for r in records]
            raise AssertionError(f'expected exactly 1 record with message {message!r}, got {len(matches)}: {messages}')
        return matches[0]

    def matching(self, substring: str) -> list[dict[str, typing.Any]]:
        return [r for r in self.records() if substring in r['message']]

    def from_module(self, name: str) -> list[dict[str, typing.Any]]:
        return [r for r in self.records() if r['name'] == name]

    def text(self) -> str:
        self.complete()
        path = logit.log_file(directory=self.directory, subprocess=self.subprocess)
        return path.read_text() if path.exists() else ''

    def jsonl_text(self) -> str:
        """Raw jsonl sink contents, for asserting on what was serialised."""
        self.complete()
        path = self.jsonl_path()
        return path.read_text() if path.exists() else ''

    def stderr(self) -> str:
        self.complete()
        return self.stderr_stream.getvalue()

    @contextlib.contextmanager
    def redirect(self) -> collections.abc.Generator[None]:
        """Route print()/stdout/stderr through StreamToLogger, as the app does."""
        out = logit.StreamToLogger(level='INFO')
        err = logit.StreamToLogger(level='ERROR')
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):  # type: ignore
            yield


@pytest.fixture
def capture(tmp_path: pathlib.Path) -> collections.abc.Generator[LogCapture]:
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
    level: str = logit.base.DEFAULT_LEVEL,
    stderr_level: str | None = None,
    diagnose: bool = False,
    rotation: logit.base.RotationSpec = None,
    retention: logit.base.RetentionSpec = None,
) -> LogCapture:
    logit.setup_logger(
        directory=directory,
        stderr=stderr,
        disabled=disabled,
        subprocess=subprocess,
        level=level,
        stderr_level=stderr_level,
        diagnose=diagnose,
        rotation=rotation,
        retention=retention,
    )
    return LogCapture(directory, stderr, subprocess=subprocess)


@pytest.fixture
def setup(tmp_path: pathlib.Path) -> collections.abc.Generator[collections.abc.Callable[..., LogCapture]]:
    """Like `capture`, but lets a test choose `disabled` / `subprocess` itself."""
    stdout_, stderr_ = sys.stdout, sys.stderr
    handlers_ = logging.root.handlers[:]

    def build(
        disabled: list[str] | None = None,
        subprocess: bool = False,
        level: str = logit.base.DEFAULT_LEVEL,
        stderr_level: str | None = None,
        diagnose: bool = False,
        rotation: logit.base.RotationSpec = None,
        retention: logit.base.RetentionSpec = None,
    ) -> LogCapture:
        return make_capture(
            tmp_path,
            io.StringIO(),
            disabled=disabled,
            subprocess=subprocess,
            level=level,
            stderr_level=stderr_level,
            diagnose=diagnose,
            rotation=rotation,
            retention=retention,
        )

    yield build
    logit.reset()
    sys.stdout, sys.stderr = stdout_, stderr_
    logging.root.handlers[:] = handlers_
