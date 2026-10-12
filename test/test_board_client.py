import importlib
import inspect
import threading
import time
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from departure.board import board_client

PROVIDERS = ["national_rail", "nexus", "ns", "ratp", "sncf", "tfl_tube", "transilien"]


class RecordingViewModel:
    instances = []

    def __init__(self, board_manager_stub):
        self.board_manager_stub = board_manager_stub
        self.calls = []
        RecordingViewModel.instances.append(self)

    def update(self, *args):
        self.calls.append(("update",) + args)

    def update_unavailable(self):
        self.calls.append(("update_unavailable",))


class InFlightUpdater(threading.Thread):
    """Updater whose first poll is still in flight until release is set."""

    instances = []

    def __init__(self, target_view_model, data_refresh_delay_in_s, end_event, **kwargs):
        super().__init__()
        self.view_model = target_view_model
        self.end_event = end_event
        self.kwargs = kwargs
        self.release = threading.Event()
        self.started_polling = threading.Event()
        InFlightUpdater.instances.append(self)

    def run(self):
        self.started_polling.set()
        self.release.wait(5)
        self.view_model.update(f"departures for {self.kwargs['station']}")
        self.end_event.wait(5)


@pytest.fixture(autouse=True)
def fakes():
    RecordingViewModel.instances = []
    InFlightUpdater.instances = []
    with mock.patch.object(board_client.grpc, "insecure_channel"):
        yield
    for updater in InFlightUpdater.instances:
        updater.release.set()
        updater.end_event.set()


def start(client, station):
    client.start(RecordingViewModel, InFlightUpdater, {"station": station})
    updater = InFlightUpdater.instances[-1]
    assert updater.started_polling.wait(5)
    return updater


def test_start_runs_updater_with_arguments():
    client = board_client.BoardClient()

    updater = start(client, "A")
    updater.release.set()

    assert client.running
    assert updater.kwargs == {"station": "A"}
    assert updater.daemon  # must not keep the CLI alive after Ctrl-C


def test_stop_blanks_board_and_ends_updater():
    client = board_client.BoardClient()
    updater = start(client, "A")

    client.stop()

    assert not client.running
    assert updater.end_event.is_set()
    assert RecordingViewModel.instances[0].calls == [("update", None)]


def test_stop_does_not_wait_for_in_flight_poll():
    client = board_client.BoardClient()
    start(client, "A")  # poll never released

    started = time.monotonic()
    client.stop()

    assert time.monotonic() - started < 1


def test_old_poll_finishing_after_restart_cannot_touch_board():
    client = board_client.BoardClient()
    old = start(client, "A")
    new = start(client, "B")

    new.release.set()
    new.join(0.1)  # let the new poll reach the board
    old.release.set()  # old poll completes after the switch
    old.join(5)

    old_view_model, new_view_model = RecordingViewModel.instances
    assert old_view_model.calls == [("update", None)]  # blanked, then nothing
    assert new_view_model.calls == [("update", "departures for B")]


def test_stop_when_not_started_does_nothing():
    client = board_client.BoardClient()

    client.stop()

    assert not client.running


def test_concurrent_starts_leave_exactly_one_client_on_board():
    client = board_client.BoardClient()
    barrier = threading.Barrier(2)

    def start_station(station):
        barrier.wait()
        client.start(RecordingViewModel, InFlightUpdater, {"station": station})

    threads = [threading.Thread(target=start_station, args=[s]) for s in "AB"]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)

    not_blanked = [
        vm for vm in RecordingViewModel.instances if ("update", None) not in vm.calls
    ]
    assert len(RecordingViewModel.instances) == 2
    assert len(not_blanked) == 1


# web server: start/stop must not block the event loop


@pytest.mark.parametrize("provider", PROVIDERS)
def test_start_client_routes_do_not_block_event_loop(provider):
    server = importlib.import_module(f"departure.provider.{provider}.server")
    endpoint = next(
        route.endpoint for route in server.router.routes if route.path == "/start-client"
    )

    # sync endpoints run in FastAPI's threadpool; async ones block the loop
    assert not inspect.iscoroutinefunction(endpoint)


def test_api_server_start_and_stop_client():
    from departure.web import api_server  # pylint: disable=import-outside-toplevel
    from departure.provider.sncf import (  # pylint: disable=import-outside-toplevel
        data_updater as sncf_data_updater,
        view_model as sncf_view_model,
    )

    http = TestClient(api_server.app)
    with mock.patch.object(api_server.app, "board_client") as client, mock.patch.dict(
        "os.environ", {"SNCF_KEY": "test-key"}
    ):
        client.running = True
        response = http.post("/sncf/start-client", json={"stop_area_id": "87393702"})
        assert response.json() == {"status": "OK"}
        client.start.assert_called_once_with(
            sncf_view_model.ViewModelSncf_192_32_3_Rows_To_ProtocolBuffers,
            sncf_data_updater.DataUpdaterSncf,
            {"stop_area_id": "87393702"},
        )

        assert http.post("/stop-client").json() == {"status": "OK"}
        client.stop.assert_called_once_with()
        assert http.get("/client-status").json() == {"client_status": "running"}


# CLI: board command starts the client and stops it on Ctrl-C


def test_cli_board_stops_client_on_interrupt():
    from departure.provider.sncf import cli  # pylint: disable=import-outside-toplevel
    from click.testing import CliRunner  # pylint: disable=import-outside-toplevel

    with mock.patch.object(cli.board_client, "BoardClient") as client_class, mock.patch.object(
        cli.time, "sleep", side_effect=KeyboardInterrupt
    ):
        result = CliRunner().invoke(cli.cli, ["board", "87393702"])

    assert result.exception is None
    client = client_class.return_value
    client.start.assert_called_once()
    client.stop.assert_called_once_with()
