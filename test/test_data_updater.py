import threading
from unittest import mock

import pytest
import requests

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


def test_national_rail_requests_connection_error_is_handled():
    # requests' ConnectionError is not a subclass of the builtin one
    assert not issubclass(requests.exceptions.ConnectionError, ConnectionError)

    try:
        from departure.provider.national_rail import (  # pylint: disable=import-outside-toplevel
            data_updater as nr_data_updater,
        )
    except TypeError:  # stale generated departure_pb2 vs. new protobuf
        pytest.skip("departure_pb2 incompatible with installed protobuf")

    updater = nr_data_updater.DataUpdaterNationalRail(
        mock.Mock(), 0, threading.Event(), "NCL"
    )
    with mock.patch.object(
        nr_data_updater.national_rail,
        "next_services",
        side_effect=requests.exceptions.ConnectionError(),
    ):
        updater.update()  # must log a warning, not raise
