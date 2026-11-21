import inspect
import typing
import warnings

import logit
import tests.emitters.wanted

if typing.TYPE_CHECKING:
    import collections.abc

    import pytest

    import tests.fixtures.base


def test_warn_produces_a_warning_record(capture: tests.fixtures.base.LogCapture) -> None:
    warnings.warn('deprecated thing', DeprecationWarning, stacklevel=1)

    record = capture.find('DeprecationWarning: deprecated thing')
    assert record['level']['name'] == 'WARNING'


def test_warn_also_logs_the_offending_source_line(capture: tests.fixtures.base.LogCapture) -> None:
    """showwarning pulls the source line from linecache and logs it second."""
    warnings.warn('with source', DeprecationWarning, stacklevel=1)

    messages = capture.messages()
    assert messages[0] == 'DeprecationWarning: with source'
    assert messages[1].strip().startswith("warnings.warn('with source'")
    assert messages[1].startswith('  ')
    assert len(messages) == 2


def test_category_name_prefixes_the_message(capture: tests.fixtures.base.LogCapture) -> None:
    warnings.warn('a user warning', UserWarning, stacklevel=1)

    assert capture.matching('UserWarning: a user warning')


def test_warning_is_attributed_to_the_emitting_module(capture: tests.fixtures.base.LogCapture) -> None:
    tests.emitters.wanted.func()

    record = capture.find('DeprecationWarning: This is a warnings.warn message from wanted.py')
    assert record['name'] == 'tests.emitters.wanted'
    assert record['file']['name'] == 'wanted.py'
    assert record['function'] == 'func'


def test_warning_reaches_all_three_sinks(capture: tests.fixtures.base.LogCapture) -> None:
    warnings.warn('sink check', DeprecationWarning, stacklevel=1)

    assert 'DeprecationWarning: sink check' in capture.text()
    assert 'DeprecationWarning: sink check' in capture.stderr()


def test_direct_showwarning_call_is_logged(capture: tests.fixtures.base.LogCapture) -> None:
    warnings.showwarning('called directly', DeprecationWarning, 'somewhere.py', 12)

    assert capture.find('DeprecationWarning: called directly')


def test_warn_location_is_the_warning_site_not_the_warnings_module(capture: tests.fixtures.base.LogCapture) -> None:
    expected_line = inspect.currentframe().f_lineno + 1
    warnings.warn('locate warn', DeprecationWarning, stacklevel=1)

    record = capture.find('DeprecationWarning: locate warn')
    assert record['file']['name'] == 'test_warnings.py'
    assert record['function'] == 'test_warn_location_is_the_warning_site_not_the_warnings_module'
    assert record['line'] == expected_line


def test_direct_showwarning_location_is_its_caller(capture: tests.fixtures.base.LogCapture) -> None:
    """Regression: finding a source line must not shift the reported frame."""
    expected_line = inspect.currentframe().f_lineno + 1
    warnings.showwarning('locate direct', UserWarning, __file__, expected_line)

    record = capture.find('UserWarning: locate direct')
    assert record['file']['name'] == 'test_warnings.py'
    assert record['function'] == 'test_direct_showwarning_location_is_its_caller'
    assert record['line'] == expected_line


def test_source_line_record_shares_the_message_location(capture: tests.fixtures.base.LogCapture) -> None:
    warnings.warn('paired records', DeprecationWarning, stacklevel=1)

    message, source = capture.records()
    assert (message['file']['name'], message['line']) == (source['file']['name'], source['line'])


def test_direct_showwarning_without_a_real_file_logs_only_the_message(capture: tests.fixtures.base.LogCapture) -> None:
    """linecache returns '' for a path that does not exist, so no source line."""
    warnings.showwarning('no such file', UserWarning, 'does-not-exist.py', 99)

    assert capture.messages() == ['UserWarning: no such file']


def test_direct_showwarning_on_a_real_file_appends_the_source_line(capture: tests.fixtures.base.LogCapture) -> None:
    path = tests.emitters.wanted.__file__
    warnings.showwarning('real file', UserWarning, path, 1)

    messages = capture.messages()
    assert messages[0] == 'UserWarning: real file'
    assert messages[1].strip().startswith('import logging')


def test_explicit_line_argument_is_used_verbatim(capture: tests.fixtures.base.LogCapture) -> None:
    warnings.showwarning('explicit', UserWarning, 'anything.py', 1, line='the given line')

    assert capture.messages() == ['UserWarning: explicit', '  the given line']


def test_source_line_lookup_failure_still_logs_the_warning(capture: tests.fixtures.base.LogCapture, monkeypatch: pytest.MonkeyPatch) -> None:
    """An OSError from linecache must not swallow the warning itself."""

    def raise_oserror(filename: str, lineno: int) -> str:
        raise OSError('boom')

    monkeypatch.setattr('linecache.getline', raise_oserror)
    warnings.showwarning('lookup failed', UserWarning, 'somewhere.py', 1)

    assert capture.messages() == [
        'could not read source line from somewhere.py',
        'UserWarning: lookup failed',
    ]


def test_setup_installs_the_hook_and_reset_restores_it(setup: collections.abc.Callable[..., tests.fixtures.base.LogCapture]) -> None:
    original = warnings.showwarning
    setup()
    assert warnings.showwarning is logit.showwarning

    logit.reset()
    assert warnings.showwarning is original
