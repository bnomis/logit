# logit

A loguru wrapper.

## Install

```shell
uv add logit
```

The dev group (`uv sync`) pulls in `joblib`, needed to run `bin/demo-logging.sh`,
plus `pytest` and `hypothesis` for the test suite.

## Usage

```python
import logit

logit.setup_logger(
    directory=None,       # defaults to <package>/../../log
    stderr=None,          # defaults to sys.__stderr__
    disabled=[],          # dotted module names to silence
    subprocess=False,     # per-pid file names instead of shared ones
)
```

`setup_logger` intercepts stdlib `logging`, Python `warnings`, and installs
three loguru sinks:

- stderr - human-readable, colour output, tagged with process and thread id
- `log.log` (in `directory`, or `log-<pid>.log` when `subprocess=True`) -
  the same record format as stderr, without colour
- `log.jsonl` (or `log-<pid>.jsonl` when `subprocess=True`) - one JSON object
  per record, including the origin module, source location, level, and
  process/thread identity

`subprocess=True` gives each process its own pair of log files instead of
every process writing to the same `log.log` / `log.jsonl`. Use it when
`setup_logger` runs inside a forked worker (e.g. `multiprocessing`, `joblib`)
so concurrent writers do not interleave into one file.

`disabled` takes a list of dotted module names (e.g. `['some.noisy.module']`)
and silences them across every capture path: stdlib `logging`, loguru calls,
`print()` via `StreamToLogger`, and `warnings.warn`. Any module not named
keeps logging normally. Calling `setup_logger` again with a different
`disabled` list re-enables the modules from the previous call before applying
the new one.

`logit.StreamToLogger` is a file-like object for redirecting `print()` output
through loguru, typically via `contextlib.redirect_stdout`/`redirect_stderr`:

```python
with contextlib.redirect_stdout(logit.StreamToLogger(level='INFO')):
    print('captured as an INFO log record')
```

`logit.showwarning` is the `warnings.showwarning` replacement `setup_logger`
installs; it is exported for direct use in tests or other warning setups.

`logit.log_file` and `logit.jsonl_file` return the paths `setup_logger` will
write to for a given `directory`/`subprocess` combination, without requiring
a running logger - useful for locating the sinks from a test or another
process.

Call `logit.reset()` to undo `setup_logger`: it removes all sinks and
restores the stdlib `logging`, loguru, and `warnings` state it changed.

## Demo

```shell
bin/demo-logging.sh
```

Runs a visual, end-to-end walk through every capture path (stdlib logging,
loguru calls, `print()`, warnings, threads, `multiprocessing`, `joblib`),
writing to `log/` in the repo. Requires the dev dependency group installed,
since it imports `joblib`.
