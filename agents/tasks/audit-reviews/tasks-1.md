# Tasks: Audit Review 1

**Source:** `agents/audit-reviews/review-1.md`
**Created:** 2026-08-04
**Version:** 1

Covers all 9 unaccepted mechanical hits and all 14 Phase B findings from review-1.
Nothing in the review has been implemented yet, so every task starts at `todo`.

The two open decisions from review-1 were settled by the user on 2026-08-04:
Task 9 rolls back registered sinks on failure, and Task 11 drops `log_dir`
from `__all__`. No task needs further human input.

---

## Task 1: Re-enable previously disabled modules on re-setup

**Status:** done
**Priority:** high
**Complexity:** medium
**Source Reference:** Finding "`disabled` state diverges across repeated `setup_logger` calls" (A5)

**Technical Goal:** make `setup_logger` idempotent with respect to `disabled`, so that loguru, stdlib logging and warnings all silence exactly the modules named in the most recent call.

**Subtasks:**

- [x] In `setup_logger`, drain `disabled_` (calling `logger.enable(name)` for each popped name) before applying the new `disabled` list, mirroring what `reset()` already does
- [x] Factor the drain into a small helper shared by `setup_logger` and `reset()` so the two cannot drift
- [x] Add `src/tests/test_selective.py::test_resetup_re_enables_the_previous_disabled_list` - disable `wanted`, call setup again disabling `unwanted`, run all emitters, assert `capture.names() == {WANTED, SOME_LIB}`
- [x] Extend the new test (or parametrise it over `PATHS`) so all five capture paths are checked, matching `test_every_capture_path_is_suppressed`
- [x] Add a test asserting `logit.base.disabled_` does not grow across repeated `setup_logger` calls

**Acceptance Criteria:**

- [x] `setup_logger(disabled=['a'])` followed by `setup_logger(disabled=['b'])` leaves `a` logging normally and only `b` silenced, on all five capture paths
- [x] `disabled_` contains exactly the names from the most recent call
- [x] `pytest src/tests/test_selective.py` passes
- [x] `pytest src/tests/test_warnings.py` still passes (`reset()` behaviour unchanged)

**Notes:**

- Key file: `src/logit/base.py:194-202` (`reset`), `:205-241` (`setup_logger`)
- The divergence is real and reproducible: `config_logger_default` rebuilds the whole dictConfig and `setup_warnings` calls `warnings.resetwarnings()`, so only the loguru path accumulates
- AGENTS.md documents the three mechanisms as equivalent; this task is what makes that true
- Correction found during implementation: the note above is wrong for the stdlib logging path. `dictConfig` only reconfigures loggers named in its `loggers` key, so a logger disabled by a previous call stayed disabled (`propagate=False`) even after a later call - including `reset()` - that did not name it. Fixed by adding a parallel `disabled_logging_` list and a `reset_disabled_logging()` helper that restores each previously-disabled stdlib logger directly before the next `dictConfig` call, called from both `config_logger_default` and `reset()`.

---

## Task 2: Delete the dead `LoguruHandler` class

**Status:** done
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding "dead `LoguruHandler` class" (T1)

**Technical Goal:** remove a class that is never instantiated, referenced, exported or tested, and which would misattribute every record if it were ever wired in.

**Subtasks:**

- [x] Delete `LoguruHandler` from `src/logit/base.py:77-79`
- [x] Confirm with grep that nothing under `src/`, `bin/` or the dictConfig at `src/logit/base.py:119-128` references it

**Acceptance Criteria:**

- [x] `grep -rn LoguruHandler src bin` returns nothing
- [x] `pytest -m "not slow"` passes
- [x] The `legacy-formatting-format` hit at `src/logit/base.py:79` no longer appears in the audit script output

**Notes:**

- Blocks Task 7 and Task 10 (deleting the class removes one signature to annotate and one mechanical hit to accept)
- If the class is being kept deliberately as a documented alternative, say so and this task becomes "add a docstring and a test" instead

---

## Task 3: Narrow the silent broad `except` around the source-line lookup

**Status:** done
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding "silent broad `except` around `linecache.getline`" (mechanical `silent-broad-except`, A19)

**Technical Goal:** stop swallowing every exception class in the warning path, and make a failed source-line lookup diagnosable.

