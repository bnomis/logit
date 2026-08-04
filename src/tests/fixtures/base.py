import contextlib
import json
import typing

import loguru

import logit

if typing.TYPE_CHECKING:
    import io
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

    def complete(self) -> None:
        # every sink uses enqueue=True and writes from a background thread
        loguru.logger.complete()

    def records(self) -> list[dict]:
        self.complete()
        path = logit.jsonl_file(directory=self.directory, subprocess=self.subprocess)
        if not path.exists():
            return []
        return [json.loads(line)['record'] for line in path.read_text().splitlines() if line.strip()]

    def messages(self) -> list[str]:
        return [r['message'] for r in self.records()]

    def names(self) -> set[str]:
        return {r['name'] for r in self.records()}

    def find(self, message: str) -> dict:
        matches = [r for r in self.records() if r['message'] == message]
        if len(matches) != 1:
            raise AssertionError(f'expected exactly 1 record with message {message!r}, got {len(matches)}: {self.messages()}')
        return matches[0]

    def matching(self, substring: str) -> list[dict]:
        return [r for r in self.records() if substring in r['message']]

    def from_module(self, name: str) -> list[dict]:
        return [r for r in self.records() if r['name'] == name]

    def text(self) -> str:
        self.complete()
        path = logit.log_file(directory=self.directory, subprocess=self.subprocess)
        return path.read_text() if path.exists() else ''

    def stderr(self) -> str:
        self.complete()
        return self.stderr_stream.getvalue()

    @contextlib.contextmanager
    def redirect(self) -> typing.Generator[None]:
        """Route print()/stdout/stderr through StreamToLogger, as the app does."""
        out = logit.StreamToLogger(level='INFO')
        err = logit.StreamToLogger(level='ERROR')
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):  # type: ignore
            yield
