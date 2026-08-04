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

2. **Selective Module Logging**: The logging configuration demonstrates two patterns:
   - `logit.wanted`: Logs are processed and output normally
   - `logit.unwanted`: Logs are suppressed via `NullHandler` in the logging config AND `logger.disable()` for loguru

3. **Warnings Integration**: Custom `warnings.showwarning` override that routes Python warnings through loguru while maintaining proper source location tracking using frame inspection.

4. **StreamToLogger**: Utility class that allows redirecting stdout/stderr to loguru using `contextlib.redirect_stdout/redirect_stderr`.

5. **Multi-Output Configuration**:
   - stderr: Human-readable colored output
   - `log/log.log`: Plain text log file
   - `log/log.jsonl`: JSON Lines format for structured logging

### Module Structure

- [src/logit/base.py](src/logit/base.py): Core logging setup and configuration
- [src/tests/test_logit.py](src/tests/test_logit.py): test entry point demonstrating all logging features
- [src/tests/src/wanted.py](src/tests/src/wanted.py): Example module with logging enabled
- [src/tests/src/unwanted.py](src/tests/src/unwanted.py): Example module with logging disabled

## Key Implementation Details

### Stack Depth Tracking

When intercepting logging calls from stdlib or warnings, the code uses frame inspection to determine the correct `depth` parameter for `logger.opt(depth=N)`. This ensures loguru reports the original caller's file/line number, not the interceptor's location.

### Warnings Filtering

Two mechanisms work together to suppress unwanted warnings:

1. `warnings.filterwarnings('ignore', module='logit.unwanted')` - stdlib filtering
2. `logger.disable('logit.unwanted')` - loguru-specific disabling