**Subtasks:**

- [x] Change `except Exception:` at `src/logit/base.py:61` to `except OSError:`
- [x] Remove the `linecache = None` rebind (the name is never read again)
- [x] Add `logger.debug` on the failure path recording the path that could not be read
- [x] Add a test covering the failure branch - e.g. `warnings.showwarning(..., filename=str(tmp_path))` where the path is a directory - asserting the warning record is still emitted without a source line

**Acceptance Criteria:**

- [x] `KeyboardInterrupt` / `MemoryError` raised during the lookup are no longer swallowed
- [x] An unreadable filename still produces the warning record and no source-line record
- [x] `pytest src/tests/test_warnings.py` passes
- [x] The `silent-broad-except` hit no longer appears in the audit script output

**Notes:**

- Key file: `src/logit/base.py:56-65`
- The `else: line = line` branch on lines 64-65 is a no-op self-assignment; drop it while you are in there
- Related: Task 10 hoists the `import linecache` on line 58 out of the function
- Correction found during implementation: CPython's `linecache.updatecache` already wraps its own `os.stat`/`open` calls in `except OSError: return []`, so `linecache.getline` never raises `OSError` for an unreadable path - a directory `filename` just yields `''` without touching our `except` clause. The regression test uses `monkeypatch.setattr('linecache.getline', ...)` to force the `OSError` directly instead, so the branch is actually exercised.

---

## Task 4: Rename `StreamToLogger._level` to `level`

**Status:** done
**Priority:** medium
**Complexity:** small
**Source Reference:** Mechanical rules `leading-underscore-self`, `leading-underscore-attribute-access`

**Technical Goal:** comply with the no-leading-underscores rule in the Python coding standard.

**Subtasks:**

- [x] Rename the attribute at `src/logit/base.py:148` and its use at `:152`
- [x] Grep `src/` and `bin/` for `_level` to confirm no external reader

**Acceptance Criteria:**

- [x] `grep -rn "_level" src bin` returns nothing
- [x] `pytest src/tests/test_streams.py` passes
- [x] Both `leading-underscore-*` rules return zero hits from the audit script

**Notes:**

- Key file: `src/logit/base.py:146-155`
- The constructor parameter is already named `level`, so the rename removes the mismatch rather than creating one
- Correction found during implementation: `grep -rn "_level" src bin` does not literally return nothing - it matches pre-existing test function names containing the substring (e.g. `test_stream_level_is_configurable`, `test_stdlib_level_maps_to_loguru_level`). None of these reference the `StreamToLogger._level` attribute; the intent of the criterion (no leftover attribute reference) is satisfied

---

## Task 5: Use the full import path for loguru in `base.py`

**Status:** done
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding "`from loguru import logger` violates the full-import-path rule" (S4)

**Technical Goal:** make `base.py` consistent with every other file in the tree, and remove the ambiguity between loguru's `logger` and a stdlib logger in a module that handles both.

**Subtasks:**

- [x] Replace `from loguru import logger` at `src/logit/base.py:11` with `import loguru`
- [x] Qualify all uses as `loguru.logger` (roughly 12 sites: `showwarning`, `InterceptHandler.emit`, `StreamToLogger.write`, `reset`, `setup_logger`)
- [x] Run `ruff check && ruff format --check`

**Acceptance Criteria:**

- [x] `grep -rn "^from " src bin` returns only `src/logit/__init__.py`
- [x] `pytest -m "not slow"` passes
- [x] `ruff check` is clean

**Notes:**

- Key file: `src/logit/base.py`
- Do this after Tasks 1-4 so those edits do not have to be rebased over a whole-file rename
- The `__init__.py` re-export on line 1 is the sanctioned exception and stays as it is

---

## Task 6: Move annotation-only imports into TYPE_CHECKING blocks

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Finding "annotation-only imports outside TYPE_CHECKING" (S4)

**Technical Goal:** follow the standard's rule that imports needed only for annotations sit inside `if typing.TYPE_CHECKING:`.

**Subtasks:**

