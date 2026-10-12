import threading
from unittest import mock

import pytest
import requests

from departure.provider.ns import api, commons, data_updater, ns, view_model

STATION_CODE = "GVC"


@pytest.fixture(autouse=True)
def ns_api_key(monkeypatch):
    monkeypatch.setenv("NS_API_KEY", "test-key")


# api: failures raise instead of returning None


@pytest.mark.parametrize(
    "side_effect",
    [requests.exceptions.Timeout(), requests.exceptions.ConnectionError()],
)
def test_api_request_raises_on_request_error(side_effect):
    with mock.patch.object(api.requests, "get", side_effect=side_effect):
        with pytest.raises(commons.NSException):
            api.api_request("https://example.org", {})


def test_departures_raise_on_http_error():
    with mock.patch.object(api.requests, "get", return_value=mock.Mock(status_code=503)):
        with pytest.raises(commons.NSException, match="503"):
            ns.departures_with_schedule(STATION_CODE)


# data updater: failed poll shows "unavailable", never stale data


class StoppingDataUpdater(data_updater.DataUpdaterNS):
    def __init__(self, target_view_model, end_event, polls):
        super().__init__(target_view_model, 0, end_event, STATION_CODE)
        self.polls = polls

    def update(self):
        if len(self.polls) == 1:
            self.end_event.set()
        with mock.patch.object(
            data_updater.ns, "departures_with_schedule", **self.polls.pop(0)
        ):
            super().update()


def run_polls(polls):
    target_view_model = mock.Mock()
    StoppingDataUpdater(target_view_model, threading.Event(), polls).run()
    return target_view_model


def test_failed_poll_shows_unavailable():
    target_view_model = run_polls([{"side_effect": commons.NSException("down")}])

    target_view_model.update_unavailable.assert_called_once_with()
    target_view_model.update.assert_not_called()


def test_recovery_with_same_departures_replaces_unavailable():
    trains = [
        {
            "direction": "Utrecht Centraal",
            "planned_time": "10:00",
            "actual_time": "10:00",
            "track": "5",
            "train_number": "2041",
            "train_category": "Intercity",
            "schedule": [],
        }
    ]
    target_view_model = run_polls(
        [
            {"return_value": trains},
            {"side_effect": commons.NSException("down")},
            {"return_value": trains},  # same as before the failure
        ]
    )

    assert target_view_model.mock_calls == [
        mock.call.update(trains, STATION_CODE),
        mock.call.update_unavailable(),
        mock.call.update(trains, STATION_CODE),
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
    model = view_model.ViewModelNS192x32x3ToProtocolBuffers(stub)

    model.update_unavailable()

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(
        model, "Data unavailable"
    )
    assert len(sections[1].content.pixels) == 0
    assert len(sections[2].content.pixels) == 0


def test_no_service_still_shown_for_empty_departures():
    stub = mock.Mock()
    model = view_model.ViewModelNS192x32x3ToProtocolBuffers(stub)

    model.update([], STATION_CODE)

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(model, "No service")
