# Audit Review 1

**Date:** 2026-08-04
**Scope:** full (`src/logit/`, `src/tests/`, `bin/`, `AGENTS.md`, `README.md`, `pyproject.toml`)
**Script output:** /tmp/audit-logit.jsonl (9 hits, 0 accepted, 9 unaccepted)
**Convergence note:** first review for this project. `checks/audit.py` was run unmodified and no check was added during the audit. No `agents/audit-reviews/summary.md` existed at start, so the script-coverage backlog was empty by construction.

**Phase B execution note:** the checklist was applied per-question across all 15 Python files in scope, inline rather than via subagent fan-out (this session is configured not to spawn agents). The corpus is ~800 lines and was held in full context for every predicate, so the per-question determinism guarantee is preserved; only the parallelism differs.

## Summary

The mechanical sweep returned 9 unaccepted hits, all in `src/logit/` (the script scans the package only): 4 for leading-underscore attributes, and one each for the stdlib `logging` import, a `.format()` false positive, an in-function import, a silent broad `except`, and an unsorted `__all__`. Phase B produced 14 findings. The most significant is a genuine state bug: calling `setup_logger()` twice with different `disabled` lists leaves the first list permanently silenced in loguru while the stdlib-logging and warnings mechanisms are rebuilt from the new list only, so the three suppression paths diverge (verified empirically). Secondary themes are missing type annotations across the whole tree, one dead class (`LoguruHandler`), and thin user-facing documentation.

## Mechanical findings (from checks/audit.py)

### Rule: `stdlib-logging` - stdlib logging import

- **Severity:** low
- **Instance count:** 1
- **Locations:**
  - `src/logit/base.py:2` - `import logging`
- **Recommendation:** this package exists to intercept stdlib logging, so the import is unavoidable. Add `# auditme: accept interceptor must import stdlib logging` above the line. The same applies to `logging.config` on line 3 if the script is later widened.

### Rule: `legacy-formatting-format` - `.format()` call

- **Severity:** low
- **Instance count:** 1
- **Locations:**
  - `src/logit/base.py:79` - `logger.log(record.levelname, self.format(record))`
- **Recommendation:** false positive - this is `logging.Handler.format(record)`, not `str.format()`. Add `# auditme: accept logging.Handler.format, not str.format`. Note this line lives in `LoguruHandler`, which is dead code (see finding "Dead `LoguruHandler` class"); deleting the class also removes this hit.

### Rule: `leading-underscore-self` / `leading-underscore-attribute-access` - `self._attr`

- **Severity:** medium
- **Instance count:** 4 (2 lines x 2 rules)
- **Locations:**
  - `src/logit/base.py:148` - `self._level = level`
  - `src/logit/base.py:152` - `logger.opt(depth=1).log(self._level, line.rstrip())`
- **Recommendation:** the coding standard is explicit that leading underscores are not an accepted privacy convention. Rename `StreamToLogger._level` to `level`. No external consumer reads it (grep confirms `_level` appears only in these two lines).

### Rule: `in-function-import` - third-party

- **Severity:** low
- **Instance count:** 1
- **Locations:**
  - `src/logit/base.py:58` - `import linecache`
- **Recommendation:** `linecache` is stdlib and cheap; the deferred import is copied from CPython's `warnings.py` but has no benefit here. Hoist it to the module import block. If kept, it needs an accept marker plus an AGENTS.md row.

### Rule: `silent-broad-except` - no logger and no raise in body

- **Severity:** medium
- **Instance count:** 1
- **Locations:**
  - `src/logit/base.py:61` - `except Exception:`
- **Recommendation:** the body only reachable failure is `linecache.getline` hitting an unreadable path, which raises `OSError`. Narrow to `except OSError:` and drop the `linecache = None` assignment (it rebinds a name that is never read again). A swallowed `MemoryError`/`KeyboardInterrupt` here would currently be invisible.

### Rule: `non-alphabetical-literal` - string members not alphabetically sorted

- **Severity:** low
- **Instance count:** 1
- **Locations:**
  - `src/logit/__init__.py:3` - `['setup_logger', 'StreamToLogger', 'reset', 'showwarning', 'log_file', 'jsonl_file', 'log_dir']`
- **Recommendation:** sort: `['StreamToLogger', 'jsonl_file', 'log_dir', 'log_file', 'reset', 'setup_logger', 'showwarning']`.

