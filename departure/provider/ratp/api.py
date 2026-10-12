import os

import requests
import zeep.exceptions
from zeep import Client

from . import commons

WSDL_FILENAME = "data/Wsiv.wsdl"


def soap_client():
    return Client(wsdl=os.path.join(os.path.dirname(__file__), WSDL_FILENAME))


def get_lines_realtime_realm():
    # may fail with requests.exceptions.ConnectionError
    return soap_client().service.getLines(line={"realm": "r"})


def get_lines_by_code(code_query):
    return soap_client().service.getLines(
        line={"code": f"*{code_query}*", "realm": "r"}
    )


def get_directions(line_id):
    return soap_client().service.getDirections(line={"id": line_id})


def get_stations_by_line(line_id):
    return soap_client().service.getStations(station={"line": {"id": line_id}}).stations


def get_stations_by_name(name_query):
    return soap_client().service.getStations(
        station={"name": name_query, "line": {"realm": "r"}}
    )


def get_missions_next(line_id, station_id, direction_sens):
    try:
        return soap_client().service.getMissionsNext(
            station={"line": {"id": line_id}, "id": station_id},
            direction={"sens": direction_sens},
        )
    except (requests.exceptions.RequestException, zeep.exceptions.Error) as e:
        raise commons.RatpException(f"RATP API request error: {e}") from e
