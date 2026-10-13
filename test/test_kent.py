from unittest import mock

import pytest
import requests

from departure.provider.kent import api, commons, data, kent
from departure.provider.nexus.bus_data_model import BusData

STOP_CODE = "2400A045760A"


# stops data


def test_stone_cross_is_in_stops_data():
    assert data.STATIONS[STOP_CODE] == "Stone Cross, Sandwich (SW-bound)"


# search


def test_search_is_case_insensitive_and_matches_locality():
    assert STOP_CODE in kent.stations_by_string("SANDWICH")
    assert STOP_CODE in kent.stations_by_string("stone cross")


def test_search_results_are_capped():
    stations = {str(i): f"Stop {i}" for i in range(500)}
    with mock.patch.object(data, "STATIONS", stations):
        assert len(kent.stations_by_string("stop")) == kent.MAX_SEARCH_RESULTS


# stop code check


def test_check_params_accepts_known_stop():
    kent.check_params(STOP_CODE)


def test_check_params_rejects_unknown_stop():
    with pytest.raises(commons.KentBusException, match="invalid stop code"):
        kent.check_params("nope")


# api: operators merged, any failure fails the poll


def operator(buses=None, error=None):
    fake = mock.Mock()
    if error:
        fake.fetch.side_effect = error
    else:
        fake.fetch.return_value = buses
    return fake


def test_next_services_combines_operators_sorted_by_time():
    later = BusData("44", "Canterbury", "10 mins", "Stagecoach")
    sooner = BusData("E1", "Dover", "2 mins", "Other")
    with mock.patch.object(
        api, "OPERATORS", [operator([later]), operator([sooner])]
    ):
        assert kent.next_services(STOP_CODE) == [sooner, later]


def test_next_services_ignores_operator_with_no_data():
    bus = BusData("44", "Canterbury", "10 mins", "Stagecoach")
    with mock.patch.object(api, "OPERATORS", [operator(None), operator([bus])]):
        assert kent.next_services(STOP_CODE) == [bus]


@pytest.mark.parametrize("failing_index", [0, 1])
def test_next_services_raises_when_an_operator_fails(failing_index):
    bus = BusData("44", "Canterbury", "10 mins", "Stagecoach")
    operators = [operator([bus]), operator([bus])]
    operators[failing_index] = operator(error=requests.exceptions.ConnectionError())
    with mock.patch.object(api, "OPERATORS", operators):
        with pytest.raises(commons.KentBusException):
            kent.next_services(STOP_CODE)


def test_next_services_rejects_invalid_stop_before_calling_operators():
    fake = operator([])
    with mock.patch.object(api, "OPERATORS", [fake]):
        with pytest.raises(commons.KentBusException):
            kent.next_services("nope")
    fake.fetch.assert_not_called()


# ui: services listed without the operator


def test_list_services_omits_operator(capsys):
    from departure.provider.kent import ui

    ui.list_services([BusData("44", "Canterbury", "10 mins", "Stagecoach")])

    assert capsys.readouterr().out == "1st 44 Canterbury 10 mins\n"


# board display


def test_kent_destination_allows_one_more_character_than_nexus():
    from departure.provider.kent.view_model import (
        ViewModelKentBus_192_32_3_Rows_To_ProtocolBuffers,
    )
    from departure.provider.nexus.view_model import ViewModelNexusBus_192_32

    assert ViewModelNexusBus_192_32.DESTINATION_MAX_WIDTH == 95
    assert (
        ViewModelKentBus_192_32_3_Rows_To_ProtocolBuffers.DESTINATION_MAX_WIDTH == 101
    )


def test_kent_long_destination_is_cut_off_later_than_nexus():
    from departure.provider.kent.view_model import (
        ViewModelKentBus_192_32_3_Rows_To_ProtocolBuffers,
    )
    from departure.provider.nexus.view_model import ViewModelNexusBus_192_32

    bus = BusData("1", "W" * 40, "2 mins", "Operator")

    nexus_pixels, _ = ViewModelNexusBus_192_32().pixels_single_line(bus, "1st")
    kent_pixels, _ = ViewModelKentBus_192_32_3_Rows_To_ProtocolBuffers(
        mock.Mock()
    ).pixels_single_line(bus, "1st")

    # the extra character is drawn, so Kent has more lit pixels
    assert len(kent_pixels) > len(nexus_pixels)


def test_delayed_bus_time_is_red_and_on_time_bus_time_is_green():
    from departure.provider.nexus.view_model import ViewModelNexusBus_192_32

    view_model = ViewModelNexusBus_192_32()
    red, green = (255, 0, 0), (0, 255, 0)

    late_pixels, _ = view_model.pixels_single_line(
        BusData("44", "Canterbury", "10 mins", "Stagecoach", delay_minutes=1), "1st"
    )
    on_time_pixels, _ = view_model.pixels_single_line(
        BusData("44", "Canterbury", "10 mins", "Stagecoach"), "1st"
    )

    late_colours = {colour for _, _, colour in late_pixels}
    on_time_colours = {colour for _, _, colour in on_time_pixels}
    assert red in late_colours and green not in late_colours
    assert green in on_time_colours and red not in on_time_colours
