# Audit Summary

**Last updated:** 2026-11-21
**Last review:** review-2
**Total reviews conducted:** 2
**Last script run hit count:** 47 (1 accepted)
**Script version:** `e924b332c5c6809821c1635aa7a1d3714064120de0317c733f7f09dfa6b50537` (digest of `find -L ~/.claude/skills/auditme/checks -name '*.py' | sort | xargs cat | shasum -a 256`)

## Unresolved findings

All raised in review-2 (2026-11-21); see review-2 for every location. Answers are collected on the review page named in review-2's header.

### README misstates the `log.log` record format

- **Rule or category:** Doc5
- **Severity:** medium
- **Location:** `README.md:55`
- **First raised:** review-2 (2026-11-21)
- **Description:** says `log.log` matches the stderr format without colour; only stderr carries the process and thread ids.
- **Recommendation:** correct the sentence.

### Sweep hits in tests and `bin/`

- **Rule or category:** `typing-deprecated-alias`, `stdlib-logging`, `except-interpolation`, `literal-duplication`, `bare-parametric-annotation`, `mutable-module-level-exported`, `ruff-version-drift`, `duplicate-side-effect-per-target`
- **Severity:** low
- **Location:** 46 hits, nearly all under `src/tests/`; also `src/logit/base.py:24,25,32`, `bin/demo-logging.py:39`, `.pre-commit-config.yaml:4`
- **First raised:** review-2 (2026-11-21)
- **Description:** first sweep to read `src/tests/` and `bin/`.
- **Recommendation:** fix, or accept with rule-scoped markers, as review-2 lists per rule.

### Small `base.py` fixes

- **Rule or category:** A2, A14, S2, S4
- **Severity:** low
- **Location:** `src/logit/base.py:2,18,40-49,75,84,96-97,287,296-297,308,320,335`
- **First raised:** review-2 (2026-11-21)
- **Description:** except tuples missing `UnicodeDecodeError`/`OSError`, `internal_files()` recomputed per warning, `showwarning_` naming, annotation-only `datetime` import, commented-out code.
- **Recommendation:** see review-2 findings P1, P2, P3, P12, P13, P14.

### AGENTS.md gaps

- **Rule or category:** Doc1, Doc2, Doc3
- **Severity:** low
- **Location:** `AGENTS.md:35-36,73`
- **First raised:** review-2 (2026-11-21)
- **Description:** run-time log files not marked as such; tools list omits hypothesis, ruff and shellcheck.
- **Recommendation:** see review-2 findings P9, P10.

### Decided restructuring

- **Rule or category:** A15, S4
- **Severity:** low
- **Location:** `bin/demo-logging.py:51,87`, `src/tests/fixtures/base.py:85`, `src/tests/conftest.py:16,31,56`, `src/tests/`
- **First raised:** review-2 (2026-11-21)
- **Description:** triplicated stream-redirect code; tests split by capture path; fixtures defined in conftest.
- **Recommendation:** decided 2026-11-21: add `logit.redirect_streams()`; keep the test split and record it in AGENTS.md; move the fixtures to `src/tests/fixtures/base.py`.

A17 (`src/logit/__init__.py`), the six A19 handlers and T1 (`bin/demo-logging.py::log_messages`) were dismissed in the ledger on 2026-11-21.

## Recently resolved

| Finding | Severity | Raised in | Resolved in |
|---------|----------|-----------|-------------|
| `disabled` state diverges across repeated `setup_logger` calls | high | review-1 | review-2 |
| Dead `LoguruHandler` class | medium | review-1 | review-2 |
| Leading-underscore attribute `StreamToLogger._level` | medium | review-1 | review-2 |
| Silent broad `except` around `linecache.getline` | medium | review-1 | review-2 |
| Missing type annotations | medium | review-1 | review-2 |
| `from loguru import logger` violates the full-import-path rule | medium | review-1 | review-2 |
| README does not describe the project or its API | medium | review-1 | review-2 |
| Unaccepted mechanical hits needing accept markers | low | review-1 | review-2 |
| Low-severity remainder (A1, A15, A14/P3, A17, T2, D2) | low | review-1 | review-2 |

## Recurring patterns

- AGENTS.md's tools list falls behind the declared dependencies and hooks (reviews 1, 2)

## Checker changes since the last review

- (none since review-2)
