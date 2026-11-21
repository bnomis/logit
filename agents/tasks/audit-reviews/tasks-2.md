# Tasks: Audit Review 2

**Source:** `agents/audit-reviews/review-2.md`
**Created:** 2026-11-21
**Version:** 2

Covers every approved item in review-2's Answers section (2026-11-21): the eight
mechanical findings, the nine Phase B fixes, and decisions D1-D3. The three
dismissals (P6, P7, P8) were recorded in the ledger on 2026-11-21 and need no
task. No task needs a user decision.

Run tests with `source bin/activate.sh` first, as AGENTS.md says. The
pre-commit hooks are ruff, ruff-format and shellcheck; none runs at pre-push.

---

## Task 1: Move the test fixtures out of conftest.py

**Status:** done
**Priority:** medium
**Complexity:** small
**Source Reference:** review-2 decision D3 (finding P15)

**Technical Goal:** follow `python/testing.md`: fixtures live in `src/tests/fixtures/` and `conftest.py` only loads them. Done first, so later tasks edit the fixtures in their new home.

**Subtasks:**

- [x] Move `capture`, `make_capture` and `setup` from `src/tests/conftest.py` into `src/tests/fixtures/base.py`, with the imports they need (`io`, `logging`, `sys`, `pytest`, `logit.base`)
- [x] Reduce `src/tests/conftest.py` to loading them: `pytest_plugins = ['tests.fixtures.base']`. If pytest refuses `pytest_plugins` there, import the two fixtures by full path instead and say so in the commit body
- [x] Update the `conftest.py` and `fixtures/base.py` lines in AGENTS.md's Module Structure list

**Acceptance Criteria:**

- [x] `src/tests/conftest.py` defines no fixture or helper function
- [x] Every test that uses `capture` or `setup` still finds it

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `pytest -m "not slow" src/tests` passes (every test module uses one of the moved fixtures)

**Notes:**

- Key files: `src/tests/conftest.py`, `src/tests/fixtures/base.py`, `AGENTS.md`
- The `stdlib-logging` hit at `src/tests/conftest.py:2` moves with `import logging`; Task 3 accepts it wherever it ends up

---

## Task 2: Tidy the sweep hits in tests, emitters and the demo

**Status:** done
**Priority:** medium
**Complexity:** medium
**Source Reference:** review-2 mechanical findings M-alias, M-dict, M-literal, M-jsonl, M-interp; Phase B A14 row at `src/tests/fixtures/base.py:34`

**Technical Goal:** clear the `typing-deprecated-alias`, `bare-parametric-annotation`, `literal-duplication`, `duplicate-side-effect-per-target` and `except-interpolation` hits.

**Subtasks:**

- [x] Replace every `typing.Callable` and `typing.Generator` with `collections.abc.Callable` / `collections.abc.Generator`: `src/logit/base.py:24-25`, the fixture signatures (now in `src/tests/fixtures/base.py`), and the test signatures in `test_level_and_diagnose.py`, `test_rotation.py`, `test_selective.py`, `test_sinks.py`, `test_warnings.py`. In test files, import `collections.abc` inside the existing `if typing.TYPE_CHECKING:` block
- [x] Annotate `LogCapture.find` and `counting_loads` (`src/tests/test_sinks.py:61`) as returning `dict[str, typing.Any]`; give `records()` and `records_cache` the same element type
- [x] Hoist `['a debug', 'an info', 'a warning']` in `src/tests/test_level_and_diagnose.py` to a module constant `ALL_MESSAGES` used by the DEBUG and ERROR parametrize rows
- [x] Add `LogCapture.jsonl_path()` returning `logit.jsonl_file(directory=self.directory, subprocess=self.subprocess)`, and call it from `records()` and `jsonl_text()`
- [x] Drop `: {e}` and the `as e` binding from the `logger.exception` calls at `src/tests/emitters/some_lib.py:23`, `unwanted.py:23`, `wanted.py:23`, `src/tests/test_level_and_diagnose.py:16` and `bin/demo-logging.py:39`, without changing which line each call is on

**Acceptance Criteria:**

- [x] `python3 ~/.claude/skills/auditme/checks/audit.py .` reports no unaccepted `typing-deprecated-alias`, `bare-parametric-annotation`, `literal-duplication`, `duplicate-side-effect-per-target` or `except-interpolation` hit

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `pytest -m "not slow" src/tests` passes (the signature changes touch every test module)

**Notes:**

