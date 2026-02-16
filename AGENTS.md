# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a test project exploring loguru for logging in Python. The project demonstrates how to:

- Intercept standard library `logging` calls and route them through loguru
- Capture `print()` statements and Python warnings as log messages
- Selectively enable/disable logging from specific modules
- Configure multiple log outputs (stderr, file, and JSONL)

## Development Commands

### Running the Application

```bash
python bin/main.py
```

### Linting and Formatting

```bash
# Run linter
ruff check .

# Run formatter
ruff format .

# Run pre-commit hooks
pre-commit run --all-files
```

### Type Checking

```bash
pyright
```

## Code Architecture

### Logging System Design

The core logging architecture is in [src/logit/log.py](src/logit/log.py):

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

- [bin/main.py](bin/main.py): Entry point demonstrating all logging features
- [src/logit/log.py](src/logit/log.py): Core logging setup and configuration
- [src/logit/wanted.py](src/logit/wanted.py): Example module with logging enabled
- [src/logit/unwanted.py](src/logit/unwanted.py): Example module with logging disabled

## Code Style Configuration

### Ruff Settings (from [pyproject.toml](pyproject.toml))

- Line length: 160 characters
- Quote style: Single quotes
- Enabled linters: flake8-bugbear, pycodestyle, Pyflakes, isort, flake8-simplify, NPY201
- Ignored rules: E501 (line length), E722 (bare except), SIM108 (ternary operator)
- Import sorting: `combine-as-imports = true`

### Pyright Configuration

Most type checking errors are disabled in this project (see [pyproject.toml](pyproject.toml:50-63)). This is a test project, not production code.

## Key Implementation Details

### Stack Depth Tracking

When intercepting logging calls from stdlib or warnings, the code uses frame inspection to determine the correct `depth` parameter for `logger.opt(depth=N)`. This ensures loguru reports the original caller's file/line number, not the interceptor's location.

### Warnings Filtering

Two mechanisms work together to suppress unwanted warnings:

1. `warnings.filterwarnings('ignore', module='logit.unwanted')` - stdlib filtering
2. `logger.disable('logit.unwanted')` - loguru-specific disabling
