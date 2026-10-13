import csv
import pathlib

STATION_CODES_FILENAME = "data/stops.csv"


def _stations(station_codes_filename):
    station_codes_path = pathlib.Path(__file__).parent / station_codes_filename

    with station_codes_path.open(encoding="utf-8", newline="") as stations_codes_file:
        reader = csv.reader(stations_codes_file)
        next(reader, None)  # skip header row
        return {row[0]: row[1] for row in reader}


STATIONS = _stations(STATION_CODES_FILENAME)
