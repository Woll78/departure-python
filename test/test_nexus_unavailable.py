import threading
from unittest import mock

import pytest
import requests
from click.testing import CliRunner

from departure.provider.nexus import api, cli, commons, data_updater, nexus, view_model
from departure.provider.nexus.bus_data_model import BusData
from departure.provider.nexus.companies import gone

STOP_CODE = "41000010JARA"


# Go North East scrape: bounded and fails loudly


def test_gone_fetch_has_timeout():
    # without a timeout a hung site blocks the polling thread forever
    with mock.patch.object(gone.requests, "get") as get:
        get.return_value.content = b"<html></html>"
        gone.GONE().fetch(STOP_CODE)

    assert get.call_args.kwargs.get("timeout")


def test_gone_fetch_raises_on_http_error():
    response = mock.Mock()
    response.raise_for_status.side_effect = requests.exceptions.HTTPError("503")
    with mock.patch.object(gone.requests, "get", return_value=response):
        with pytest.raises(requests.exceptions.HTTPError):
            gone.GONE().fetch(STOP_CODE)


# api: any operator failing raises, never a partial or empty board


@pytest.mark.parametrize("failing_operator", ["GONE", "Stagecoach"])
def test_next_services_raises_when_an_operator_fails(failing_operator):
    bus = BusData("27", "Jarrow", "5 mins", "Go North East")
    with mock.patch.object(
        api.GONE, "fetch", return_value=[bus]
    ), mock.patch.object(api.Stagecoach, "fetch", return_value=[]), mock.patch.object(
        getattr(api, failing_operator),
        "fetch",
        side_effect=requests.exceptions.ConnectionError(),
    ):
        with pytest.raises(commons.NexusBusException):
            nexus.next_services(STOP_CODE)


def test_next_services_combines_operators_sorted_by_time():
    later = BusData("27", "Jarrow", "10 mins", "Go North East")
    sooner = BusData("E1", "Heworth", "2 mins", "Stagecoach")
    with mock.patch.object(api.GONE, "fetch", return_value=[later]), mock.patch.object(
        api.Stagecoach, "fetch", return_value=[sooner]
    ):
        assert nexus.next_services(STOP_CODE) == [sooner, later]


# data updater: failed poll shows "unavailable", never stale data


class StoppingDataUpdater(data_updater.DataUpdaterNexusBus):
    def __init__(self, target_view_model, end_event, polls):
        super().__init__(target_view_model, 0, end_event, STOP_CODE)
        self.polls = polls

    def update(self):
        if len(self.polls) == 1:
            self.end_event.set()
        with mock.patch.object(
            data_updater.nexus, "next_services", **self.polls.pop(0)
        ):
            super().update()


def run_polls(polls):
    target_view_model = mock.Mock()
    StoppingDataUpdater(target_view_model, threading.Event(), polls).run()
    return target_view_model


def test_failed_poll_shows_unavailable():
    target_view_model = run_polls(
        [{"side_effect": commons.NexusBusException("down")}]
    )

    target_view_model.update_unavailable.assert_called_once_with()
    target_view_model.update.assert_not_called()


def test_recovery_with_same_services_replaces_unavailable():
    services = [BusData("27", "Jarrow", "5 mins", "Go North East")]
    target_view_model = run_polls(
        [
            {"return_value": services},
            {"side_effect": commons.NexusBusException("down")},
            {"return_value": services},  # same as before the failure
        ]
    )

    assert target_view_model.mock_calls == [
        mock.call.update(services),
        mock.call.update_unavailable(),
        mock.call.update(services),
    ]


# view model: "unavailable" is distinct from "no service"


def sent_sections(stub):
    request = stub.BoardSectionsUpdate.call_args.args[0]
    return {r.section_index: r for r in request.requests}


def text_pixel_count(model, text):
    pixels, _ = model.board_text.colour_text_pixels([[text, "orange"]])
    return len(pixels)


def test_update_unavailable_shows_message_on_board():
    stub = mock.Mock()
    model = view_model.ViewModelNexusBus_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update_unavailable()

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(
        model, "Data unavailable"
    )
    assert len(sections[1].content.pixels) == 0
    assert len(sections[2].content.pixels) == 0


def test_no_service_still_shown_for_empty_departures():
    stub = mock.Mock()
    model = view_model.ViewModelNexusBus_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update([])

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(model, "No service.")


# cli: failure is reported, not a traceback


def test_cli_next_reports_api_failure():
    with mock.patch.object(
        cli.nexus, "next_services", side_effect=commons.NexusBusException("API down")
    ):
        result = CliRunner().invoke(cli.cli, ["next", STOP_CODE])

    assert result.exception is None
    assert "error: API down" in result.output