- Depends on Task 1
- `bin/demo-logging.py` is a script: check it still runs with `bin/demo-logging.sh`

---

## Task 3: Accept the stdlib-logging and disabled_ hits with scoped markers

**Status:** done
**Priority:** low
**Complexity:** small
**Source Reference:** review-2 mechanical findings M-stdlib, M-mutable; Phase B A20 row at `src/logit/base.py:32`

**Technical Goal:** mark the sites where the code must do what the rule forbids, scoped to the one rule.

**Subtasks:**

- [x] Add an inline `# auditme: accept[stdlib-logging] <reason>` on the `import logging` line of `src/tests/emitters/some_lib.py`, `unwanted.py`, `wanted.py` (reason: the emitter logs through stdlib logging to exercise the interceptor), `src/tests/test_intercept.py` (drives stdlib logging) and the fixture module that now imports it after Task 1 (saves and restores stdlib logging state). Inline, so no emitter line moves
- [x] Add `# auditme: accept[mutable-module-level-exported] <reason>` on the line above `disabled_ = []` in `src/logit/base.py` (reason: the module's own record of what it disabled, appended and drained by setup_logger and reset; the one outside read is a test checking it does not grow)

**Acceptance Criteria:**

- [x] `python3 ~/.claude/skills/auditme/checks/audit.py .` reports every `stdlib-logging` and `mutable-module-level-exported` hit as accepted

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `pytest src/tests/test_selective.py src/tests/test_intercept.py -m "not slow"` passes

**Notes:**

- Depends on Task 1

---

## Task 4: Move the ruff hook to the version the audit runs

**Status:** done
**Priority:** low
**Complexity:** small
**Source Reference:** review-2 mechanical finding M-ruff

**Technical Goal:** make the commit hook and the audit format with the same ruff.

**Subtasks:**

- [x] Set the `ruff-pre-commit` `rev` in `.pre-commit-config.yaml` to `v0.17.6`
- [x] Run `pre-commit run --all-files`; commit any reformat or lint fix it makes as its own commit (`style: reformat with ruff 0.17.6`), separate from the rev change

**Acceptance Criteria:**

- [x] `python3 ~/.claude/skills/auditme/checks/audit.py .` reports no `ruff-version-drift` hit

**Definition of Done:**

- [x] The task's commits pass their pre-commit hooks (never `--no-verify`)
- [x] If the reformat touched Python files, `pytest -m "not slow" src/tests` passes

**Notes:**

- If the ruff on PATH is no longer 0.17.6 when this runs, use the version `ruff --version` prints, and say so in the commit body

---

## Task 5: Small fixes in base.py

**Status:** done
**Priority:** medium
**Complexity:** small
**Source Reference:** review-2 findings P1, P2, P3, P12, P13, P14

**Technical Goal:** close the A2, A14, S2 and S4 findings in `src/logit/base.py`.

**Subtasks:**

- [x] P1: `except (OSError, UnicodeDecodeError):` around `linecache.getline`
- [x] P2: `contextlib.suppress(ValueError, OSError)` around `loguru.logger.remove(sink_id)` in the rollback
- [x] P2: add a test to `src/tests/test_sinks.py`, beside `test_failed_sink_registration_leaves_no_sinks_registered`, where removing a sink during rollback raises `OSError` and `setup_logger` still raises the original sink-registration `OSError`
- [x] P3: decorate `internal_files` with `functools.cache`
- [x] P12: rename `showwarning_` to `ORIGINAL_SHOWWARNING` and update `reset()`
- [x] P13: move `import datetime` under `if typing.TYPE_CHECKING:`
- [x] P14: delete the commented-out `showwarning_orig` block, the commented-out lines after `showwarning`'s last call and in `setup_logger` (`# dont need to take over stdout`, `# logger.add(sys.__stdout__)`), and the comments that restate the next line (`# remove all handlers`, `# log to file`, `# log to jsonl`)

**Acceptance Criteria:**

- [x] No commented-out code remains in `src/logit/base.py`
- [x] The new rollback test fails if `OSError` is removed from the `suppress`
- [x] `grep -rn showwarning_ src bin` finds nothing

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `pytest src/tests/test_sinks.py src/tests/test_warnings.py src/tests/test_rotation.py -m "not slow"` passes

**Notes:**

- Key file: `src/logit/base.py`
- `RotationSpec` and `RetentionSpec` are read by the fixtures only as annotations, so the `TYPE_CHECKING` import is safe; check that `pytest` still collects

---

## Task 6: Add logit.redirect_streams()

**Status:** done
**Priority:** medium
**Complexity:** medium
**Source Reference:** review-2 decision D1 (finding P5)

**User Story:** As a user of logit, I want one call that routes stdout to INFO and stderr to ERROR, so that I do not rebuild the `StreamToLogger` pair by hand.

**Subtasks:**

- [x] Add a `@contextlib.contextmanager` `redirect_streams(stdout_level: str = 'INFO', stderr_level: str = 'ERROR')` to `src/logit/base.py`, with a docstring, that enters `contextlib.redirect_stdout(StreamToLogger(level=stdout_level))` and `contextlib.redirect_stderr(StreamToLogger(level=stderr_level))`
- [x] Export it in `src/logit/__init__.py` and `__all__` (keep the order ruff's RUF022 writes)
- [x] Use it in `bin/demo-logging.py` (`subprocess_entrypoint` and `main`) and in `LogCapture.redirect`
- [x] Add tests to `src/tests/test_streams.py`: stdout lands at INFO and stderr at ERROR by default; custom levels are honoured; a `print()` inside it is attributed to the caller's file and line; `sys.stdout`/`sys.stderr` are restored on exit, including after an exception
- [x] Document it in README.md's Usage section beside `StreamToLogger`

**Acceptance Criteria:**

- [x] No file builds the INFO/ERROR `StreamToLogger` pair by hand
- [x] README.md shows `logit.redirect_streams()`

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)
- [x] `pytest src/tests/test_streams.py src/tests/test_selective.py -m "not slow"` passes
- [x] `bin/demo-logging.sh` runs to completion

**Notes:**

- Depends on Tasks 1 and 5 (both edit the same files)
- `StreamToLogger.write` logs with `opt(depth=1)`, so attribution is to `print`'s caller whatever wraps the redirect; the attribution test confirms it

---

## Task 7: Correct README.md and AGENTS.md

**Status:** done
**Priority:** high
**Complexity:** small
**Source Reference:** review-2 findings P11 (medium), P9, P10; decision D2

**Technical Goal:** make the user guide and the agent guide match the code.

**Subtasks:**

- [x] P11: in README.md, say `log.log` has the stderr record format without colour and without the process and thread ids
- [x] In README.md's `setup_logger(...)` example, add the `rotation` and `retention` parameters with their defaults, and a short paragraph on each (from the `setup_logger` docstring). This one is not a review-2 item: the example lists every other parameter and omits these two, and the user-guide rule requires every option to be documented
- [x] P9: in AGENTS.md's Multi-Output Configuration list, say `log/log.log` and `log/log.jsonl` are written at run time and `log/` is git-ignored
- [x] P10: add to AGENTS.md's Tools and Libraries `hypothesis` (property tests in `src/tests/test_streams.py`), and `ruff` and `shellcheck` (run through pre-commit)
- [x] D2: add a line to AGENTS.md's Tests section saying `base.py`'s tests are split by capture path on purpose rather than mirrored as `test_base.py`; add the missing `test_level_and_diagnose.py` and `test_rotation.py` rows to its table

**Acceptance Criteria:**

- [x] Every parameter of `setup_logger` appears in README.md's example
- [x] AGENTS.md's tools list names every declared dependency and every pre-commit hook's tool

**Definition of Done:**

- [x] The task's commit passes its pre-commit hooks (never `--no-verify`)

**Notes:**

- Depends on Task 6 (README.md also gains `redirect_streams` there)

---

## Task 8: Whole-tree checks before merge

**Status:** done
**Priority:** medium
**Complexity:** small
**Source Reference:** review-2 (all items)

**Technical Goal:** confirm the list as a whole leaves the tree clean.

**Subtasks:**

- [x] Run `pre-commit run --all-files`
- [x] Run `python3 ~/.claude/skills/auditme/checks/audit.py . > /tmp/audit-logit.jsonl` and check every hit is accepted
- [x] Run the tests below
- [x] In `agents/audit-reviews/summary.md`, move review-2's findings from Unresolved to Recently resolved

**Acceptance Criteria:**

- [x] The sweep reports zero unaccepted hits

**Definition of Done:**

- [x] `pre-commit run --all-files` exits 0
- [x] `pytest -m "not slow" src/tests` passes (every test module imports `logit`, which this list changed)
- [x] `pytest -m slow src/tests/test_concurrency.py` passes (it drives `StreamToLogger` and `setup_logger` across processes)

**Notes:**

- Depends on Tasks 1-7
