import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).parent.parent

_spec = importlib.util.spec_from_file_location(
    "build_kent_stops", ROOT / "scripts" / "build_kent_stops.py"
)
build_kent_stops = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_kent_stops)


def row(code="2400A045760A", name="Stone Cross", locality="Sandwich",
        indicator="SW-bound", status="active", stop_type="BCT"):
    return {
        "ATCOCode": code,
        "CommonName": name,
        "LocalityName": locality,
        "Indicator": indicator,
        "Status": status,
        "StopType": stop_type,
    }


def test_stop_name_includes_locality_and_indicator():
    assert build_kent_stops.stop_name(row()) == "Stone Cross, Sandwich (SW-bound)"


def test_stop_name_omits_empty_parts():
    assert build_kent_stops.stop_name(row(locality="", indicator="")) == "Stone Cross"


def test_build_rows_keeps_only_active_bus_stops():
    rows = [
        row(code="A"),
        row(code="B", status="inactive"),
        row(code="C", stop_type="RSE"),  # rail station entrance
        row(code="D", stop_type="BCS"),  # bus station bay
    ]
    assert [code for code, _ in build_kent_stops.build_rows(rows)] == ["A", "D"]


def test_build_rows_sorted_by_name():
    rows = [row(code="B", name="Zebra Road"), row(code="A", name="Abbey Road")]
    assert [name.split(",")[0] for _, name in build_kent_stops.build_rows(rows)] == [
        "Abbey Road",
        "Zebra Road",
    ]