## Phase B per-question results

Files in scope for every question (15): `src/logit/__init__.py`, `src/logit/base.py`, `src/tests/conftest.py`, `src/tests/fixtures/base.py`, `src/tests/emitters/{__init__,some_lib,unwanted,wanted}.py`, `src/tests/test_{sinks,intercept,streams,warnings,selective,concurrency}.py`, `bin/demo-logging.py`.

### A1: External call envelope

- **Hits:**
  - `src/logit/base.py:220`, `:226`, `:232` - the three `logger.add(...)` sink registrations open files/streams; any `OSError` (unwritable directory, path is a directory) escapes `setup_logger` as a raw loguru/stdlib exception. The package defines no domain `*Error` class to translate to.
- **No-hit confirmation:** 14 other files inspected; `linecache.getline` (base.py:60) is already enveloped; test/demo file I/O is test-harness code with no domain layer.
- **Verified:** loguru's file sink creates missing parent directories (checked against the installed version), so the common "fresh clone has no `log/`" case does not fail.

### A2: Except tuple coverage

- **Hits:** none. The only `try/except` touching disk (`base.py:57-63`) uses bare `Exception`, which satisfies the predicate.

### A3: Domain-error layering

- **Hits:** none. The package defines no `*Error` class, so the predicate does not fire. (`AssertionError` at `src/tests/fixtures/base.py:44` is test-harness signalling.)

### A4: Docstring `Raises` accuracy

- **Hits:** none. No docstring in the tree has a `Raises:` section.

### A5: Two sources of truth

- **Hits:**
  - `src/logit/base.py:239-241` vs `:164` and `:143` - the `disabled` argument feeds three mechanisms, but only the loguru one accumulates into the module-level `disabled_` list and is never undone by a subsequent `setup_logger`. `setup_warnings` calls `warnings.resetwarnings()` and `config_logger_default` rebuilds the whole dictConfig, so both of those reflect only the newest list, while loguru reflects the union of every list ever passed.
- **Verification:** `setup_logger(disabled=['tests.emitters.wanted'])` followed by `setup_logger(disabled=['tests.emitters.unwanted'])` then emitting from both modules produces zero records - `wanted` is still disabled in loguru. Expected: only `unwanted` silenced.

### A6: Stage method dual-path

- **Hits:** none. No pipeline-stage classes exist.

### A7: Constructor purity

- **Hits:** none. `StreamToLogger.__init__` (base.py:147) and `LogCapture.__init__` (fixtures/base.py:19) only assign; neither does I/O nor mutates its arguments.

### A8: Late dataclass mutation

- **Hits:** none. No `@dataclass` in the tree.

### A9: Pure-named function side effects

- **Hits:** none. No function name in the tree starts with a prefix from the locked set (`get_`, `resolve_`, `find_`, `compute_`, `build_`, `load_`, `parse_`, `is_`, `has_`, `validate_`, `count_`, `check_`, `allocate_`).

### A10: Predicate semantics

- **Hits:** none. No `is_X` / `has_X` / `should_X` functions.

### A11: Exhaustion via `assert_never`

- **Hits:** none. No `if/elif/else` chain over a `Literal` or enum.

### A12: `assert` misuse

- **Hits:** none. No `assert` statements outside `src/tests/`.

### A13: Same value to multiple structural slots

- **Hits:** none. No constructor call passes one value to two distinguishable slots.

### A14: Repeated computation per request

- **Hits:**
  - `src/tests/fixtures/base.py:28-51` - `LogCapture.records()` re-opens and re-parses the whole jsonl file on every call, and `messages()`, `names()`, `find()`, `matching()`, `from_module()` all route through it. `src/tests/test_sinks.py:35-38` calls `find()` five times in one test, i.e. five full read-and-parse passes; `find()`'s failure path (line 44) parses a sixth time.
- **No-hit confirmation:** `log_dir()`/`this_dir()` are reached at most twice per `setup_logger` call, below the "more than twice" threshold.

### A15: Duplicate constructor / serialisation logic

- **Hits:**
  - `src/logit/base.py:228` and `:234` - the file and jsonl sinks are registered with byte-identical `format=` strings, and `:222` differs only by the `<level>` colour tags and the process/thread fields. A field added to one will silently not appear in the others.

