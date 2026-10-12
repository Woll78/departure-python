import threading
from unittest import mock

import pytest
import requests

from departure.provider.tfl_tube import api, commons, data_updater, tfl_tube, view_model

LINE_ID, STATION_ID, DIRECTION = "central", "940GZZLULGN", "Westbound"


@pytest.fixture(autouse=True)
def tfl_app_key(monkeypatch):
    monkeypatch.setenv("TFL_APP_KEY", "test-key")


# api: failures raise instead of returning None


@pytest.mark.parametrize(
    "side_effect",
    [requests.exceptions.Timeout(), requests.exceptions.ConnectionError()],
)
def test_api_request_raises_on_request_error(side_effect):
    with mock.patch.object(api.requests, "get", side_effect=side_effect):
        with pytest.raises(commons.TflTubeException):
            api.unified_api_request("https://example.org")


def test_next_trains_raises_on_http_error():
    # an outage must not be reported as "no trains"
    with mock.patch.object(api.requests, "get", return_value=mock.Mock(status_code=503)):
        with pytest.raises(commons.TflTubeException, match="503"):
            tfl_tube.next_trains(LINE_ID, STATION_ID)


def test_next_trains_raises_when_trains_at_platform_unavailable():
    # without this call the train at the platform, i.e. the 1st one, is missing
    with mock.patch.object(api, "line_arrivals", return_value=[]), mock.patch.object(
        api, "tube_arrivals", side_effect=commons.TflTubeException("down")
    ):
        with pytest.raises(commons.TflTubeException):
            tfl_tube.next_trains(LINE_ID, STATION_ID)


# data updater: failed poll shows "unavailable", never stale data


class StoppingDataUpdater(data_updater.DataUpdaterTflTube):
    def __init__(self, target_view_model, end_event, polls):
        super().__init__(
            target_view_model, 0, end_event, LINE_ID, STATION_ID, DIRECTION
        )
        self.polls = polls

    def update(self):
        if len(self.polls) == 1:
            self.end_event.set()
        with mock.patch.object(
            data_updater.tfl_tube, "next_trains", **self.polls.pop(0)
        ):
            super().update()


def run_polls(polls):
    target_view_model = mock.Mock()
    StoppingDataUpdater(target_view_model, threading.Event(), polls).run()
    return target_view_model


def test_failed_poll_shows_unavailable():
    target_view_model = run_polls([{"side_effect": commons.TflTubeException("down")}])

    target_view_model.update_unavailable.assert_called_once_with()
    target_view_model.update.assert_not_called()


def test_recovery_with_same_trains_replaces_unavailable():
    trains = {"central-114": {"towards": "Northolt", "time_to_station": 60}}
    target_view_model = run_polls(
        [
            {"return_value": trains},
            {"side_effect": commons.TflTubeException("down")},
            {"return_value": trains},  # same as before the failure
        ]
    )

    assert target_view_model.mock_calls == [
        mock.call.update(trains),
        mock.call.update_unavailable(),
        mock.call.update(trains),
    ]


# view model


def sent_sections(stub):
    request = stub.BoardSectionsUpdate.call_args.args[0]
    return {r.section_index: r for r in request.requests}


def test_update_unavailable_shows_message_on_board():
    stub = mock.Mock()
    model = view_model.ViewModelTflTube_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update_unavailable()

    sections = sent_sections(stub)
    expected_pixels, _ = model.board_text.colour_text_pixels(
        [["Data unavailable", "orange"]]
    )
    assert len(sections[0].content.pixels) == len(expected_pixels)
    assert len(sections[1].content.pixels) == 0
    assert len(sections[2].content.pixels) == 0
