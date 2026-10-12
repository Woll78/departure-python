from types import SimpleNamespace as NS
from unittest import mock

from departure.provider.national_rail import national_rail


def service(destination="London", calling_points=True, has_destination=True):
    if calling_points:
        cps = NS(
            callingPointList=[
                NS(callingPoint=[NS(locationName="York", st="10:00", et="On time")])
            ]
        )
    else:
        cps = None
    return NS(
        std="09:00",
        etd="On time",
        platform="3",
        destination=NS(location=[NS(locationName=destination)])
        if has_destination
        else NS(location=[]),
        origin=NS(location=[NS(locationName="Newcastle")]),
        operator="LNER",
        subsequentCallingPoints=cps,
    )


def board(*services):
    return NS(trainServices=NS(service=list(services)))


class TestServicesFromStationBoard:
    def test_no_services(self):
        assert (
            national_rail.services_from_station_board_with_details(
                NS(trainServices=None)
            )
            == []
        )

    def test_service_fields(self):
        result = national_rail.services_from_station_board_with_details(
            board(service())
        )
        assert result == [
            {
                "std": "09:00",
                "etd": "On time",
                "platform": "3",
                "destination_location_name": "London",
                "origin_location_name": "Newcastle",
                "operator": "LNER",
                "calling_points": [
                    {"location_name": "York", "st": "10:00", "et": "On time"}
                ],
            }
        ]

    def test_service_without_calling_points_does_not_wipe_the_board(self):
        result = national_rail.services_from_station_board_with_details(
            board(service("A"), service("B", calling_points=False), service("C"))
        )
        assert [s["destination_location_name"] for s in result] == ["A", "B", "C"]
        assert result[1]["calling_points"] == []

    def test_malformed_service_is_skipped_others_kept(self):
        result = national_rail.services_from_station_board_with_details(
            board(service("A"), service(has_destination=False), service("C"))
        )
        assert [s["destination_location_name"] for s in result] == ["A", "C"]


def test_next_services_does_not_scan_stations():
    with mock.patch.object(national_rail, "check_params"), mock.patch.object(
        national_rail.api,
        "get_departure_board_with_details",
        return_value=board(service()),
    ), mock.patch.object(national_rail, "stations_by_string") as scan:
        assert len(national_rail.next_services("NCL")) == 1
    scan.assert_not_called()
