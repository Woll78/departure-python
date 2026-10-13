from typing import List

import requests

from departure.provider.nexus.bus_data_model import BusData
from departure.provider.nexus.companies.stagecoach import Stagecoach

from . import commons

# to add an operator: write a class with fetch(stop_id) -> list of BusData and
# append an instance here
OPERATORS = [Stagecoach()]


def departures(stop_code: str) -> List[BusData]:
    combined = []

    # one operator failing must fail the poll: showing the other operators'
    # buses alone could show "No service" or the wrong next bus
    try:
        for operator in OPERATORS:
            buses = operator.fetch(stop_code)
            if buses:
                combined.extend(buses)
    except requests.exceptions.RequestException as e:
        raise commons.KentBusException(f"Kent bus data request error: {e}") from e

    return sorted(combined, key=lambda bus: bus.time)
