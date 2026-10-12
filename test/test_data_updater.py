import threading
from unittest import mock

from departure.board import data_updater


class FlakyUpdater(data_updater.DataUpdater):
    def __init__(self, end_event, failures):
        super().__init__(mock.Mock(), 0, end_event)
        self.calls = 0
        self.failures = failures

    def update(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise TypeError("API returned nothing")
        self.end_event.set()


def test_thread_survives_failed_updates_and_keeps_polling():
    end_event = threading.Event()
    updater = FlakyUpdater(end_event, failures=2)

    updater.run()  # runs inline; would raise on the first poll before the fix

    assert updater.calls == 3


class FailingFailureHandler(FlakyUpdater):
    def update_failed(self):
        raise RuntimeError("board unreachable")


def test_thread_survives_failure_in_update_failed():
    end_event = threading.Event()
    updater = FailingFailureHandler(end_event, failures=2)

    updater.run()

    assert updater.calls == 3
