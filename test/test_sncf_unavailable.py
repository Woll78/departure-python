import threading
from unittest import mock

import pytest
import requests
from click.testing import CliRunner

from departure.provider.sncf import api, cli, commons, data_updater, sncf, view_model

STOP_AREA_ID = "87393702"


@pytest.fixture(autouse=True)
def sncf_key(monkeypatch):
    monkeypatch.setenv("SNCF_KEY", "test-key")


# api: failures raise instead of returning None


@pytest.mark.parametrize(
    "side_effect",
    [requests.exceptions.Timeout(), requests.exceptions.ConnectionError()],
)
def test_api_request_raises_on_request_error(side_effect):
    with mock.patch.object(api.requests, "get", side_effect=side_effect):
        with pytest.raises(commons.SncfException):
            api.api_request("https://example.org")


def test_api_request_raises_on_http_error():
    response = mock.Mock(status_code=503)
    with mock.patch.object(api.requests, "get", return_value=response):
        with pytest.raises(commons.SncfException, match="503"):
            api.api_request("https://example.org")


def test_next_trains_propagates_api_failure():
    # an outage must not be reported as "no trains"
    with mock.patch.object(api.requests, "get", return_value=mock.Mock(status_code=503)):
        with pytest.raises(commons.SncfException, match="503"):
            sncf.next_trains(STOP_AREA_ID)


# data updater: failed poll shows "unavailable", never stale data


class StoppingDataUpdater(data_updater.DataUpdaterSncf):
    def __init__(self, target_view_model, end_event, polls):
        super().__init__(target_view_model, 0, end_event, STOP_AREA_ID)
        self.polls = polls

    def update(self):
        if len(self.polls) == 1:
            self.end_event.set()
        with mock.patch.object(data_updater.sncf, "next_trains", **self.polls.pop(0)):
            super().update()


def run_polls(polls):
    target_view_model = mock.Mock()
    StoppingDataUpdater(target_view_model, threading.Event(), polls).run()
    return target_view_model


def test_failed_poll_shows_unavailable():
    target_view_model = run_polls([{"side_effect": commons.SncfException("down")}])

    target_view_model.update_unavailable.assert_called_once_with()
    target_view_model.update.assert_not_called()


def test_recovery_with_same_trains_replaces_unavailable():
    trains = [
        {
            "headsign": "8501",
            "direction": "Lyon-Part-Dieu",
            "time": "10:00",
            "base_time": "10:00",
            "commercial_mode": "TGV INOUI",
        }
    ]
    target_view_model = run_polls(
        [
            {"return_value": trains},
            {"side_effect": commons.SncfException("down")},
            {"return_value": trains},  # same as before the failure
        ]
    )

    assert target_view_model.mock_calls == [
        mock.call.update(trains),
        mock.call.update_unavailable(),
        mock.call.update(trains),
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
    model = view_model.ViewModelSncf_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update_unavailable()

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(
        model, "Information indisponible"
    )
    assert len(sections[1].content.pixels) == 0
    assert len(sections[2].content.pixels) == 0


def test_no_service_still_shown_for_empty_departures():
    stub = mock.Mock()
    model = view_model.ViewModelSncf_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update([])

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(model, "Pas de service")


# cli: failure is reported, not a traceback


def test_cli_next_reports_api_failure():
    with mock.patch.object(
        cli.sncf, "next_trains", side_effect=commons.SncfException("API down")
    ):
        result = CliRunner().invoke(cli.cli, ["next", STOP_AREA_ID])

    assert result.exception is None
    assert "error: API down" in result.output
