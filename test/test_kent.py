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
