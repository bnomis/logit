# logit

A loguru wrapper.

## Project Overview

This is a project exploring loguru for logging in Python. The project demonstrates how to:

- Intercept standard library `logging` calls and route them through loguru
- Capture `print()` statements and Python warnings as log messages
- Selectively enable/disable logging from specific modules
- Configure multiple log outputs (stderr, file, and JSONL)

## Code Architecture

### Logging System Design

The core logging architecture is in [src/logit/base.py](src/logit/base.py):

1. **InterceptHandler**: Custom `logging.Handler` that intercepts all standard library logging calls and redirects them to loguru with proper stack depth tracking for accurate file/line numbers.

2. **Selective Module Logging**: `setup_logger(disabled=[...])` takes a list of dotted module names to silence. Each name is applied through three mechanisms, because each covers a different capture path:
   - `NullHandler` in the stdlib logging config (stdlib `logging` calls)
   - `logger.disable()` (loguru calls, and `print()` via `StreamToLogger`)
   - `warnings.filterwarnings(module=...)` (Python warnings)

   Any module not in the list logs normally.

3. **Warnings Integration**: Custom `warnings.showwarning` override that routes Python warnings through loguru while maintaining proper source location tracking using frame inspection.

4. **StreamToLogger**: Utility class that allows redirecting stdout/stderr to loguru using `contextlib.redirect_stdout/redirect_stderr`.

5. **Multi-Output Configuration**:
   - stderr: Human-readable coloured output
   - `log/log.log`: Plain text log file
   - `log/log.jsonl`: JSON Lines format for structured logging

### Module Structure

- [src/logit/**init**.py](src/logit/__init__.py): public API re-exports (`__all__`)
- [src/logit/base.py](src/logit/base.py): Core logging setup and configuration
- [bin/demo-logging.py](bin/demo-logging.py): visual demo of every capture path, run via [bin/demo-logging.sh](bin/demo-logging.sh)
- [src/tests/conftest.py](src/tests/conftest.py): `capture` and `setup` fixtures shared across the test suite
- [src/tests/emitters/](src/tests/emitters): modules that emit on every capture path, used as test subjects
- [src/tests/fixtures/base.py](src/tests/fixtures/base.py): `LogCapture`, which reads the sinks back for assertions

### Tests

Tests assert *where* each message lands. The jsonl sink is the oracle: it
serialises the origin module (`record.name`), source location
(`file`/`line`/`function`), level and process/thread identity, so routing,
level mapping and frame-depth correctness can all be checked from it.

The `capture` fixture configures logit into a `tmp_path` and hands back a
`LogCapture`. Use `setup` instead when a test needs to choose `disabled` or
`subprocess`. Both restore the global loguru/logging/warnings state on teardown.

| File | Covers |
| --- | --- |
| `test_sinks.py` | one record reaching stderr, `log.log` and `log.jsonl` consistently |
| `test_intercept.py` | stdlib `logging` -> loguru: level mapping, attribution, `exc_info` |
| `test_streams.py` | `print()` / stdout / stderr via `StreamToLogger` |
| `test_warnings.py` | `warnings.warn` and direct `showwarning` calls |
| `test_selective.py` | enabled vs disabled module routing across all five paths |
| `test_concurrency.py` | threads, `multiprocessing`, joblib, per-pid files (`slow`) |

```shell
source bin/activate.sh
pytest -m "not slow"    # fast suite
pytest -m slow          # forking tests
```

## Tools and Libraries

- [loguru](https://loguru.readthedocs.io/en/stable/): the logging library this project wraps
- [joblib](https://joblib.readthedocs.io/en/stable/): dev dependency, used by `bin/demo-logging.py` and `src/tests/test_concurrency.py` to demonstrate/exercise per-process logging
- [pytest](https://docs.pytest.org/en/stable/): test runner
- [uv](https://docs.astral.sh/uv/): package and virtual environment management

## Key Implementation Details

### Stack Depth Tracking

When intercepting logging calls from stdlib or warnings, the code uses frame inspection to determine the correct `depth` parameter for `logger.opt(depth=N)`. This ensures loguru reports the original caller's file/line number, not the interceptor's location.

### Warnings Filtering

Two mechanisms work together to suppress unwanted warnings:

1. `warnings.filterwarnings('ignore', module=...)` - stdlib filtering. CPython
   matches this regex, anchored at the start, against the emitting module's
   dotted `__name__`, so the name is `re.escape`d before use.
2. `logger.disable(...)` - loguru-specific disabling.

Note that attribution follows the *call frame*, not the `filename` argument: a
warning raised from inside a disabled module is suppressed, but a warning
*about* that module raised from elsewhere is not.
