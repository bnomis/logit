# Audit Review 2

**Date:** 2026-11-21
**Scope:** full (`src/logit/`, `src/tests/`, `bin/`, `AGENTS.md`, `README.md`, `pyproject.toml`, `.pre-commit-config.yaml`)
**Commit:** 3bbef7db9a1edf66b7d502ee83eb6f05fc1891d3
**Script output:** /tmp/audit-logit.jsonl (47 hits, 1 accepted, 46 unaccepted)
**Convergence note:** script extended since review-1. The sweep now audits every package under `src/` and the `bin/` extra root (review-1 read `src/logit/` only), and adds `typing-deprecated-alias`, `ruff-version-drift`, `translator-envelope-gap` and others; expect mechanical delta, nearly all of it in `src/tests/`. Newly listed Phase B questions, judged for the first time and so catch-up, not regressions: A1, A11, A17, A19, T1, T2, Doc1, Doc2, Doc4, Doc5 (and A4). No check was added and no predicate changed during this audit. Checker digest: `e924b332c5c6809821c1635aa7a1d3714064120de0317c733f7f09dfa6b50537`.
**Review page:** https://claude.ai/artifact/CmCwqoxBtbfiXv1idhtW9f

## What is being reviewed and how

Every finding from review-1 has been fixed (the tasks-1 list is fully ticked and each fix is confirmed in the source below). This review covers what the wider sweep and the newly listed questions now see. The user answers each item on the review page: approve the recommended action, or flag it with a comment, and pick an option for each decision. The approved items become the task list for tasks-2.

## Summary

The sweep returned 46 unaccepted hits: 29 `typing-deprecated-alias` (nearly all `typing.Callable`/`typing.Generator` in test signatures), 5 `stdlib-logging` and 5 `except-interpolation` (test emitters and the demo), and one or two each of `literal-duplication`, `bare-parametric-annotation`, `mutable-module-level-exported`, `ruff-version-drift` and `duplicate-side-effect-per-target`. Phase B produced 22 hit rows, consolidated into 15 findings; none is high severity. Nine of the hit rows (A17, A19, T1) are code doing exactly what it exists to do, and are recommended for dismissal.

## Automatic checks

- `requests.md` `## Open` empty at audit start: pass
- `checks/audit.py` run, full JSONL saved: pass (exit 0)
- `phaseb.py check` on every listed batch: pass (A17, A19, T1, Doc1, Doc2, Doc5 - all batches complete)
- Listed questions with no candidates: A1, A4, A11, T2, Doc4 (no `agents/specs/`)

## Mechanical findings (from checks/audit.py)

### Rule: typing-deprecated-alias - `typing.Callable`/`typing.Generator` -> `collections.abc`

- **Severity:** low
- **Instance count:** 29
- **Locations:**
  - `src/logit/base.py:24` - `type RotationSpec = ... typing.Callable[..., typing.Any] | None`
  - `src/logit/base.py:25` - `type RetentionSpec = ... typing.Callable[..., typing.Any] | None`
  - `src/tests/conftest.py:17` - `-> typing.Generator[tests.fixtures.base.LogCapture]`
  - `src/tests/conftest.py:57` - `typing.Generator[...]` (Generator)
  - `src/tests/conftest.py:57` - `typing.Callable[...]` (Callable)
  - `src/tests/fixtures/base.py:83` - `def redirect(self) -> typing.Generator[None]:`
  - `src/tests/test_level_and_diagnose.py:19`, `:35`, `:47`, `:66`, `:94`, `:106`, `:117`, `:129` - `setup: typing.Callable[..., tests.fixtures.base.LogCapture]`
  - `src/tests/test_rotation.py:34`, `:44`, `:54` - same
  - `src/tests/test_selective.py:31`, `:40`, `:60`, `:71`, `:87`, `:95`, `:102`, `:109`, `:117`, `:129` - same
  - `src/tests/test_sinks.py:89` - same
  - `src/tests/test_warnings.py:125` - same
