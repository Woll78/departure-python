import xml.etree.ElementTree as ET
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
            auth=(os.environ["TRANSILIEN_USER"], os.environ["TRANSILIEN_PASSWORD"]),
        )
    except requests.exceptions.Timeout as e:
        raise commons.TransilienException(
            "Transilien API HTTP request timed out"
        ) from e
    except requests.exceptions.RequestException as e:
        raise commons.TransilienException(
            f"Transilien API HTTP request error: {e}"
        ) from e

    # process response
    if response.status_code == 200:
        return ET.fromstring(response.content.decode("utf-8"))

    raise commons.TransilienException(
        f"Transilien API request failed, HTTP response: {response.status_code}"
    )


def departures(station_id):
    url = f"https://api.transilien.com/gare/{station_id}/depart/"
    return api_request(url)
