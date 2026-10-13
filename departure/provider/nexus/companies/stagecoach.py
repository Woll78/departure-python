import datetime as datetime
import json
import requests

from departure.provider.nexus.bus_data_model import BusData

class Stagecoach:

    def fetch(self, stopId):

        url = 'https://api.stagecoachbus.com/adc/stop-monitor'
        headers = {
                    "Connection": "keep-alive",
                    "Origin": "https://www.stagecoachbus.com/",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
                    "Content-Type": "application/json",
                    "Accept": "*/*",
                    "Referer": "https://www.stagecoachbus.com/",
                    "Accept-Encoding": "gzip,deflate,br",
                    "sec-ch-ua": '"Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"',
                    "sec-ch-ua-mobile": '?0',                    
                    "X-SC-apiKey": 'ukbusprodapi_7k8K536tNsPH#!',
                    "X-SC-securityMethod": 'API',
                    "sec-ch-ua-platform": 'Windows',                    
                }
        # Adding empty header as parameters are being sent in payload
        #payload = {"StopMonitorRequest":{"header":{"retailOperation":"","channel":"","ipAddress":""},"lookAheadMinutes":60,"stopMonitorQueries":{"stopMonitorQuery":[{"stopPointLabel":"41000010JARB","servicesFilters":{"servicesFilter":[]}}]}}}
        payload = {"StopMonitorRequest":{"header":{"retailOperation":"","channel":"","ipAddress":""},"lookAheadMinutes":60,"stopMonitorQueries":{"stopMonitorQuery":[{"stopPointLabel":stopId,"servicesFilters":{"servicesFilter":[]}}]}}}
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
        response.raise_for_status()

        bus_data = json.loads(response.content)

        return [
            BusData(
                j['number'],
                j['destination'],
                calculate_departure_time(j['time']),
                "Stagecoach",
                calculate_delay_minutes(j['aimed'], j['time']),
            )
            for j in extract_journeys(bus_data)
            if not j['cancelled']
        ]


def extract_journeys(obj):
    """Return one dict per journey, keeping each journey's fields together.

    A journey is the lowest node whose subtree holds both an
    expectedDepartureTime and a lineRef, so a journey missing a field can't
    shift the fields of the journeys after it.
    """
    if isinstance(obj, dict):
        children = obj.values()
    elif isinstance(obj, list):
        children = obj
    else:
        return []

    journeys = [j for child in children for j in extract_journeys(child)]
    if journeys:
        return journeys

    times = json_extract(obj, 'expectedDepartureTime')
    numbers = json_extract(obj, 'lineRef')
    if not times or not numbers:
        return []

    aimed_times = json_extract(obj, 'aimedDepartureTime')
    destinations = json_extract(obj, 'destinationDisplay')
    cancelled = json_extract(obj, 'cancelled')
    return [{
        'time': times[0],
        'aimed': aimed_times[0] if aimed_times else None,
        'number': numbers[0],
        'destination': destinations[0] if destinations else '',
        'cancelled': bool(cancelled) and str(cancelled[0]).lower() == 'true',
    }]


def calculate_delay_minutes(aimed_time, expected_time):
    """Whole minutes the bus runs behind its timetable; 0 if on time, early or unknown."""
    if not aimed_time:
        return 0

    time_format = '%Y-%m-%dT%H:%M:%SZ'
    try:
        delay = (
            datetime.datetime.strptime(expected_time, time_format)
            - datetime.datetime.strptime(aimed_time, time_format)
        )
    except ValueError:
        return 0

    return max(0, int(delay.total_seconds() / 60))


def calculate_departure_time(departure_time):

    utc_now = datetime.datetime.utcnow()
    utc_leave = datetime.datetime.strptime(departure_time, '%Y-%m-%dT%H:%M:%SZ')
    timeDiff = utc_leave - utc_now
    timeDiff_minutes = int(timeDiff.total_seconds() / 60)

    if timeDiff_minutes == 0:
        return 'Due'
    elif timeDiff_minutes == 1:
        return '1 min'
    else: 
        return str(timeDiff_minutes) +' mins'


def json_extract(obj, key):
    """Recursively fetch values from nested JSON."""
    arr = []

    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    values = extract(obj, arr, key)
    return values