### A16: CLI entry envelope

- **Hits:** none. There is no `src/logit/cli/` and no `run_*` entry point; `bin/demo-logging.py:85 main()` is outside the predicate's enumeration.

### A17: Public-surface drift

- **Hits:**
  - `src/logit/__init__.py:3` - `log_dir` is exported in `__all__` but has no consumer outside `src/logit/base.py` (grep across `src/` and `bin/` confirms).
  - `src/tests/emitters/__init__.py:1` - empty `__init__.py` whose consumers (`test_selective.py:5-7`, `bin/demo-logging.py:17-19`) import submodules directly.
- **Note on the second hit:** module identity is the whole point of the emitter package - the tests assert on `record['name'] == 'tests.emitters.wanted'` - so this is very likely a deliberate design. It still needs an explicit accept marker to stop recurring.

### A18: Hot-path setup

- **Hits:** none. No method in the tree is named `on_step` / `on_log` / `on_evaluate` / `on_batch_*`.

### A19: Wrong logger level for broad-except

- **Hits:** none. The one broad `except` (base.py:61) logs nothing at all, which is the `silent-broad-except` mechanical rule rather than this predicate. `logger.exception` uses in the emitter modules sit under narrow `except ValueError`.

### A20: Mutable module-level singleton

- **Hits:** none. `disabled_` (base.py:17) is a mutable module-level list, but grep confirms no other module imports it by name (it is not in `__all__` and not referenced outside `base.py`), so the predicate's "imported elsewhere" condition is not met. `EMITTERS` (test_selective.py:13), `LEVELS`, `PATHS`, `DISABLED` are likewise not imported elsewhere.

### A21: Lazy init race

- **Hits:** none. No `if X is None: X = ...` pattern at module scope or in a module-level helper.

### A22: Fall-through after partial handling

- **Hits:** none. No `if/else` chain in the tree mixes raising and returning branches.

### A23: Discarded multi-return

- **Hits:** none. No call to a tuple- or dataclass-returning function discards components. (`joblib.Parallel(...)(...)` at `bin/demo-logging.py:60` and `test_concurrency.py:92` returns a list, outside the predicate.)

### A24: Identity of subprocess / shell-out calls

- **Hits:** none. No `subprocess.run` or git shell-out anywhere in the tree.

### S1: Type annotations on every signature

- **Hits:** 70 signatures across 12 files (full enumeration via AST walk):
  - `src/logit/base.py:46` `showwarning` - all 6 params and return
  - `src/logit/base.py:78` `LoguruHandler.emit` - `record`, return
  - `src/logit/base.py:147` `StreamToLogger.__init__` - `level`, return
  - `src/logit/base.py:150` `StreamToLogger.write` - `buffer`, return
  - `src/logit/base.py:154` `StreamToLogger.flush` - return
  - `bin/demo-logging.py:24,42,49,58,63,74,85` - return on all 7
  - `src/tests/emitters/{some_lib,unwanted,wanted}.py:8` `func` - return
  - `src/tests/test_concurrency.py:40,58,72,91,102`
  - `src/tests/test_intercept.py:18,25,33,46,54,68,78,85`
  - `src/tests/test_selective.py:20,26,35,55,65,80,88,95,102`
  - `src/tests/test_sinks.py:8,16,30,41,49,63`
  - `src/tests/test_streams.py:8,16,24,34,43,53,64,71,79,88,95,101`
  - `src/tests/test_warnings.py:8,15,26,32,41,48,54,64,75,82,89,98,104`
- **No-hit confirmation:** `src/tests/conftest.py` and `src/tests/fixtures/base.py` are fully annotated; `src/logit/base.py` functions other than the five listed are annotated.

### S2: Naming conventions

- **Hits:** none beyond the mechanical `leading-underscore-self` hits. Classes are PascalCase, module-level constants are UPPER_SNAKE, functions/modules are snake_case, and `bin/` script names use dashes as required.

### S3: TYPE_CHECKING block placement

- **Hits:** none - the tree contains no `if typing.TYPE_CHECKING:` block. The related rule violation (imports needed only for annotations) is reported under S4.

### S4: Project-specific rule files

Rules checked: `python/coding-standards.md`, `python/testing.md`, `python/dependencies.md`, `python/logging.md`, `python/utilities.md`, `python/environment.md`, `markdown.md`, `security.md`.

