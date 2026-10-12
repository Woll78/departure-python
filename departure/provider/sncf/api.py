import json
import os
import logging

import requests

from . import commons

logger = logging.getLogger(__name__)


def api_request(url: str):
    commons.check_env_vars()

    try:
        response = requests.get(
            url,
            timeout=15,
            # http://doc.navitia.io/#authentication
            auth=(os.environ["SNCF_KEY"], ""),
        )
    except requests.exceptions.Timeout as e:
        raise commons.SncfException("SNCF API HTTP request timed out") from e
    except requests.exceptions.RequestException as e:
        raise commons.SncfException(f"SNCF API HTTP request error: {e}") from e

    # process response
    if response.status_code == 200:
        return json.loads(response.content.decode("utf-8"))

    raise commons.SncfException(
        f"SNCF API request failed, HTTP response: {response.status_code}"
    )


def departures(station_id):
    url = (
        "https://api.navitia.io/v1/coverage/sncf/stop_areas/"
        f"stop_area:OCE:SA:{station_id}/departures"
    )
    return api_request(url)


def disruptions(disruption_id):
    url = f"https://api.navitia.io/v1/coverage/sncf/disruptions/{disruption_id}/"
    return api_request(url)


def vehicle_journeys(vehicle_journey_id):
    url = f"https://api.navitia.io/v1/coverage/sncf/vehicle_journeys/{vehicle_journey_id}/"
    return api_request(url)
