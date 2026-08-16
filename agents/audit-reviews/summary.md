# Audit Summary

**Last updated:** 2026-08-04
**Last review:** review-1
**Total reviews conducted:** 1
**Last script run hit count:** 9 (0 accepted)
**Script version:** ~/.claude/skills/auditme/checks/audit.py, unmodified during review-1

## Unresolved findings

### `disabled` state diverges across repeated `setup_logger` calls

- **Rule or category:** A5
- **Severity:** high
- **Location:** `src/logit/base.py:239-241`
- **First raised:** review-1 (2026-08-04)
- **Description:** `setup_logger` never re-enables names disabled by a previous call, so loguru silences the union of every `disabled` list ever passed while the stdlib-logging and warnings mechanisms track only the newest list.
- **Recommendation:** drain `disabled_` at the top of `setup_logger` before applying the new list; add a regression test across all five capture paths.

### Dead `LoguruHandler` class

- **Rule or category:** T1
- **Severity:** medium
- **Location:** `src/logit/base.py:77-79`
- **First raised:** review-1 (2026-08-04)
- **Description:** never instantiated, referenced, exported or tested; also carries the only `legacy-formatting-format` mechanical hit.
- **Recommendation:** delete it.

### Leading-underscore attribute `StreamToLogger._level`

- **Rule or category:** `leading-underscore-self` / `leading-underscore-attribute-access`
- **Severity:** medium
- **Location:** `src/logit/base.py:148,152`
- **First raised:** review-1 (2026-08-04)
- **Description:** violates the no-leading-underscores rule in the Python coding standard.
- **Recommendation:** rename to `level`.

### Silent broad `except` around `linecache.getline`

- **Rule or category:** `silent-broad-except` / A19
- **Severity:** medium
- **Location:** `src/logit/base.py:61`
- **First raised:** review-1 (2026-08-04)
- **Description:** `except Exception:` with no log and no re-raise, plus a dead `linecache = None` rebind.
- **Recommendation:** narrow to `except OSError:`, drop the rebind, log at debug.

### Missing type annotations

- **Rule or category:** S1
- **Severity:** medium
- **Location:** 70 signatures; package code at `src/logit/base.py:46,78,147,150,154`
- **First raised:** review-1 (2026-08-04)
- **Description:** the standard requires parameter and return annotations everywhere, including explicit `-> None`.
- **Recommendation:** annotate the package and `bin/` first, then emitters and tests.

### `from loguru import logger` violates the full-import-path rule

- **Rule or category:** S4
- **Severity:** medium
- **Location:** `src/logit/base.py:11`
- **First raised:** review-1 (2026-08-04)
- **Description:** only file in the tree using `from X import Y` outside an `__init__.py` re-export.
- **Recommendation:** use `import loguru` and qualify the 12 uses.

### README does not describe the project or its API

- **Rule or category:** Doc3
- **Severity:** medium
- **Location:** `README.md:1-3`
- **First raised:** review-1 (2026-08-04)
- **Description:** three lines, a description that disagrees with AGENTS.md and `pyproject.toml`, and no usage documentation for any exported symbol.
- **Recommendation:** one agreed description plus a usage section.

### Unaccepted mechanical hits needing accept markers

- **Rule or category:** `stdlib-logging`, `legacy-formatting-format`, `in-function-import`, `non-alphabetical-literal`
- **Severity:** low
- **Location:** `src/logit/base.py:2,58,79`; `src/logit/__init__.py:3`
- **First raised:** review-1 (2026-08-04)
- **Description:** the stdlib logging import is inherent to an interceptor; `self.format(record)` is `logging.Handler.format`, not `str.format`; `import linecache` is a stdlib deferred import with no benefit; `__all__` is unsorted.
- **Recommendation:** add `# auditme: accept ...` markers for the first two, hoist `linecache`, sort `__all__`.

### Low-severity remainder

- **Rule or category:** A1, A15, A14/P3, A17, T2, D2, Doc1/Doc2
- **Severity:** low
- **Location:** `src/logit/base.py:220,226,232` (unguarded sink registration); `:222,228,234` (duplicated format strings); `src/tests/fixtures/base.py:28-51` (records re-parsed per accessor); `src/logit/__init__.py:1,3` (`log_dir` exported but unused); `src/tests/emitters/__init__.py:1` (needs accept marker); `src/tests/test_streams.py` (no property tests); `pyproject.toml:7` (`joblib` in runtime deps); `AGENTS.md` (structure and libraries gaps)
- **First raised:** review-1 (2026-08-04)
- **Description:** see review-1 for the individual entries.
- **Recommendation:** see review-1. Two open options were settled by the user on 2026-08-04: A1 is fixed by rolling back registered sinks on failure (not by documenting the non-atomicity), and A17's `log_dir` is dropped from `__all__` (not kept and tested). Planned in `agents/tasks/audit-reviews/tasks-1.md` Tasks 9 and 11.

## Recently resolved

| Finding | Severity | Raised in | Resolved in |
|---------|----------|-----------|-------------|
| (none yet) | | | |

## Recurring patterns

- (none yet - first review)

## Script coverage backlog

- (empty)

## Checker changes since review-1

- **`translator-envelope-gap`** (2026-08-16) - a function whose only error
  envelope is a translating decorator or a `with` block over a translating
  contextmanager, where that envelope's except tuple omits a branch of A2's
  locked set the body triggers. Shipped from the skill's `requests.md`.
  Catch-up surface here: **zero**.
