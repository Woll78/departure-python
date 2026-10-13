"""
UI for Kent bus
"""

import departure.commons.helpers as helpers
from departure.provider.nexus.ui import list_stations  # noqa: F401


def list_services(services):
    for i, service in enumerate(services):
        print(
            f"{helpers.ordinal_en(i + 1)} {service.number} "
            f"{service.destination} {service.timeLiteral}"
        )
