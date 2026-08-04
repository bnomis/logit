import json
import multiprocessing
import os
import pathlib
import threading

import joblib
import loguru
import pytest

import logit.base

pytestmark = pytest.mark.slow

MESSAGES = 20


def child_entrypoint(directory: str, label: str) -> None:
    """Runs in a forked/spawned child: sets up its own per-pid sinks."""
    logit.base.setup_logger(directory=pathlib.Path(directory), subprocess=True)
    for index in range(MESSAGES):
        loguru.logger.info(f'{label} {index}')
    loguru.logger.complete()


def child_records(directory: pathlib.Path) -> dict[int, list[dict]]:
    """Every log-<pid>.jsonl in the directory, keyed by pid."""
    by_pid = {}
    for path in sorted(directory.glob('log-*.jsonl')):
        pid = int(path.stem.removeprefix('log-'))
        by_pid[pid] = [json.loads(line)['record'] for line in path.read_text().splitlines() if line.strip()]
    return by_pid


def emit(label: str) -> None:
    for index in range(MESSAGES):
        loguru.logger.info(f'{label} {index}')


def test_threads_share_the_log_and_keep_distinct_thread_ids(capture):
    threads = [threading.Thread(target=emit, args=(f'thread-{n}',)) for n in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    records = capture.records()
    assert len(records) == 3 * MESSAGES

    for n in range(3):
        assert len([r for r in records if r['message'].startswith(f'thread-{n} ')]) == MESSAGES

    thread_ids = {r['thread']['id'] for r in records}
    assert len(thread_ids) == 3
    assert {r['process']['id'] for r in records} == {os.getpid()}


def test_threaded_records_are_not_interleaved_mid_line(capture):
    """enqueue=True serialises writes, so no line may be torn."""
    threads = [threading.Thread(target=emit, args=(f'thread-{n}',)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    lines = [line for line in capture.text().splitlines() if line.strip()]
    assert len(lines) == 4 * MESSAGES
    for line in lines:
        assert line.count('thread-') == 1


def test_multiprocessing_children_write_their_own_files(capture):
    processes = [multiprocessing.Process(target=child_entrypoint, args=(str(capture.directory), f'proc-{n}')) for n in range(2)]
    for process in processes:
        process.start()
    for process in processes:
        process.join()

    assert all(p.exitcode == 0 for p in processes)

    by_pid = child_records(capture.directory)
    assert len(by_pid) == 2
    for pid, records in by_pid.items():
        assert len(records) == MESSAGES, f'pid {pid} lost records across fork'
        assert {r['process']['id'] for r in records} == {pid}

    labels = {r['message'].split()[0] for records in by_pid.values() for r in records}
    assert labels == {'proc-0', 'proc-1'}


def test_joblib_workers_write_their_own_files(capture):
    joblib.Parallel(n_jobs=2)(joblib.delayed(child_entrypoint)(str(capture.directory), f'job-{n}') for n in range(2))

    by_pid = child_records(capture.directory)
    assert by_pid, 'no per-pid files were written'
    assert sum(len(records) for records in by_pid.values()) == 2 * MESSAGES

    for pid, records in by_pid.items():
        assert {r['process']['id'] for r in records} == {pid}


def test_child_logs_do_not_land_in_the_parent_log(capture):
    loguru.logger.info('parent only')
    process = multiprocessing.Process(target=child_entrypoint, args=(str(capture.directory), 'child'))
    process.start()
    process.join()

    assert capture.messages() == ['parent only']
    assert os.getpid() not in child_records(capture.directory)
