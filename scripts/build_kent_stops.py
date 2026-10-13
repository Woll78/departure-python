"""Build departure/provider/kent/data/stops.csv from a NaPTAN stops extract.

Usage: python scripts/build_kent_stops.py NAPTAN_STOPS_CSV OUTPUT_CSV
"""

import csv
import sys

BUS_STOP_TYPES = {"BCT", "BCS", "BCQ", "BCE"}


def stop_name(row):
    name = row["CommonName"].strip()
    locality = row["LocalityName"].strip()
    indicator = row["Indicator"].strip()
    if locality:
        name += f", {locality}"
    if indicator:
        name += f" ({indicator})"
    return name


def build_rows(rows):
    stops = [
        (stop_name(row), row["ATCOCode"])
        for row in rows
        if row["Status"] == "active" and row["StopType"] in BUS_STOP_TYPES
    ]
    return [(code, name) for name, code in sorted(stops)]


def main(naptan_path, output_path):
    with open(naptan_path, encoding="utf-8-sig", newline="") as naptan_file:
        rows = build_rows(csv.DictReader(naptan_file))

    with open(output_path, "w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["code", "name"])
        writer.writerows(rows)

    print(f"wrote {len(rows)} stops to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
