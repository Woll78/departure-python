import os
from typing import ChainMap
from departure.provider.nexus.companies.gone import GONE
from departure.provider.nexus.companies.stagecoach import Stagecoach


from . import commons

go_north_east = GONE()
stagecoach = Stagecoach()

def departures(station_id: str):
    go_north_east = GONE()
    stagecoach = Stagecoach()

    combined_operators = ChainMap(go_north_east.fetch(station_id), stagecoach.fetch(station_id))

    return sorted(combined_operators, key=lambda x: x.time)