import threading
from unittest import mock

from departure.provider.kent import commons, data_updater, view_model
from departure.provider.nexus.bus_data_model import BusData

STOP_CODE = "2400A045760A"


# data updater: failed poll shows "unavailable", never stale data


class StoppingDataUpdater(data_updater.DataUpdaterKentBus):
    def __init__(self, target_view_model, end_event, polls):
        super().__init__(target_view_model, 0, end_event, STOP_CODE)
        self.polls = polls

    def update(self):
        if len(self.polls) == 1:
            self.end_event.set()
        with mock.patch.object(
            data_updater.kent, "next_services", **self.polls.pop(0)
        ):
            super().update()


def run_polls(polls):
    target_view_model = mock.Mock()
    StoppingDataUpdater(target_view_model, threading.Event(), polls).run()
    return target_view_model


def test_failed_poll_shows_unavailable():
    target_view_model = run_polls([{"side_effect": commons.KentBusException("down")}])

    target_view_model.update_unavailable.assert_called_once_with()
    target_view_model.update.assert_not_called()


def test_recovery_with_same_services_replaces_unavailable():
    services = [BusData("44", "Canterbury", "5 mins", "Stagecoach")]
    target_view_model = run_polls(
        [
            {"return_value": services},
            {"side_effect": commons.KentBusException("down")},
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
    model = view_model.ViewModelKentBus_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update_unavailable()

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(
        model, "Data unavailable"
    )


def test_no_service_shown_for_empty_departures():
    stub = mock.Mock()
    model = view_model.ViewModelKentBus_192_32_3_Rows_To_ProtocolBuffers(stub)

    model.update([])

    sections = sent_sections(stub)
    assert len(sections[0].content.pixels) == text_pixel_count(model, "No service.")
