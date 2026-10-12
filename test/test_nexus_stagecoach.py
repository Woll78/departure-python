import json
from unittest import mock

from departure.provider.nexus.companies import stagecoach


def journey(time, number, destination=None, cancelled=None):
    node = {
        "monitoredVehicleJourney": {
            "lineRef": number,
            "monitoredCall": {"expectedDepartureTime": time},
        }
    }
    if destination is not None:
        node["monitoredVehicleJourney"]["destinationDisplay"] = destination
    if cancelled is not None:
        node["monitoredVehicleJourney"]["cancelled"] = cancelled
    return node


def response_with(*journeys):
    return {"stopMonitors": {"stopMonitor": [{"monitoredStopVisit": list(journeys)}]}}


class TestExtractJourneys:
    def test_fields_stay_together(self):
        result = stagecoach.extract_journeys(
            response_with(
                journey("2026-10-12T10:00:00Z", "10", "Newcastle"),
                journey("2026-10-12T10:10:00Z", "20", "Gateshead"),
            )
        )
        assert [(j["number"], j["destination"]) for j in result] == [
            ("10", "Newcastle"),
            ("20", "Gateshead"),
        ]

    def test_missing_destination_does_not_shift_later_journeys(self):
        result = stagecoach.extract_journeys(
            response_with(
                journey("2026-10-12T10:00:00Z", "10"),
                journey("2026-10-12T10:10:00Z", "20", "Gateshead"),
            )
        )
        assert [(j["number"], j["destination"]) for j in result] == [
            ("10", ""),
            ("20", "Gateshead"),
        ]

    def test_cancelled_flag(self):
        result = stagecoach.extract_journeys(
            response_with(
                journey("2026-10-12T10:00:00Z", "10", "A", cancelled=True),
                journey("2026-10-12T10:10:00Z", "20", "B", cancelled=False),
            )
        )
        assert [j["cancelled"] for j in result] == [True, False]

    def test_empty_response(self):
        assert stagecoach.extract_journeys({}) == []
        assert stagecoach.extract_journeys(response_with()) == []


class TestFetch:
    def test_cancelled_buses_are_dropped_and_request_has_timeout(self):
        body = response_with(
            journey("2099-10-12T10:00:00Z", "10", "A", cancelled=True),
            journey("2099-10-12T10:10:00Z", "20", "B"),
        )
        fake = mock.Mock(content=json.dumps(body).encode())
        with mock.patch.object(
            stagecoach.requests, "post", return_value=fake
        ) as post:
            buses = stagecoach.Stagecoach().fetch("stop")

        assert [b.number for b in buses] == ["20"]
        assert post.call_args.kwargs["timeout"] == 10
        fake.raise_for_status.assert_called_once()