- [ ] `src/logit/base.py:8` - `typing` is used only in `stderr: typing.TextIO | None`; move it (keep `pathlib`, used at runtime by `this_dir`)
- [ ] `src/tests/conftest.py:3,5` - move `pathlib` and `typing` (keep `io`, `logging`, `sys`, used at runtime)
- [ ] `src/tests/fixtures/base.py:4,5` - move `pathlib` and `typing` (keep `io`, used at runtime by nothing but the annotation - verify before moving; `contextlib` and `json` stay)
- [ ] Use the same idiom in all three files so a convention exists for the tree

**Acceptance Criteria:**

- [ ] Every remaining module-level import is referenced outside an annotation
- [ ] `pytest -m "not slow"` passes (annotations are lazily evaluated on 3.14, so nothing should break)
- [ ] `ruff check` is clean

**Notes:**

- Depends on Task 5 (both touch the `base.py` import block)
- Python 3.14 evaluates annotations lazily, so no `from __future__ import annotations` is needed - and the standard forbids adding it

---

## Task 7: Annotate the package and demo signatures

**Status:** todo
**Priority:** medium
**Complexity:** small
**Source Reference:** Finding "missing type annotations across the tree" (S1) - package and `bin/` portion

**Technical Goal:** give every signature in shipped code the parameter and return annotations the standard requires.

**Subtasks:**

- [ ] `src/logit/base.py:46` `showwarning` - annotate all six parameters and `-> None`, mirroring `warnings.showwarning`'s signature (`message: Warning | str`, `category: type[Warning]`, `filename: str`, `lineno: int`, `file: typing.TextIO | None`, `line: str | None`)
- [ ] `src/logit/base.py:147,150,154` - annotate `StreamToLogger.__init__`, `write` and `flush`
- [ ] `bin/demo-logging.py:24,42,49,58,63,74,85` - add `-> None` to all seven functions
- [ ] Run `ruff check && ruff format --check`

**Acceptance Criteria:**

- [ ] An AST walk over `src/logit/` and `bin/` reports zero signatures missing parameter or return annotations
- [ ] `pytest -m "not slow"` passes
- [ ] `bin/demo-logging.sh` still runs end to end

**Notes:**

- Depends on Task 2 (`LoguruHandler.emit` disappears rather than being annotated)
- Depends on Task 6 (the annotations may need `typing` under TYPE_CHECKING)
- `StreamToLogger` is passed to `contextlib.redirect_stdout`, so `write`/`flush` are the file-like protocol - annotate them to match `typing.TextIO`

---

## Task 8: Annotate the test and emitter signatures

**Status:** todo
**Priority:** low
**Complexity:** medium
**Source Reference:** Finding "missing type annotations across the tree" (S1) - test portion

**Technical Goal:** bring the remaining 62 unannotated signatures in `src/tests/` up to the standard.

**Subtasks:**

- [ ] `src/tests/emitters/{some_lib,unwanted,wanted}.py:8` - add `-> None` to `func`
- [ ] Annotate every test function's fixture parameters and `-> None`: `capture: tests.fixtures.base.LogCapture`, `setup: typing.Callable[..., tests.fixtures.base.LogCapture]` (the types are already spelled out in `src/tests/conftest.py:14,39`)
- [ ] Annotate parametrised arguments (`method`, `level`, `template`, `name`) and the `run_all` helper at `src/tests/test_selective.py:20`
- [ ] Run `ruff check && ruff format --check`

**Acceptance Criteria:**

- [ ] An AST walk over `src/tests/` reports zero signatures missing parameter or return annotations
- [ ] `pytest -m "not slow"` and `pytest -m slow` both pass

**Notes:**

- Depends on Task 6 (`typing` import placement convention)
- Full location list is in review-1's S1 block; the count is 62 across six test files and three emitters
- Mechanical change - a good candidate to do in one pass per file

---

## Task 9: Consolidate sink registration in `setup_logger`

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Findings "duplicated sink format strings" (A15) and "unguarded sink registration in `setup_logger`" (A1)

**Technical Goal:** stop the three sink format strings from drifting, and make sink registration atomic - a failure part-way through must not leave earlier sinks installed.

**Subtasks:**

- [ ] Hoist the shared record format (`'{time:YYYY-MM-DDTHH:mm:ss!UTC} {level: <8} {file}:{line}/{function} {message}'`) to a module-level constant and derive the stderr variant (colour tags plus process/thread fields) from it
- [ ] Collect the id returned by each `logger.add(...)` as it succeeds
- [ ] Wrap the three registrations so that on `OSError` every already-registered id is passed to `logger.remove(id)` before the exception is re-raised
- [ ] Make the rollback tolerant of a sink that is already gone, so a failure during cleanup cannot mask the original error
- [ ] Add a test using an unwritable directory asserting that `setup_logger` raises and that no sinks remain registered afterwards

