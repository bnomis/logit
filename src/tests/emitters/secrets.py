"""Emitter whose traceback lines reference a value that must not be logged.

loguru's diagnose annotates the values of expressions appearing on traceback
lines, so the leak needs a real source file and a call that passes the secret.
"""

SECRET = 'SECRET-KEY-abc123'


def send(url: str, params: dict[str, str]) -> None:
    raise RuntimeError('upstream failed')


def call_api() -> None:
    params = {'apikey': SECRET, 'query': 'transformers'}
    send('https://example.invalid/api', params)
