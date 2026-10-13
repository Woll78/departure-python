from unittest import mock

from click.testing import CliRunner
from fastapi.testclient import TestClient

from departure.cli import client
from departure.provider.kent import cli, commons, data_updater, view_model
from departure.web import api_server

STOP_CODE = "2400A045760A"


def test_search_route_finds_stone_cross():
    response = TestClient(api_server.app).get("/kent/search/stone cross, sandwich")

    assert response.json()[STOP_CODE] == "Stone Cross, Sandwich (SW-bound)"


def test_start_client_route_starts_board():
    board_client = mock.Mock()
    with mock.patch.object(api_server.app, "board_client", board_client):
        response = TestClient(api_server.app).post(
            "/kent/start-client", json={"code": STOP_CODE}
        )

    assert response.json() == {"status": "OK"}
    board_client.start.assert_called_once_with(
        view_model.ViewModelKentBus_192_32_3_Rows_To_ProtocolBuffers,
        data_updater.DataUpdaterKentBus,
        {"stop_code": STOP_CODE},
    )


def test_start_client_route_rejects_unknown_stop():
    board_client = mock.Mock()
    with mock.patch.object(api_server.app, "board_client", board_client):
        response = TestClient(api_server.app).post(
            "/kent/start-client", json={"code": "nope"}
        )

    assert response.json()["status"] == "error"
    board_client.start.assert_not_called()


def test_cli_is_registered_as_kent():
    assert "kent" in client.entry_point.commands


def test_cli_search_lists_stop():
    result = CliRunner().invoke(cli.cli, ["search", "stone cross, sandwich"])

    assert STOP_CODE in result.output


def test_cli_next_reports_api_failure():
    with mock.patch.object(
        cli.kent, "next_services", side_effect=commons.KentBusException("API down")
    ):
        result = CliRunner().invoke(cli.cli, ["next", STOP_CODE])

    assert result.exception is None
    assert "error: API down" in result.output
