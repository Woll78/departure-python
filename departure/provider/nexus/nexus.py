from typing import List, Any

from departure.provider.nexus.bus_data_model import BusData

from . import data, commons, api


def check_params(stop_code: str) -> None:
    stations = data.STATIONS

    if stop_code is not None:
        try:
            _ = stations[stop_code]
        except Exception:
            raise commons.NexusBusException(
                f"invalid stop code {stop_code}"
            ) from Exception


def stations_by_string(string):
    string = str(string).lower().strip()
    results = {}
    stations = data.STATIONS

    # iterate over stations
    for station_id in stations:
        # match?
        if string in stations[station_id].lower():
            results[station_id] = stations[station_id]

    return results


def departures(stop_code: str) -> List[BusData]:
    check_params(stop_code)

    departures = api.departures(stop_code)

    return departures
 

def next_services(stop_code: str) -> List[BusData]:

    # check parameters
    check_params(stop_code)

    # get busses departing from stop
    departures = api.departures(stop_code)

    return departures
