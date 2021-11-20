"""
UI for Nexus Bus
"""

from tabulate import tabulate

import departure.commons.helpers as helpers


def list_stations(stops):
    print(
        tabulate(
            [
                [station[0], station[1]]
                for station in sorted(stops.items(), key=lambda k: k[1])
            ],
            headers=["id", "name"],
        )
    )


def list_services(services):
    for i, service in enumerate(services):
        print(
            f"{helpers.ordinal_en(i + 1)} {service.number} "
            f"{service.destination} ({service.operator}) "
            f"{service.timeLiteral}"
        )
