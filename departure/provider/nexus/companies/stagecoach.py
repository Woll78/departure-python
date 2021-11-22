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
        response = requests.post(url, data=json.dumps(payload), headers=headers)
     #   print(response.content)

        bus_data = json.loads(response.content)  

        # print(bus_data)      
        departure_time = json_extract(bus_data, 'expectedDepartureTime')
        number = json_extract(bus_data, 'lineRef')
        destination = json_extract(bus_data, 'destinationDisplay')        
        cancelled = json_extract(bus_data, 'cancelled')             

        bus_objects = []

        for i in range(len(departure_time)):
            journey = BusData(number[i], destination[i], calculate_departure_time(departure_time[i]), "Stagecoach")
            bus_objects.append(journey)

        return bus_objects


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