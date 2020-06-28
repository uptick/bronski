import logging
import signal
import time

import pytest

from bronski.runner import JobRunner, ProgramKilled


def test_setup_signals(mocker, freezer):
    runner = JobRunner(None)

    mock_signal = mocker.patch("signal.signal")
    mock_setitimer = mocker.patch("signal.setitimer")

    freezer.move_to("2020-06-01T12:34:01")

    runner.setup_signals()

    mock_signal.assert_any_call(signal.SIGTERM, runner.break_handler)
    mock_signal.assert_any_call(signal.SIGINT, runner.break_handler)
    mock_signal.assert_any_call(signal.SIGALRM, runner.timer_handler)

    mock_setitimer.assert_called_once_with(signal.ITIMER_REAL, 59, 60)


def test_timer_handler(caplog):
    runner = JobRunner(None)

    assert not runner.trigger.is_set()

    with caplog.at_level(logging.DEBUG):
        runner.timer_handler(None, None)

    assert runner.trigger.is_set()
    assert "Scanning jobs..." in caplog.text


def test_break_handler(caplog):

    runner = JobRunner(None)

    with caplog.at_level(logging.INFO):
        with pytest.raises(ProgramKilled):
            runner.break_handler(0, None)

    assert "Detected stop request..." in caplog.text


def test_stop(caplog, mocker):
    runner = JobRunner(None)

    mocker.patch.object(runner, "join")

    assert not runner.stopped.is_set()
    assert not runner.trigger.is_set()

    with caplog.at_level(logging.INFO):
        runner.stop()

    assert "Setting stop..." in caplog.text
    assert runner.stopped.is_set()
    assert runner.trigger.is_set()
    runner.join.assert_called_once()


def test_run_stopped(caplog):
    runner = JobRunner(None)

    runner.trigger.set()
    runner.stopped.set()

    with caplog.at_level(logging.INFO):
        runner.run()

    assert "Starting Bronski Runner..." in caplog.text

    assert "Stopping..." in caplog.text


def YIELD():
    time.sleep(0.001)


@pytest.mark.timeout(timeout=5)
def test_run_trigger(caplog, mocker):

    MockModel = mocker.Mock()
    MockModel.objects.current_jobs.configure_mock(return_value=[])

    mocker.patch("django.db.close_old_connections")

    runner = JobRunner(MockModel)

    assert not runner.is_alive()

    with caplog.at_level(logging.DEBUG):
        try:
            runner.start()

            YIELD()

            assert runner.is_alive()

            runner.trigger.set()

            YIELD()

            assert runner.is_alive()

            while runner.trigger.is_set():
                YIELD()

            runner.stopped.set()

            YIELD()

            assert runner.is_alive()

            runner.trigger.set()

            YIELD()

            assert not runner.is_alive()

        finally:
            if runner.is_alive():
                runner.trigger.set()
                runner.stop()