- **Hits:**
  - `src/logit/base.py:11` - `from loguru import logger` violates "Always use full import paths - no `from X import Y` in internal code". Every other file in the tree uses `import loguru` / `loguru.logger`; `base.py` is the sole outlier, and the `__init__.py` re-export exemption does not cover it.
  - `src/logit/base.py:8` - `typing` is imported at module level but used only in the `stderr: typing.TextIO | None` annotation; the rule requires annotation-only imports to sit in a `typing.TYPE_CHECKING` block.
  - `src/tests/conftest.py:3,5` - `pathlib` and `typing` are used only in annotations.
  - `src/tests/fixtures/base.py:4,5` - `pathlib` and `typing` are used only in annotations (`io` is used at runtime, so it stays).
- **No-hit confirmation:** no `from __future__ import annotations`, no `as` imports, no wildcard imports, no `%`-formatting or `.format()` in string construction, no `pip install` in scripts, `bin/` wrapper scripts exist for every `bin/*.py`, `uv.lock` is committed and coherent.

### P1: O(n^2) on real-size inputs

- **Hits:** none. The only nested loop (`StreamToLogger.write` over `splitlines`) is linear.

### P2: Blocking I/O in hot paths

- **Hits:** none. All three sinks use `enqueue=True`, so record writes happen off the calling thread. `linecache.getline` reads the source file on the warning path but caches per file.

### P3: Repeated expensive computation per request

- **Hits:** same as A14 - `src/tests/fixtures/base.py:28` `LogCapture.records()`.

### Sec1: Secrets in source

- **Hits:** none.

### Sec2: Input validation at system boundaries

- **Hits:** none. `bin/demo-logging.py` takes no arguments (`demo-logging.sh` forwards `"$@"`, which the script ignores); `setup_logger(directory=...)` is a library parameter, not an external boundary.

### Sec3: Command injection

- **Hits:** none. No `subprocess` or shell execution.

### Sec4: Path traversal

- **Hits:** none. `log_file`/`jsonl_file` join a caller-supplied directory with a fixed basename; the only interpolated component is `os.getpid()`.

### Sec5: PII in logs

- **Hits:** none in this package's own logging. (Callers who route `print()` into `StreamToLogger` inherit responsibility for what they print; that is out of the predicate's scope.)

### T1: Test coverage of branchy logic

- **Hits:**
  - `src/logit/base.py:77-79` - `LoguruHandler` has no test and, more importantly, no call site: the dictConfig at `:121` wires `InterceptHandler`, and `LoguruHandler` is not exported in `__all__` or referenced anywhere in `src/` or `bin/`. It is dead code.
  - `src/logit/base.py:194-202` - `reset()`'s `disabled_` drain is untested, and the `setup_logger` -> `setup_logger` state transition (the A5 bug) has no test at all.
  - `src/logit/base.py:56` - the `filename != 'sys'` branch of the source-line lookup is never exercised.
  - `src/logit/base.py:61` - the `except` path around `linecache.getline` is never exercised.
  - `src/logit/base.py:40-42` - the `hook is None` fallback in `internal_files()` is never exercised.
- **No-hit confirmation:** `InterceptHandler.emit` is fully covered (level mapping, numeric fallback, frame depth, `exc_info`); all five capture paths and both `subprocess` modes have tests; `StreamToLogger.write` covers empty, whitespace, multiline and trailing-whitespace inputs.

### T2: Property-based tests

- **Hits:**
  - `src/tests/test_streams.py` - `StreamToLogger.write` maps arbitrary text to a list of stripped lines, a well-defined domain, and is tested only with hand-picked literals. No `hypothesis` test exists anywhere in the suite, and `hypothesis` is not a declared dependency.

### T3: Integration vs unit balance

- **Hits:** none. `setup_logger` is exercised end-to-end by `test_sinks.py` and across processes by `test_concurrency.py`.

### D1: Declared in pyproject

- **Hits:** none. `loguru`, `joblib` and `pytest` are the only third-party imports and all are declared.

### D2: Unused declarations

- **Hits:**
  - `pyproject.toml:7` - `joblib` is declared as a runtime dependency of the `logit` package, but nothing under `src/logit/` imports it; the only importers are `src/tests/test_concurrency.py` and `bin/demo-logging.py`. It belongs in the `dev` dependency group.

