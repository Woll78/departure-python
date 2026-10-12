import os
from typing import ChainMap

import requests

from departure.provider.nexus.companies.gone import GONE
from departure.provider.nexus.companies.stagecoach import Stagecoach


from . import commons

go_north_east = GONE()
stagecoach = Stagecoach()

def departures(station_id: str):
    go_north_east = GONE()
    stagecoach = Stagecoach()

    # combined_operators = ChainMap(go_north_east.fetch(station_id), stagecoach.fetch(station_id))
    combined_operators = []

    # one operator failing must fail the poll: showing the other operator's
    # buses alone could show "No service" or the wrong next bus
    try:
        gone_data = go_north_east.fetch(station_id)
        stagecoach_data = stagecoach.fetch(station_id)
    except requests.exceptions.RequestException as e:
        raise commons.NexusBusException(f"Nexus bus data request error: {e}") from e

    if gone_data is not None:
       combined_operators.extend(gone_data)

    if stagecoach_data is not None:
       combined_operators.extend(stagecoach_data)  

    return sorted(combined_operators, key=lambda x: x.time)