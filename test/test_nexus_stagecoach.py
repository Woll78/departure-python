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


class TestCalculateDelayMinutes:
    aimed = "2026-10-12T10:00:00Z"

    def test_on_time(self):
        assert stagecoach.calculate_delay_minutes(self.aimed, self.aimed) == 0

    def test_under_a_minute_late_rounds_down(self):
        assert (
            stagecoach.calculate_delay_minutes(self.aimed, "2026-10-12T10:00:59Z") == 0
        )

    def test_one_minute_late(self):
        assert (
            stagecoach.calculate_delay_minutes(self.aimed, "2026-10-12T10:01:00Z") == 1
        )

    def test_four_minutes_late(self):
        assert (
            stagecoach.calculate_delay_minutes(self.aimed, "2026-10-12T10:04:48Z") == 4
        )

    def test_early_is_not_negative(self):
        assert (
            stagecoach.calculate_delay_minutes(self.aimed, "2026-10-12T09:58:00Z") == 0
        )

    def test_missing_or_bad_aimed_time_counts_as_on_time(self):
        assert stagecoach.calculate_delay_minutes(None, self.aimed) == 0
        assert stagecoach.calculate_delay_minutes("", self.aimed) == 0
        assert stagecoach.calculate_delay_minutes("nonsense", self.aimed) == 0


class TestDelayInFetch:
    def test_delay_comes_from_aimed_vs_expected(self):
        body = response_with(
            {
                "monitoredVehicleJourney": {
                    "lineRef": "44",
                    "destinationDisplay": "Canterbury",
                    "monitoredCall": {
                        "aimedDepartureTime": "2099-10-12T10:00:00Z",
                        "expectedDepartureTime": "2099-10-12T10:05:00Z",
                    },
                }
            },
            journey("2099-10-12T10:10:00Z", "43", "Canterbury"),  # no aimed time
        )
        fake = mock.Mock(content=json.dumps(body).encode())
        with mock.patch.object(stagecoach.requests, "post", return_value=fake):
            buses = stagecoach.Stagecoach().fetch("stop")

        assert [(b.number, b.delay_minutes, b.is_delayed) for b in buses] == [
            ("44", 5, True),
            ("43", 0, False),
        ]