### D3: Lockfile coherence

- **Hits:** none. The script's lockfile check produced no hit.

### Doc1: AGENTS.md project structure matches layout

- **Hits:**
  - `AGENTS.md` "Module Structure" section - omits `src/logit/__init__.py` (the public API surface, and the file that defines `__all__`) and `src/tests/conftest.py` (mentioned in prose under Tests but not in the structure list).

### Doc2: AGENTS.md tools and libraries list is current

- **Hits:**
  - `AGENTS.md` - has no tools/libraries section at all, and `joblib` (a declared dependency, exercised by `test_concurrency.py` and `bin/demo-logging.py`) is never mentioned.

### Doc3: README.md and AGENTS.md consistent

- **Hits:**
  - `README.md:3` - describes the project as "A test of using loguru for logging"; `AGENTS.md:3` says "A loguru wrapper"; `pyproject.toml:4` says "Testing loguru and logging". Three different framings.
  - `README.md` - documents none of the public API (`setup_logger`, `StreamToLogger`, `reset`, `log_file`, `jsonl_file`, `showwarning`), gives no install or usage instructions, and does not mention `bin/demo-logging.sh`.

### Doc4: Specs match implementation

- **Not applicable:** there is no `agents/specs/` directory; no specs are in scope. Step 5 (spec review) was skipped for the same reason.

### Doc5: User docs match implementation

- **Not applicable:** there is no `docs/` directory.

## Phase B findings (consolidated)

### Finding: `disabled` state diverges across repeated `setup_logger` calls

- **Category:** A
- **Question:** A5
- **Severity:** high
- **Location:** `src/logit/base.py:239-241`
- **Description:** `setup_logger` appends every disabled name to the module-level `disabled_` list and calls `logger.disable(name)`, but never re-enables names from a previous call. `config_logger_default` rebuilds the entire stdlib dictConfig and `setup_warnings` calls `warnings.resetwarnings()`, so those two mechanisms track only the latest `disabled` list. After two calls with different lists, loguru silences the union while stdlib logging and warnings silence only the newest set - the three mechanisms AGENTS.md describes as equivalent no longer agree. Verified: two successive calls disabling `wanted` then `unwanted` leave both modules producing zero records.
- **Recommendation:** drain `disabled_` (re-enabling each name) at the top of `setup_logger`, the way `reset()` does, before applying the new list. Add a regression test asserting that a second `setup_logger` with a different list re-enables the previously disabled module across all five capture paths.

### Finding: dead `LoguruHandler` class

- **Category:** T
- **Question:** T1
- **Severity:** medium
- **Location:** `src/logit/base.py:77-79`
- **Description:** `LoguruHandler` is never instantiated, never referenced by the dictConfig (which uses `InterceptHandler`), never exported and never tested. It also carries the only `legacy-formatting-format` mechanical hit. Unlike `InterceptHandler` it does no frame-depth tracking, so if it were ever wired in, every record would be attributed to `base.py`.
- **Recommendation:** delete the class. If it is being kept as a documented alternative, move it to the demo or add a docstring plus a test.

### Finding: missing type annotations across the tree

- **Category:** S
- **Question:** S1
- **Severity:** medium
- **Location:** 70 signatures; see the S1 block for the full list. Package code: `src/logit/base.py:46,78,147,150,154`.
- **Description:** the coding standard requires parameter and return annotations on all signatures, including an explicit `-> None`. The five package-level gaps matter most: `showwarning` is a public, exported symbol whose signature must mirror `warnings.showwarning`, and `StreamToLogger.write`/`flush` form the file-like protocol that `contextlib.redirect_stdout` relies on.
- **Recommendation:** annotate `src/logit/base.py` and `bin/demo-logging.py` first, then the emitters and tests (`capture` and `setup` fixtures are typed in `conftest.py` already, so the fixture parameter types can be copied from there).

### Finding: `from loguru import logger` violates the full-import-path rule

- **Category:** S
- **Question:** S4
- **Severity:** medium
- **Location:** `src/logit/base.py:11`
- **Description:** the standard forbids `from X import Y` outside `__init__.py` re-export lists. Every other file in the repo uses `import loguru` and `loguru.logger`, so `base.py` is the only inconsistent file; a reader cannot tell from `logger.add(...)` in `setup_logger` whether `logger` is loguru's or a stdlib logger - which is exactly the ambiguity this codebase is about.
- **Recommendation:** switch to `import loguru` and qualify all 12 uses as `loguru.logger`.

