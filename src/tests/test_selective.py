import warnings

import pytest

import tests.emitters.some_lib
import tests.emitters.unwanted
import tests.emitters.wanted

UNWANTED = 'tests.emitters.unwanted'
WANTED = 'tests.emitters.wanted'
SOME_LIB = 'tests.emitters.some_lib'

EMITTERS = {
    WANTED: tests.emitters.wanted,
    UNWANTED: tests.emitters.unwanted,
    SOME_LIB: tests.emitters.some_lib,
}


def run_all(capture):
    with capture.redirect():
        for module in EMITTERS.values():
            module.func()


def test_disabled_module_is_completely_silent(setup):
    capture = setup(disabled=[UNWANTED])
    run_all(capture)

    assert capture.from_module(UNWANTED) == []
    assert 'unwanted.py' not in capture.text()
    assert 'unwanted.py' not in capture.stderr()


def test_enabled_modules_still_log(setup):
    capture = setup(disabled=[UNWANTED])
    run_all(capture)

    assert capture.names() == {WANTED, SOME_LIB}
    assert capture.from_module(WANTED)
    assert capture.from_module(SOME_LIB)


# every message func() emits, one per capture path
PATHS = [
    pytest.param('This is an error message from {module}.py', id='logging'),
    pytest.param('This is a print message from {module}.py', id='print'),
    pytest.param('This is a print message to stderr from {module}.py', id='print-stderr'),
    pytest.param('DeprecationWarning: This is a warnings.warn message from {module}.py', id='warn'),
    pytest.param('DeprecationWarning: This is a warnings.showwarning message from {module}.py', id='showwarning'),
]


@pytest.mark.parametrize('template', PATHS)
def test_every_capture_path_is_suppressed(setup, template):
    """All five routes into loguru must respect the disabled list."""
    capture = setup(disabled=[UNWANTED])
    run_all(capture)

    assert template.format(module='unwanted') not in capture.messages()
    # the identical path from an enabled module still gets through
    assert template.format(module='wanted') in capture.messages()


def test_direct_showwarning_is_attributed_to_its_caller_not_its_filename(setup):
    """The filename argument only feeds linecache; attribution comes from the frame.

    So a warning *about* a disabled module, raised from elsewhere, is not
    suppressed - only warnings raised *inside* it are.
    """
    capture = setup(disabled=[UNWANTED])
    warnings.showwarning('about unwanted', UserWarning, tests.emitters.unwanted.__file__, 1)

    record = capture.find('UserWarning: about unwanted')
    assert record['name'] == __name__
    assert record['file']['name'] == 'test_selective.py'


@pytest.mark.parametrize('name', [WANTED, UNWANTED, SOME_LIB])
def test_any_module_can_be_the_disabled_one(setup, name):
    capture = setup(disabled=[name])
    run_all(capture)

    assert name not in capture.names()
    assert capture.names() == set(EMITTERS) - {name}


def test_multiple_modules_can_be_disabled(setup):
    capture = setup(disabled=[UNWANTED, SOME_LIB])
    run_all(capture)

    assert capture.names() == {WANTED}


def test_nothing_is_suppressed_by_default(setup):
    capture = setup()
    run_all(capture)

    assert capture.names() == set(EMITTERS)


def test_disabling_covers_submodules(setup):
    capture = setup(disabled=['tests.emitters'])
    run_all(capture)

    assert capture.records() == []
