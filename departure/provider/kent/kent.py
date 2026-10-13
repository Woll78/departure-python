from typing import List

from departure.provider.nexus.bus_data_model import BusData

from . import api, commons, data

MAX_SEARCH_RESULTS = 50


def check_params(stop_code: str) -> None:
    if stop_code not in data.STATIONS:
        raise commons.KentBusException(f"invalid stop code {stop_code}")


def stations_by_string(string):
    string = str(string).lower().strip()
    results = {}

    for station_id, name in data.STATIONS.items():
        if string in name.lower():
            results[station_id] = name
            if len(results) == MAX_SEARCH_RESULTS:
                break

    return results


def next_services(stop_code: str) -> List[BusData]:
    check_params(stop_code)
    return api.departures(stop_code)
