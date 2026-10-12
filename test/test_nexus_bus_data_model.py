import datetime
from unittest import mock

from departure.provider.nexus import bus_data_model
from departure.provider.nexus.bus_data_model import BusData, prepare_departure_time


def _frozen_now(now):
    class FrozenDatetime(datetime.datetime):
        @classmethod
        def today(cls):
            return now

    return mock.patch.object(bus_data_model.datetime, "datetime", FrozenDatetime)


class TestPrepareDepartureTime:
    now = datetime.datetime(2026, 10, 12, 10, 0, 0)

    def test_clock_time_later_today(self):
        with _frozen_now(self.now):
            assert prepare_departure_time("14:35") == datetime.datetime(
                2026, 10, 12, 14, 35
            )

    def test_clock_time_already_passed_rolls_to_tomorrow(self):
        with _frozen_now(self.now):
            assert prepare_departure_time("00:05") == datetime.datetime(
                2026, 10, 13, 0, 5
            )

    def test_due(self):
        with _frozen_now(self.now):
            assert prepare_departure_time("Due") == self.now

    def test_minutes(self):
        with _frozen_now(self.now):
            assert prepare_departure_time("5 mins") == self.now + datetime.timedelta(
                minutes=5
            )

    def test_negative_minutes_treated_as_due(self):
        with _frozen_now(self.now):
            assert prepare_departure_time("-1 mins") == self.now

    def test_no_digits_sorts_last(self):
        assert prepare_departure_time("Cancelled") == datetime.datetime.max
        assert prepare_departure_time("") == datetime.datetime.max


class TestBusDataSorting:
    def test_mixed_literals_sort_without_error(self):
        buses = [
            BusData("1", "A", "Cancelled", "x"),
            BusData("2", "B", "14:35", "x"),
            BusData("3", "C", "Due", "x"),
        ]
        ordered = [b.number for b in sorted(buses, key=lambda b: b.time)]
        assert ordered[-1] == "1"
