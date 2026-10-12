import threading
from unittest import mock

import pytest
import requests
import zeep.exceptions
from click.testing import CliRunner

from departure.provider.ratp import api, cli, commons, data_updater, ratp, view_model

LINE_ID, STATION_ID, DIRECTION = "RB", "15", "A"


# api: SOAP and HTTP failures raise RatpException


@pytest.mark.parametrize(
    "side_effect",
    [
        requests.exceptions.ConnectionError(),
        requests.exceptions.Timeout(),
        zeep.exceptions.Fault("server error"),
        zeep.exceptions.TransportError("bad gateway", status_code=502),
    ],
)
def test_next_departures_raises_on_api_failure(side_effect):
    client = mock.Mock()
    client.service.getMissionsNext.side_effect = side_effect

    with mock.patch.object(api, "soap_client", return_value=client):
        with pytest.raises(commons.RatpException):
            ratp.next_departures(LINE_ID, STATION_ID, DIRECTION)


# data updater: failed poll shows "unavailable", never stale data


class StoppingDataUpdater(data_updater.DataUpdaterRatp):
    def __init__(self, target_view_model, end_event, polls):
        super().__init__(
            target_view_model, 0, end_event, LINE_ID, STATION_ID, DIRECTION
        )
        self.polls = polls

    def update(self):
        if len(self.polls) == 1:
            self.end_event.set()
        with mock.patch.object(
            data_updater.ratp, "next_departures", **self.polls.pop(0)
        ):
            super().update()


def run_polls(polls):
    target_view_model = mock.Mock()
    StoppingDataUpdater(target_view_model, threading.Event(), polls).run()
    return target_view_model


def test_failed_poll_shows_unavailable():
    target_view_model = run_polls([{"side_effect": commons.RatpException("down")}])

    target_view_model.update_unavailable.assert_called_once_with()
    target_view_model.update.assert_not_called()


def test_recovery_with_same_departures_replaces_unavailable():
    departures = {
        "missions": [
            {
                "code": None,
                "destinationName": "Robinson",
                "datetime": "202010121000",
                "message": "2 mn",
            }
        ],
        "perturbations": "",
    }
    target_view_model = run_polls(
        [
            {"return_value": departures},
            {"side_effect": commons.RatpException("down")},
            {"return_value": departures},  # same as before the failure
        ]
    )

    assert target_view_model.mock_calls == [
        mock.call.update(departures),
        mock.call.update_unavailable(),
        mock.call.update(departures),
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
    model = view_model.ViewModelRatp_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update_unavailable()

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(
        model, "Information indisponible"
    )
    assert len(sections[1].content.pixels) == 0
    assert len(sections[2].content.pixels) == 0
    assert sections[2].movement[0].HasField("no_movement")


def test_no_service_still_shown_for_empty_departures():
    stub = mock.Mock()
    model = view_model.ViewModelRatp_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update({"missions": [], "perturbations": ""})

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(model, "Pas de service")


def test_disruptions_still_scroll_horizontally():
    stub = mock.Mock()
    model = view_model.ViewModelRatp_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update({"missions": [], "perturbations": "Trafic perturbé"})

    bottom = sent_sections(stub)[2]
    assert bottom.movement[0].HasField("scrolling_content")
    assert bottom.content.repeat_x


# cli: failure is reported, not a traceback


def test_cli_next_reports_api_failure():
    with mock.patch.object(
        cli.ratp, "next_departures", side_effect=commons.RatpException("API down")
    ):
        result = CliRunner().invoke(cli.cli, ["next", LINE_ID, STATION_ID, DIRECTION])

    assert result.exception is None
    assert "error: API down" in result.output