- **Recommendation:** use `collections.abc.Callable` / `collections.abc.Generator` (import `collections.abc`; in tests, under the existing `TYPE_CHECKING` block).

### Rule: stdlib-logging - stdlib logging import

- **Severity:** low
- **Instance count:** 5
- **Locations:**
  - `src/tests/conftest.py:2` - `import logging`
  - `src/tests/emitters/some_lib.py:1` - `import logging`
  - `src/tests/emitters/unwanted.py:1` - `import logging`
  - `src/tests/emitters/wanted.py:1` - `import logging`
  - `src/tests/test_intercept.py:2` - `import logging`
- **Recommendation:** accept each with `# auditme: accept[stdlib-logging] <reason>`: the emitters must log through stdlib `logging` to exercise the interceptor, and conftest/test_intercept save, restore and drive stdlib logging state.

### Rule: except-interpolation - f-string interpolates caught exception

- **Severity:** low
- **Instance count:** 5
- **Locations:**
  - `src/tests/emitters/some_lib.py:23` - `logger.exception(f'Caught an exception in some_lib.py: {e}')`
  - `src/tests/emitters/unwanted.py:23` - `logger.exception(f'Caught an exception in unwanted.py: {e}')`
  - `src/tests/emitters/wanted.py:23` - `logger.exception(f'Caught an exception in wanted.py: {e}')`
  - `src/tests/test_level_and_diagnose.py:16` - `loguru.logger.exception(f'search failed: {e}')`
  - `bin/demo-logging.py:39` - `loguru.logger.exception(f'Caught an exception in demo-logging.py: {e}')`
- **Recommendation:** drop `: {e}` and the `as e` binding; `logger.exception` already records the exception and traceback. No test asserts on the interpolated text (checked with grep).

### Rule: literal-duplication - identical ordered literal across 2 locations

- **Severity:** low
- **Instance count:** 2
- **Locations:**
  - `src/tests/test_level_and_diagnose.py:59` - `('a debug', 'an info', 'a warning')`
  - `src/tests/test_level_and_diagnose.py:62` - `('a debug', 'an info', 'a warning')`
- **Recommendation:** hoist to a module constant (`ALL_MESSAGES`) used by both parametrize rows.

### Rule: bare-parametric-annotation - bare `dict`

- **Severity:** low
- **Instance count:** 2
- **Locations:**
  - `src/tests/fixtures/base.py:53` - `def find(self, message: str) -> dict:`
  - `src/tests/test_sinks.py:61` - `def counting_loads(line: str) -> dict:`
- **Recommendation:** `dict[str, typing.Any]` (the jsonl record shape).

### Rule: mutable-module-level-exported - `disabled_` read by another file

- **Severity:** low
- **Instance count:** 1
- **Locations:**
  - `src/logit/base.py:32` - `disabled_ = []` (read by `src/tests/test_selective.py:135`)
- **Recommendation:** accept with `# auditme: accept[mutable-module-level-exported] <reason>`: it is the module's own mutable record of what it disabled, appended and drained by `setup_logger`/`reset`, so it cannot be a tuple; the one external read is a test asserting it does not grow.

### Rule: ruff-version-drift - hook pins a different ruff

- **Severity:** low
- **Instance count:** 1
- **Locations:**
  - `.pre-commit-config.yaml:4` - `ruff on PATH is 0.17.6; the hook pins v0.15.1`
- **Recommendation:** move the `ruff-pre-commit` `rev` to `v0.17.6`, then run `pre-commit run --all-files` and commit any reformat separately.

### Rule: duplicate-side-effect-per-target - `jsonl_file` resolved twice in `LogCapture`

- **Severity:** low
- **Instance count:** 1
- **Locations:**
  - `src/tests/fixtures/base.py:34` - `LogCapture: methods ['jsonl_text', 'records'] share sink logit.jsonl_file`