**Acceptance Criteria:**

- [ ] Adding a field to the shared format changes both the text and jsonl sinks
- [ ] A mid-sequence `OSError` leaves zero sinks registered and re-raises the original exception
- [ ] `pytest src/tests/test_sinks.py` passes (the format assertions there pin the current layout)

**Notes:**

- Key file: `src/logit/base.py:220-237`
- Rollback must not touch sinks registered before `setup_logger` was called; note that line 212 already calls `logger.remove()` unconditionally at the top, so the only ids in play are the ones this call created
- Use `os.access` or a `chmod 0o500` `tmp_path` subdirectory for the failure test, and skip it when running as root
- Loguru does create missing parent directories (verified during the audit), so the fresh-clone case is already safe - this is only about permission/EISDIR failures
- `src/tests/test_sinks.py:24-27` asserts on the exact `file:line/function` layout, so keep the format text identical

---

## Task 10: Clear the remaining mechanical hits

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Mechanical rules `stdlib-logging`, `in-function-import`, `non-alphabetical-literal`, `legacy-formatting-format`; Finding "empty `tests/emitters/__init__.py`" (A17)

**Technical Goal:** take the audit script's unaccepted hit count to zero, so the next run is a clean baseline.

**Subtasks:**

- [ ] Hoist `import linecache` from `src/logit/base.py:58` into the module import block
- [ ] Sort `src/logit/__init__.py:3` to `['StreamToLogger', 'jsonl_file', 'log_file', 'reset', 'setup_logger', 'showwarning']` (`log_dir` is removed by Task 11)
- [ ] Add `# auditme: accept interceptor must import stdlib logging` above `src/logit/base.py:2`
- [ ] Add `# auditme: accept emitter modules exist to be addressed by dotted name` to `src/tests/emitters/__init__.py`
- [ ] Re-run `python3 ~/.claude/skills/auditme/checks/audit.py . --package logit` and confirm every remaining hit is `accepted: true`

**Acceptance Criteria:**

- [ ] The audit script reports zero `accepted: false` hits
- [ ] `pytest -m "not slow"` passes
- [ ] `ruff check` is clean

**Notes:**

- Depends on Tasks 2, 3, 4 and 11 - those remove the `legacy-formatting-format`, `silent-broad-except`, `leading-underscore-*` and (possibly) `non-alphabetical-literal` hits at source, so this task only mops up what is genuinely intentional
- The script scans `src/logit/` only; the emitters marker is for Phase B, not the script
- This is the convergence gate: review-2 on unchanged code should report the same finding set as review-1 minus everything fixed here

---

## Task 11: Drop `log_dir` from the public surface

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Finding "`log_dir` exported but unused" (A17)

**Technical Goal:** stop exporting a helper that has no consumer outside the package and whose default path is fragile for anyone but this repo.

**Subtasks:**

- [ ] Remove `log_dir` from `__all__` and from the re-export at `src/logit/__init__.py:1`
- [ ] Keep `log_dir` in `src/logit/base.py:176` - `log_file` and `jsonl_file` still call it for their default
- [ ] Confirm `log_file`/`jsonl_file` cover every external need (`src/tests/test_sinks.py:55-56` and `src/tests/fixtures/base.py:30,55` are the only consumers)
- [ ] Grep `src/` and `bin/` for `logit.log_dir` to confirm nothing breaks

**Acceptance Criteria:**

- [ ] Every symbol in `__all__` has at least one consumer outside `src/logit/`
- [ ] `grep -rn "logit.log_dir\|log_dir" src bin` matches only `src/logit/base.py`
- [ ] `pytest -m "not slow"` passes

**Notes:**

- Blocks Task 10's `__all__` sort - the sorted list becomes `['StreamToLogger', 'jsonl_file', 'log_file', 'reset', 'setup_logger', 'showwarning']`
- The default path `pathlib.Path(__file__).parent.parent.parent / 'log'` resolves relative to the *installed* package; keeping it private means a consumer who needs a different location passes `directory=` instead

