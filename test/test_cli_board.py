import importlib
from unittest import mock

import pytest
from click.testing import CliRunner

# (provider, board command arguments that fail validation)
INVALID_BOARDS = [
    ("national_rail", ["board", "XXX"]),
    ("nexus", ["board", "NOT-A-STOP"]),
    ("ns", ["board", "XXX"]),
    ("sncf", ["board", "00000000"]),
    ("tfl_tube", ["board", "central", "XXX", "w"]),
    ("transilien", ["board", "00000000"]),
]


def invoke_board(cli, args):
    with mock.patch.object(
        cli.board_client, "BoardClient"
    ) as client_class, mock.patch.object(cli.time, "sleep", side_effect=KeyboardInterrupt):
        result = CliRunner().invoke(cli.cli, args)
    return result, client_class.return_value


@pytest.mark.parametrize("provider,args", INVALID_BOARDS)
def test_board_does_not_start_for_invalid_station(provider, args):
    cli = importlib.import_module(f"departure.provider.{provider}.cli")

    result, client = invoke_board(cli, args)

    assert result.exception is None
    client.start.assert_not_called()


def test_ratp_board_does_not_start_for_invalid_station():
    from departure.provider.ratp import cli, commons  # pylint: disable=import-outside-toplevel

    with mock.patch.object(
        cli.ratp, "check_params", side_effect=commons.RatpException("invalid")
    ):
        result, client = invoke_board(cli, ["board", "RB", "999", "A"])

    assert result.exception is None
    client.start.assert_not_called()


def test_nexus_board_passes_stop_code_to_data_updater():
    from departure.provider.nexus import cli, data_updater  # pylint: disable=import-outside-toplevel

    result, client = invoke_board(cli, ["board", "41000010jara"])

    assert result.exception is None
    data_updater_class, arguments = client.start.call_args.args[1:]
    assert data_updater_class is data_updater.DataUpdaterNexusBus
    assert arguments == {"stop_code": "41000010JARA"}
