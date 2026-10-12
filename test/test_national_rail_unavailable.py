import threading
from unittest import mock

import pytest
import requests
import zeep.exceptions
from click.testing import CliRunner

from departure.provider.national_rail import (
    api,
    cli,
    commons,
    data_updater,
    national_rail,
    view_model,
)

STATION_CODE = "NCL"


@pytest.fixture(autouse=True)
def ldb_token(monkeypatch):
    monkeypatch.setenv("LDB_TOKEN", "test-token")


# api: SOAP and HTTP failures raise NationalRailException


@pytest.mark.parametrize(
    "side_effect",
    [
        # requests' ConnectionError is not a subclass of the builtin one
        requests.exceptions.ConnectionError(),
        requests.exceptions.Timeout(),
        zeep.exceptions.Fault("server error"),
        zeep.exceptions.TransportError("bad gateway", status_code=502),
    ],
)
def test_next_services_raises_on_api_failure(side_effect):
    with mock.patch.object(api, "Client") as client_class:
        client_class.return_value.service.GetDepBoardWithDetails.side_effect = (
            side_effect
        )
        with pytest.raises(commons.NationalRailException):
            national_rail.next_services(STATION_CODE)


def test_next_services_raises_when_wsdl_cannot_be_loaded():
    with mock.patch.object(
        api, "Client", side_effect=requests.exceptions.ConnectionError()
    ):
        with pytest.raises(commons.NationalRailException):
            national_rail.next_services(STATION_CODE)


# data updater: failed poll shows "unavailable", never stale data


class StoppingDataUpdater(data_updater.DataUpdaterNationalRail):
    def __init__(self, target_view_model, end_event, polls):
        super().__init__(target_view_model, 0, end_event, STATION_CODE)
        self.polls = polls

    def update(self):
        if len(self.polls) == 1:
            self.end_event.set()
        with mock.patch.object(
            data_updater.national_rail, "next_services", **self.polls.pop(0)
        ):
            super().update()


def run_polls(polls):
    target_view_model = mock.Mock()
    StoppingDataUpdater(target_view_model, threading.Event(), polls).run()
    return target_view_model


def test_failed_poll_shows_unavailable():
    target_view_model = run_polls(
        [{"side_effect": commons.NationalRailException("down")}]
    )

    target_view_model.update_unavailable.assert_called_once_with()
    target_view_model.update.assert_not_called()


def test_recovery_with_same_services_replaces_unavailable():
    services = [
        {
            "std": "10:00",
            "etd": "On time",
            "platform": "3",
            "destination_location_name": "Edinburgh",
            "origin_location_name": "London Kings Cross",
            "operator": "LNER",
            "calling_points": [],
        }
    ]
    target_view_model = run_polls(
        [
            {"return_value": services},
            {"side_effect": commons.NationalRailException("down")},
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
    model = view_model.ViewModelNationalRail_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update_unavailable()

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(
        model, "Data unavailable"
    )
    assert len(sections[1].content.pixels) == 0
    assert len(sections[2].content.pixels) == 0


def test_no_service_still_shown_for_empty_departures():
    stub = mock.Mock()
    model = view_model.ViewModelNationalRail_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update([])

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(model, "No service")


# cli: failure is reported, not a traceback


def test_cli_next_reports_api_failure():
    with mock.patch.object(
        cli.national_rail,
        "next_services",
        side_effect=commons.NationalRailException("API down"),
    ):
        result = CliRunner().invoke(cli.cli, ["next", STATION_CODE])

    assert result.exception is None
    assert "error: API down" in result.output