---

## Task 12: Cache parsed records in `LogCapture`

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Finding "`LogCapture` re-reads and re-parses the sink on every accessor" (A14 / P3)

**Technical Goal:** stop re-reading and re-parsing the jsonl sink once per accessor call.

**Subtasks:**

- [ ] Cache the parsed record list on the `LogCapture` instance, invalidated whenever `complete()` runs or new records may have been written
- [ ] Make `find()` reuse the list it already loaded for its assertion message instead of calling `messages()` (which re-parses)
- [ ] Verify the cache cannot mask records written between two assertions in the same test

**Acceptance Criteria:**

- [ ] A test calling `find()` five times parses the file once
- [ ] `pytest -m "not slow"` and `pytest -m slow` both pass unchanged

**Notes:**

- Key file: `src/tests/fixtures/base.py:24-51`
- `src/tests/test_sinks.py:35-38` is the worst case: five `find()` calls, so five full parses
- Correctness beats speed here - if a safe invalidation rule is not obvious, cache only within a single accessor call (fixing `find()`) and leave `records()` alone

---

## Task 13: Fix dependency placement and add a property test

**Status:** todo
**Priority:** low
**Complexity:** small
**Source Reference:** Findings "`joblib` declared as a runtime dependency" (D2) and "no property-based tests" (T2)

**Technical Goal:** stop shipping a test-only dependency to consumers, and cover `StreamToLogger.write` over its whole input domain.

**Subtasks:**

- [ ] `uv remove joblib && uv add --dev joblib` (only `src/tests/test_concurrency.py` and `bin/demo-logging.py` import it)
- [ ] `uv add --dev hypothesis`
- [ ] Add a property test in `src/tests/test_streams.py` over arbitrary text asserting the invariant: emitted messages equal `[line.rstrip() for line in buffer.rstrip().splitlines()]`
- [ ] Give it `@settings(max_examples=20, deadline=10000)` as the testing standard requires

**Acceptance Criteria:**

- [ ] `logit`'s runtime dependency list is `["loguru"]`
- [ ] `pytest src/tests/test_streams.py` passes, including the property test
- [ ] `uv.lock` is regenerated by `uv`, not hand-edited

**Notes:**

- `bin/demo-logging.py` imports joblib, so the demo needs the dev group installed - note that in the README (Task 14)
- The existing literal-based tests at `src/tests/test_streams.py:64-92` stay; the property test generalises them

---

## Task 14: Bring the documentation in line with the code

**Status:** todo
**Priority:** medium
**Complexity:** medium
**Source Reference:** Findings "README does not describe the project or its API" (Doc3) and "AGENTS.md structure and library gaps" (Doc1 / Doc2)

**Technical Goal:** one agreed description of the project, and a README that documents the public API for a human reader.

**Subtasks:**

- [ ] Settle one description and propagate it to `README.md:3`, `AGENTS.md:3` and `pyproject.toml:4` (currently "A test of using loguru for logging" / "A loguru wrapper" / "Testing loguru and logging")
- [ ] Add a README usage section: install, `logit.setup_logger(directory=..., stderr=..., disabled=[...], subprocess=...)`, what each of the three sinks contains and where it lands, the `disabled` mechanism, `StreamToLogger` for `print()` capture, and `reset()`
- [ ] Document the `subprocess=True` per-pid file mode and when to use it
- [ ] Mention `bin/demo-logging.sh` and how to run it (including the dev-group dependency on joblib)
- [ ] Add `src/logit/__init__.py` and `src/tests/conftest.py` to AGENTS.md's Module Structure list
- [ ] Add a short "Tools and libraries" section to AGENTS.md naming loguru, joblib, pytest and uv
- [ ] Keep to ASCII punctuation per the markdown rules

**Acceptance Criteria:**

- [ ] All three description strings agree
- [ ] Every symbol in `logit.__all__` appears in the README
- [ ] AGENTS.md's Module Structure list matches `find src bin -name '*.py'`
- [ ] `pre-commit run --all-files` passes

**Notes:**

- Depends on Tasks 1, 11 and 13 - the README should document the corrected `disabled` semantics, the final `__all__`, and the final dependency groups
- Do this last so it documents the shipped state rather than the current one

---