- **Recommendation:** add one `jsonl_path()` method that `records()` and `jsonl_text()` both call (also closes the A14 row on the same line).

## Phase B per-question results

Every sampled question ran in full mode (whole tree): review-1 recorded no `**Commit:**`. Listed questions were judged candidate by candidate. Each reviewer covered the 18 Python files under `src/` (excluding `__pycache__` and `src/logit.egg-info`) and `bin/demo-logging.py`; documentation questions read `AGENTS.md`, `README.md`, `pyproject.toml` and `.pre-commit-config.yaml`.

### A1 (listed): External call envelope

- **Candidates judged:** 0 (the lister found none). **Hits:** none.

### A2 (sampled): Except tuple coverage

- **Mode:** full
- **Hits:**
  - `src/logit/base.py:84` - `try` around `linecache.getline` reads and decodes a source file; catches `OSError` only, `UnicodeDecodeError` missing (CPython's `linecache` swallows both today, so nothing escapes in practice)
  - `src/logit/base.py:335` - `contextlib.suppress(ValueError)` around `loguru.logger.remove(sink_id)`, which closes file sinks; `OSError` missing, so a close failure would replace the original error re-raised at `:337`
- **No-hit confirmation:** 3 envelopes touch disk; the third (`base.py:295`, `except OSError`) passes.

### A3 (sampled): Domain-error layering

- **Mode:** full. **Hits:** none. The package defines no domain `*Error` class.

### A4 (listed): Docstring `Raises` accuracy

- **Candidates judged:** 0. **Hits:** none.

### A5 (sampled): Two sources of truth

- **Mode:** full. **Hits:** none. `stderr_level` falls back to `level` explicitly (`base.py:284`, documented).

### A6 (sampled): Stage method dual-path

- **Mode:** full. **Hits:** none. No pipeline-stage class.

### A7 (sampled): Constructor purity

- **Mode:** full. **Hits:** none. Two `__init__` methods, both attribute-only.

### A8 (sampled): Late dataclass mutation

- **Mode:** full. **Hits:** none. No dataclasses.

### A9 (sampled): Pure-named function side effects

- **Mode:** full. **Hits:** none. No function uses a listed pure prefix.

### A10 (sampled): Predicate semantics

- **Mode:** full. **Hits:** none. No predicate functions.

### A11 (listed): Exhaustion via assert_never

- **Candidates judged:** 0. **Hits:** none.

### A12 (sampled): assert misuse

- **Mode:** full. **Hits:** none. No `assert` in non-test code.

### A13 (sampled): Same value to multiple structural slots

- **Mode:** full. **Hits:** none.

### A14 (sampled): Repeated computation per request

- **Mode:** full
- **Hits:**
  - `src/logit/base.py:75` - `showwarning` rebuilds `internal_files()` on every warning; its value is fixed for the process
  - `src/tests/fixtures/base.py:34` - `records()` and `jsonl_text()` each resolve `logit.jsonl_file(...)` on every call (also sweep: `duplicate-side-effect-per-target`)

### A15 (sampled): Duplicate constructor / serialisation logic

- **Mode:** full
- **Hits:**
  - `bin/demo-logging.py:51` - `subprocess_entrypoint` builds the `StreamToLogger('INFO')`/`StreamToLogger('ERROR')` pair and `redirect_stdout`/`redirect_stderr` inline
  - `bin/demo-logging.py:87` - `main` repeats the same pair and redirect
  - `src/tests/fixtures/base.py:85` - `LogCapture.redirect` repeats it a third time

### A16 (sampled): CLI entry envelope

- **Mode:** full. **Hits:** none. No `cli/` package or `run_*` function.

### A17 (listed): Public-surface drift

- **Candidates judged:** 2 (`src/logit/__init__.py`, `src/tests/emitters/__init__.py`)
- **Hits:**
  - `src/logit/__init__.py:3` - `jsonl_file`, `log_file`, `reset` and `showwarning` are in `__all__` but nothing outside `src/logit` and `src/tests` reads them; the README documents all four as public API

### A18 (sampled): Hot-path setup

- **Mode:** full. **Hits:** none.

### A19 (listed): Wrong logger level for broad-except

- **Candidates judged:** 6
- **Hits:**
  - `bin/demo-logging.py:38` - narrow `except ValueError` logs at `exception` and carries on
  - `src/tests/emitters/some_lib.py:22` - same
  - `src/tests/emitters/unwanted.py:22` - same
  - `src/tests/emitters/wanted.py:22` - same
  - `src/tests/test_intercept.py:62` - same (the test asserts the record carries `exc_info`)
  - `src/tests/test_level_and_diagnose.py:15` - narrow `except RuntimeError`, same
- **Note:** in every case the `try` raises on purpose so the handler can emit a `logger.exception` record, which is what the demo shows and the tests assert. The brief has no exemption for that.

### A20 (sampled): Mutable module-level singleton

- **Mode:** full
- **Hits:**
  - `src/logit/base.py:32` - `disabled_ = []` read as `logit.base.disabled_` by `src/tests/test_selective.py:135` (also sweep: `mutable-module-level-exported`)

### A21 - A25 (sampled)

- **Mode:** full. **Hits:** none for A21 (lazy init race), A22 (fall-through after partial handling), A23 (discarded multi-return), A24 (subprocess memoisation) and A25 (shallow immutable wrapper).

### S1 (sampled): Type annotations on every signature

- **Mode:** full. **Hits:** none in non-test source. Tests: 0 missing parameter annotations, 0 missing return annotations, 0 modules affected, 15 modules fully annotated.

### S2 (sampled): Naming convention

- **Mode:** full
- **Hits:**
  - `src/logit/base.py:18` - `showwarning_` is a module constant (never reassigned) but named like the mutable-state names (`disabled_`); UPPER_SNAKE expected

### S3 (sampled): TYPE_CHECKING block placement

- **Mode:** full. **Hits:** none.

### S4 (sampled): Project-specific rule files

- **Mode:** full
- **Hits:**
  - `src/logit/base.py:2` - coding-standards.md (annotation-only imports go under `TYPE_CHECKING`): `datetime` is used only in the lazily evaluated `type` aliases on lines 24-25
  - `src/logit/base.py:40` - coding-standards.md (comments): commented-out `showwarning_orig` function, lines 40-49
  - `src/logit/base.py:96` - same: commented-out code, lines 96-97
  - `src/logit/base.py:287` - same: `# remove all handlers` restates the next line
  - `src/logit/base.py:296` - same: commented-out code, lines 296-297
  - `src/logit/base.py:308` - same: `# log to file` restates the call
  - `src/logit/base.py:320` - same: `# log to jsonl` restates the call
  - `src/tests/` - python/testing.md (tests mirror the source layout): no `src/tests/test_base.py`; `base.py`'s tests are split by capture path
  - `src/tests/conftest.py:16` - python/testing.md (fixtures live in `src/tests/fixtures/`, conftest loads them): `capture` and its helper `make_capture` (`:31`) are defined in conftest
  - `src/tests/conftest.py:56` - same: `setup` is defined in conftest

### P1 - P3, Sec1 - Sec5 (sampled)

- **Mode:** full. **Hits:** none. `src/tests/emitters/secrets.py` holds a placeholder, not a real secret: its docstring names it as the value that must not reach the logs.

### T1 (listed): Test coverage of branchy logic

- **Candidates judged:** 7
- **Hits:**
  - `bin/demo-logging.py:24` - `log_messages`: no test runs the demo, so neither its `try` nor its `except ValueError` branch is exercised

### T2 (listed): Property-based tests

- **Candidates judged:** 0. **Hits:** none.

### T3 (sampled): Integration vs unit balance

- **Mode:** full. **Hits:** none. The `capture`/`setup` fixtures drive the real `setup_logger` end to end.

### D1 - D3 (sampled)

- **Mode:** full. **Hits:** none. Every import is declared and every declared dependency imported; no lockfile-drift hit.

### Doc1 (listed): AGENTS.md project structure

- **Candidates judged:** 3
- **Hits:**
  - `AGENTS.md:35-36` (Logging System Design) - names `log/log.log` and `log/log.jsonl` without saying they are written at run time and git-ignored

### Doc2 (listed): AGENTS.md tools and libraries list

- **Candidates judged:** 7
- **Hits:**
  - `AGENTS.md:73` (Tools and Libraries) - omits `hypothesis` (dev dependency), and the `ruff`, `ruff-format` and `shellcheck` pre-commit hooks

### Doc3 (sampled): README.md and AGENTS.md consistent

- **Mode:** full
- **Hits:**
  - `AGENTS.md:73` - omits `hypothesis`, which `README.md:12` names as part of the dev group

### Doc4 (listed): Specs match implementation

- **Candidates judged:** 0 (no `agents/specs/`). **Hits:** none.

### Doc5 (listed): User docs match implementation

- **Candidates judged:** 9
- **Hits:**
  - `README.md:55` - says `log.log` uses "the same record format as stderr, without colour", but only `STDERR_FORMAT` (`src/logit/base.py:28`) adds `{process.id} {thread.id}`; `log.log` lines carry neither

### Coverage (sampled)

Every sampled hit above is a first full-tree run of that question on this project: coverage, not drift. None is marked "missed by" review-1.

## Phase B findings (consolidated)

### Finding P1: Source-line lookup misses `UnicodeDecodeError`

- **Category:** A. **Question:** A2. **Severity:** low
- **Location:** `src/logit/base.py:84`
- **Description:** the `except` around `linecache.getline` names `OSError` only.
- **Recommendation:** `except (OSError, UnicodeDecodeError):`.

### Finding P2: Sink rollback can mask the original error

- **Category:** A. **Question:** A2. **Severity:** low
- **Location:** `src/logit/base.py:335`
- **Description:** `contextlib.suppress(ValueError)` around `remove(sink_id)` does not cover `OSError` from closing a file sink; one would replace the `OSError` the handler is re-raising.
- **Recommendation:** `contextlib.suppress(ValueError, OSError)`, with a test that makes removal fail.

### Finding P3: `internal_files()` recomputed per warning

- **Category:** A. **Question:** A14. **Severity:** low
- **Location:** `src/logit/base.py:75`
- **Recommendation:** decorate `internal_files` with `functools.cache`.

### Finding P4: `jsonl_file` resolved in two `LogCapture` methods

- **Category:** A. **Question:** A14 (and sweep `duplicate-side-effect-per-target`). **Severity:** low
- **Location:** `src/tests/fixtures/base.py:34`
- **Recommendation:** one `jsonl_path()` method, as in the mechanical finding.

### Finding P5: Stream-redirect pair built in three places

- **Category:** A. **Question:** A15. **Severity:** low
- **Location:** `bin/demo-logging.py:51`, `bin/demo-logging.py:87`, `src/tests/fixtures/base.py:85`
- **Description:** each builds the INFO/ERROR `StreamToLogger` pair and both redirects by hand.
- **Recommendation:** see decision D1 on the review page.

### Finding P6: `__all__` exports with no consumer outside the tests

- **Category:** A. **Question:** A17. **Severity:** low
- **Location:** `src/logit/__init__.py:3`
- **Recommendation:** dismiss: the README documents `jsonl_file`, `log_file`, `reset` and `showwarning` as public API for library users, so a consumer outside this repository is the intended one.

### Finding P7: `logger.exception` in handlers that carry on

- **Category:** A. **Question:** A19. **Severity:** low
- **Location:** the six handlers listed under A19
- **Recommendation:** dismiss all six: each catches an exception its own `try` raises so that it can emit the `logger.exception` record the demo shows and the tests assert on.

### Finding P8: Demo script untested

- **Category:** T. **Question:** T1. **Severity:** low
- **Location:** `bin/demo-logging.py:24`
- **Recommendation:** dismiss: a visual demo whose `try` always raises; every capture path it shows is tested through the emitters.

### Finding P9: AGENTS.md names log files without saying they are run-time output

- **Category:** Doc. **Question:** Doc1. **Severity:** low
- **Location:** `AGENTS.md:35-36`
- **Recommendation:** say the files are written at run time to `log/`, which is git-ignored.

### Finding P10: AGENTS.md tools list incomplete

- **Category:** Doc. **Question:** Doc2, Doc3. **Severity:** low
- **Location:** `AGENTS.md:73`
- **Recommendation:** add `hypothesis` (property tests in `test_streams.py`), and ruff and shellcheck (run through pre-commit).

### Finding P11: README misstates the `log.log` record format

- **Category:** Doc. **Question:** Doc5. **Severity:** medium
- **Location:** `README.md:55`
- **Recommendation:** say `log.log` has the stderr format without colour and without the process and thread ids.

### Finding P12: `showwarning_` named like mutable state

- **Category:** S. **Question:** S2. **Severity:** low
- **Location:** `src/logit/base.py:18`
- **Recommendation:** rename to `ORIGINAL_SHOWWARNING` and update `reset()`.

### Finding P13: `datetime` imported only for annotations

- **Category:** S. **Question:** S4. **Severity:** low
- **Location:** `src/logit/base.py:2`
- **Recommendation:** move the import under `if typing.TYPE_CHECKING:`.

### Finding P14: Commented-out code and restating comments in `base.py`

- **Category:** S. **Question:** S4. **Severity:** low
- **Location:** `src/logit/base.py:40-49`, `:96-97`, `:287`, `:296-297`, `:308`, `:320`
- **Recommendation:** delete them.

### Finding P15: Test layout and fixture placement depart from the testing rule

- **Category:** S. **Question:** S4. **Severity:** low
- **Location:** `src/tests/` (no `test_base.py`), `src/tests/conftest.py:16`, `:31`, `:56`
- **Recommendation:** see decisions D2 and D3 on the review page.

## Decisions

### D1: How to remove the triplicated stream-redirect code (P5)

- **Background:** `bin/demo-logging.py` (twice) and `src/tests/fixtures/base.py` (once) each build `StreamToLogger(level='INFO')` for stdout and `StreamToLogger(level='ERROR')` for stderr and enter both redirects. The README shows the same pattern for a single stream.
- **Affects:** `src/logit/base.py`, `src/logit/__init__.py`, `README.md`, the demo and the fixture.
- **Options:**
  - **Add `logit.redirect_streams()` (recommended):** a context manager in the library doing the pair; all three call sites use it, and the README documents it. One new public symbol.
  - **Factor within the demo only:** one helper in `bin/demo-logging.py`; the fixture copy stays, and the next full audit reports A15 at the fixture again.
  - **Leave as is:** the finding recurs on every full audit.

### D2: Tests split by capture path instead of mirroring `base.py` (P15)

- **Background:** `python/testing.md` says `src/logit/base.py` is tested in `src/tests/test_base.py`. This project deliberately splits `base.py`'s tests by capture path, and AGENTS.md's Tests table documents that split.
- **Options:**
  - **Keep the split and record the exception (recommended):** add one line in `AGENTS.md`'s Tests section saying the tests are split by capture path rather than mirroring `base.py`, on purpose. No test moves.
  - **Merge into `test_base.py`:** one large file of ~800 lines; loses the per-path table.

### D3: Fixtures defined in `conftest.py` (P15)

- **Background:** `python/testing.md` says fixtures live in `src/tests/fixtures/` and conftest only loads them. `capture`, `make_capture` and `setup` are defined in `src/tests/conftest.py`, beside `LogCapture` in `src/tests/fixtures/base.py`.
- **Options:**
  - **Move them to `src/tests/fixtures/base.py` (recommended):** conftest loads them via `pytest_plugins = ['tests.fixtures.base']`. No test changes.
  - **Leave them:** the next full audit reports S4 again.

## Files reviewed (Phase B)

- `src/logit/__init__.py`, `src/logit/base.py` - A1-A25, S1-S4, P1-P3, Sec1-Sec5, T1, T2
- `src/tests/conftest.py`, `src/tests/fixtures/base.py`, `src/tests/emitters/*.py`, `src/tests/test_*.py` - A1-A25 (A12 excepted), S1 (count), S2-S4, P1-P3, Sec1-Sec5, T1-T3
- `bin/demo-logging.py`, `bin/demo-logging.sh`, `bin/activate.sh` - A1-A25, S1-S4, P1-P3, Sec1-Sec5, T1
- `AGENTS.md`, `README.md`, `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml` - D1-D3, Doc1-Doc5

## Prior findings re-verified

From summary.md's unresolved list:

- `disabled` state diverges across repeated `setup_logger` calls - resolved at `src/logit/base.py:289` (`re_enable_disabled()`) and `:134` (`reset_disabled_logging()`)
- Dead `LoguruHandler` class - resolved (no match in `src/` or `bin/`)
- Leading-underscore `StreamToLogger._level` - resolved at `src/logit/base.py:183` (`self.level`)
- Silent broad `except` around `linecache.getline` - resolved at `src/logit/base.py:86` (`except OSError`, logs at debug)
- Missing type annotations - resolved (S1 finds none)
- `from loguru import logger` - resolved at `src/logit/base.py:16` (`import loguru`)
- README does not describe the project or its API - resolved (`README.md` Usage section)
- Unaccepted mechanical hits from review-1 - resolved (accept markers at `src/logit/base.py:6`, `src/tests/emitters/__init__.py:1`; `linecache` hoisted; `__all__` sorted)
- Low-severity remainder - resolved: sink rollback at `src/logit/base.py:333`; shared `RECORD_FORMAT` at `:27`; `records()` cache at `src/tests/fixtures/base.py:40`; `log_dir` out of `__all__`; hypothesis tests in `src/tests/test_streams.py:116`; `joblib` in the dev group. The AGENTS.md libraries gap is partly open again as P10.

Every task in `agents/tasks/audit-reviews/tasks-1.md` is ticked and confirmed above.

## Recommendations

1. P11 (medium): fix the README's `log.log` format sentence.
2. Mechanical: switch to `collections.abc`, drop `{e}` interpolation, add the scoped accept markers, bump the ruff hook, and the small test-fixture tidies.
3. P1, P2, P3, P12, P13, P14: small `base.py` fixes.
4. P9, P10: AGENTS.md corrections.
5. D1-D3 as answered; dismiss P6, P7, P8 with `phaseb.py dismiss`.

## Answers

Answered on the review page on 2026-11-21. Every recommendation was accepted; no item was flagged and no comment was left.

| Item | Answer |
|---|---|
| M-alias, M-stdlib, M-interp, M-literal, M-dict, M-mutable, M-ruff, M-jsonl (every mechanical finding) | approved as recommended |
| P1, P2, P3, P9, P10, P11, P12, P13, P14 (fixes) | approved as recommended |
| P6 (A17 `__all__` surface), P7 (six A19 handlers), P8 (T1 demo) | dismissal approved; recorded with `phaseb.py dismiss` on 2026-11-21 |
| D1: stream-redirect code | add `logit.redirect_streams()` |
| D2: test layout | keep the split by capture path and record the exception in AGENTS.md |
| D3: fixtures in conftest | move them to `src/tests/fixtures/base.py` |
