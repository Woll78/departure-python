import logging
from typing import List, Any

from . import data, commons, api

logger = logging.getLogger(__name__)


def check_params(station_code: str) -> None:
    stations = data.STATIONS

    if station_code is not None:
        try:
            _ = stations[station_code]
        except Exception:
            raise commons.NationalRailException(
                f"invalid station code {station_code}"
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


def services_from_station_board_with_details(station_board_with_details):
    services = []

    # end here if no services
    if station_board_with_details.trainServices is None:
        return services

    for station_board_service in station_board_with_details.trainServices.service:
        try:
            services.append(service_from_station_board_service(station_board_service))
        except (AttributeError, IndexError, TypeError):
            # skip the malformed service, keep the rest of the board
            logger.warning("skipping malformed service", exc_info=True)

    return services


def service_from_station_board_service(station_board_service):
    # cancelled or terminating services have no calling points
    if station_board_service.subsequentCallingPoints is None:
        calling_points = []
    else:
        calling_points = [
            {"location_name": cp.locationName, "st": cp.st, "et": cp.et}
            for cp in station_board_service.subsequentCallingPoints.callingPointList[
                0
            ].callingPoint
        ]

    return {
        "std": station_board_service.std,
        "etd": station_board_service.etd,
        "platform": station_board_service.platform,
        "destination_location_name": station_board_service.destination.location[
            0
        ].locationName,
        "origin_location_name": station_board_service.origin.location[0].locationName,
        "operator": station_board_service.operator,
        "calling_points": calling_points,
    }


def next_services(station_code: str) -> List[Any]:
    # check parameters
    check_params(station_code)

    # get trains departing from station
    station_board_with_details = api.get_departure_board_with_details(station_code)
    services = services_from_station_board_with_details(station_board_with_details)

    return services