### Finding: annotation-only imports outside TYPE_CHECKING

- **Category:** S
- **Question:** S4
- **Severity:** low
- **Location:** `src/logit/base.py:8`, `src/tests/conftest.py:3,5`, `src/tests/fixtures/base.py:4,5`
- **Description:** `typing` and `pathlib` are imported at module scope but referenced only inside annotations, which Python 3.14 evaluates lazily. The standard requires such imports to move into an `if typing.TYPE_CHECKING:` block.
- **Recommendation:** move them; keep `io` in `fixtures/base.py` (used at runtime) and `pathlib` in `base.py` (used at runtime by `this_dir`).

### Finding: silent broad `except` around `linecache.getline`

- **Category:** A
- **Question:** mechanical `silent-broad-except`, corroborated by A19
- **Severity:** medium
- **Location:** `src/logit/base.py:61`
- **Description:** `except Exception:` swallows every failure of the source-line lookup with no log line and no re-raise, and additionally rebinds `linecache = None`, a name never read again. The only expected failure is an unreadable path (`OSError`).
- **Recommendation:** narrow to `except OSError:`, drop the `linecache = None` assignment, and consider `logger.debug` on the failure so a silently missing source line is diagnosable.

### Finding: unguarded sink registration in `setup_logger`

- **Category:** A
- **Question:** A1
- **Severity:** low
- **Location:** `src/logit/base.py:220,226,232`
- **Description:** the three `logger.add(...)` calls open the stderr stream and two files. A read-only or non-writable `directory` surfaces a raw `OSError` from inside loguru, and because the calls are sequential, a failure on the second sink leaves the first already registered - `setup_logger` is not atomic. Loguru does create missing parent directories (verified), so the common case is safe.
- **Recommendation:** if the package gains a domain error type, wrap the three registrations and translate. At minimum, document that `setup_logger` is not atomic, or capture the sink ids and remove them on failure.

### Finding: duplicated sink format strings

- **Category:** A
- **Question:** A15
- **Severity:** low
- **Location:** `src/logit/base.py:222,228,234`
- **Description:** the file and jsonl sinks share a byte-identical format string and the stderr format differs only by colour tags and the process/thread fields. Adding a field to one sink will silently skip the others.
- **Recommendation:** hoist the shared format to a module-level constant and derive the stderr variant from it.

### Finding: `LogCapture` re-reads and re-parses the sink on every accessor

- **Category:** P
- **Question:** A14 / P3
- **Severity:** low
- **Location:** `src/tests/fixtures/base.py:28-51`
- **Description:** `records()` calls `logger.complete()` and re-parses the whole jsonl file each time; six public accessors route through it. `test_sinks.py:35-38` triggers five full parses in a single test, and `find()`'s assertion message triggers another.
- **Recommendation:** cache the parsed records per `LogCapture` instance, invalidated by `complete()`, or have `find()` reuse the list it already loaded.

### Finding: `log_dir` exported but unused

- **Category:** A
- **Question:** A17
- **Severity:** low
- **Location:** `src/logit/__init__.py:1,3`
- **Description:** `log_dir` is in `__all__` but no code outside `src/logit/base.py` calls it. It also hardcodes `<package parent>/../log`, which resolves relative to the installed package - a fragile default for any consumer that is not this repo.
- **Recommendation:** drop it from `__all__`, or keep it and add a test that pins the documented default location.

### Finding: empty `tests/emitters/__init__.py` with submodule-reaching consumers

- **Category:** A
- **Question:** A17
- **Severity:** low
- **Location:** `src/tests/emitters/__init__.py:1`
- **Description:** the package exports nothing and all five consumers import submodules directly. This is almost certainly deliberate - the tests assert on the dotted module name of each emitter - but nothing records that.
- **Recommendation:** add `# auditme: accept emitter modules exist to be addressed by dotted name` to the file.

### Finding: no property-based tests

