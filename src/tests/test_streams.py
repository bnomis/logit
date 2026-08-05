import inspect
import sys
import typing

import hypothesis
import hypothesis.strategies

import logit
import tests.emitters.wanted

if typing.TYPE_CHECKING:
    import tests.fixtures.base


def test_print_becomes_an_info_record(capture: tests.fixtures.base.LogCapture) -> None:
    with capture.redirect():
        print('printed to stdout')

    record = capture.find('printed to stdout')
    assert record['level']['name'] == 'INFO'


def test_print_to_stderr_becomes_an_error_record(capture: tests.fixtures.base.LogCapture) -> None:
    with capture.redirect():
        print('printed to stderr', file=sys.stderr)

    record = capture.find('printed to stderr')
    assert record['level']['name'] == 'ERROR'


def test_stdout_and_stderr_are_separated_by_level(capture: tests.fixtures.base.LogCapture) -> None:
    with capture.redirect():
        print('out one')
        print('err one', file=sys.stderr)
        print('out two')

    levels = {r['message']: r['level']['name'] for r in capture.records()}
    assert levels == {'out one': 'INFO', 'err one': 'ERROR', 'out two': 'INFO'}


def test_print_reaches_all_three_sinks(capture: tests.fixtures.base.LogCapture) -> None:
    with capture.redirect():
        print('print to every sink')

    assert 'print to every sink' in capture.messages()
    assert 'print to every sink' in capture.text()
    assert 'print to every sink' in capture.stderr()


def test_print_is_attributed_to_the_calling_module(capture: tests.fixtures.base.LogCapture) -> None:
    with capture.redirect():
        tests.emitters.wanted.func()

    record = capture.find('This is a print message from wanted.py')
    assert record['name'] == 'tests.emitters.wanted'
    assert record['file']['name'] == 'wanted.py'
    assert record['function'] == 'func'


def test_print_source_location_is_the_caller(capture: tests.fixtures.base.LogCapture) -> None:
    with capture.redirect():
        expected_line = inspect.currentframe().f_lineno + 1
        print('locate this print')

    record = capture.find('locate this print')
    assert record['file']['name'] == 'test_streams.py'
    assert record['function'] == 'test_print_source_location_is_the_caller'
    assert record['line'] == expected_line


def test_multiline_write_becomes_one_record_per_line(capture: tests.fixtures.base.LogCapture) -> None:
    with capture.redirect():
        print('first\nsecond\nthird')

    assert capture.messages() == ['first', 'second', 'third']


def test_bare_newline_produces_no_record(capture: tests.fixtures.base.LogCapture) -> None:
    """print() writes its terminator separately; rstrip() must swallow it."""
    with capture.redirect():
        print('single line')

    assert capture.messages() == ['single line']


def test_empty_and_whitespace_writes_produce_no_records(capture: tests.fixtures.base.LogCapture) -> None:
    stream = logit.StreamToLogger(level='INFO')
    stream.write('\n')
    stream.write('   \n\t')
    stream.write('')

    assert capture.records() == []


def test_trailing_whitespace_is_stripped_per_line(capture: tests.fixtures.base.LogCapture) -> None:
    stream = logit.StreamToLogger(level='INFO')
    stream.write('padded   \nalso padded\t\n')

    assert capture.messages() == ['padded', 'also padded']


def test_stream_level_is_configurable(capture: tests.fixtures.base.LogCapture) -> None:
    logit.StreamToLogger(level='CRITICAL').write('urgent\n')

    assert capture.find('urgent')['level']['name'] == 'CRITICAL'


def test_flush_is_a_noop(capture: tests.fixtures.base.LogCapture) -> None:
    stream = logit.StreamToLogger(level='INFO')
    stream.write('before flush\n')
    stream.flush()

    assert capture.messages() == ['before flush']


@hypothesis.settings(max_examples=20, deadline=10000, suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
@hypothesis.given(buffer=hypothesis.strategies.text())
def test_write_splits_and_strips_arbitrary_text(buffer: str, capture: tests.fixtures.base.LogCapture) -> None:
    stream = logit.StreamToLogger(level='INFO')
    before = len(capture.messages())
    stream.write(buffer)

    expected = [line.rstrip() for line in buffer.rstrip().splitlines()]
    assert capture.messages()[before:] == expected