- **Category:** T
- **Question:** T2
- **Severity:** low
- **Location:** `src/tests/test_streams.py`
- **Description:** `StreamToLogger.write` has a well-defined input domain (arbitrary text) and a simple invariant (output lines equal `buffer.rstrip().splitlines()` with each line right-stripped, and no empty trailing record). It is currently tested only with hand-picked literals. `hypothesis` is listed in the project's tools file but is not a declared dependency.
- **Recommendation:** add `hypothesis` to the dev group and a single property test over `text` asserting the invariant, with `@settings(max_examples=20, deadline=10000)` as the standard requires.

### Finding: `joblib` declared as a runtime dependency

- **Category:** D
- **Question:** D2
- **Severity:** low
- **Location:** `pyproject.toml:7`
- **Description:** nothing under `src/logit/` imports `joblib`; only `src/tests/test_concurrency.py` and `bin/demo-logging.py` do. Anyone installing `logit` pulls in joblib and its transitive deps for nothing.
- **Recommendation:** `uv remove joblib && uv add --dev joblib`.

### Finding: AGENTS.md structure and library gaps

- **Category:** Doc
- **Question:** Doc1 / Doc2
- **Severity:** low
- **Location:** `AGENTS.md` "Module Structure"
- **Description:** the module list omits `src/logit/__init__.py` (which owns `__all__`) and `src/tests/conftest.py`, and there is no tools/libraries section - `joblib`, used by the concurrency tests and the demo, is never mentioned.
- **Recommendation:** add both files to the structure list and a short "Tools and libraries" section naming loguru, joblib, pytest and uv.

### Finding: README does not describe the project or its API

- **Category:** Doc
- **Question:** Doc3
- **Severity:** medium
- **Location:** `README.md:1-3`
- **Description:** the README is three lines and calls the project "A test of using loguru for logging", while AGENTS.md calls it "A loguru wrapper" and `pyproject.toml` says "Testing loguru and logging". None of the seven exported symbols, the `disabled` mechanism, the three sinks, the `subprocess=True` per-pid mode or `bin/demo-logging.sh` are documented for a human reader.
- **Recommendation:** settle on one description, propagate it to `pyproject.toml` and AGENTS.md, and add a short usage section: install, `logit.setup_logger(...)`, the `disabled` list, the three sink locations, and how to run the demo.

## Files reviewed (Phase B)

Checklist applied to all 15 Python files plus `AGENTS.md`, `README.md`, `pyproject.toml`:

- `src/logit/__init__.py` - A1-A24, S1-S4, P1-P3, Sec1-Sec5, T1-T3, D1-D3
- `src/logit/base.py` - A1-A24, S1-S4, P1-P3, Sec1-Sec5, T1-T3, D1-D3
- `src/tests/conftest.py` - as above
- `src/tests/fixtures/base.py` - as above
- `src/tests/emitters/__init__.py` - as above
- `src/tests/emitters/some_lib.py` - as above
- `src/tests/emitters/unwanted.py` - as above
- `src/tests/emitters/wanted.py` - as above
- `src/tests/test_sinks.py` - as above
- `src/tests/test_intercept.py` - as above
- `src/tests/test_streams.py` - as above
- `src/tests/test_warnings.py` - as above
- `src/tests/test_selective.py` - as above
- `src/tests/test_concurrency.py` - as above
- `bin/demo-logging.py` - as above
- `AGENTS.md`, `README.md`, `pyproject.toml` - Doc1-Doc3, D1-D3

## Prior findings re-verified

None - this is the first review. No `agents/audit-reviews/summary.md` and no `agents/tasks/audit-reviews/` existed at audit start.

## Recommendations

Prioritised by severity:

1. **High** - fix the `disabled` state divergence in `setup_logger` (drain `disabled_` before re-applying) and add the regression test.
2. **Medium** - delete the dead `LoguruHandler`; rename `StreamToLogger._level`; narrow the silent `except Exception`; switch `base.py` to `import loguru`; annotate the five package signatures.
3. **Medium** - rewrite `README.md` with a single project description and a usage section.
4. **Low** - add the six accept markers (stdlib logging import, `Handler.format`, emitters `__init__.py`) or fix the underlying hits; sort `__all__`; hoist `linecache`; hoist the shared sink format; move `joblib` to the dev group; move annotation-only imports into TYPE_CHECKING blocks; cache `LogCapture.records()`; add the hypothesis property test; fill the AGENTS.md gaps.

Doing (1), (2) and the accept markers takes the next run's mechanical hit count to zero and leaves only the documentation and low-severity items.
