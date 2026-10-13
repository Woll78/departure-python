"""
CLI for Kent bus
"""

import time
import logging

import click

from departure.board import board_client

from . import ui, kent, commons, view_model, data_updater

ONE_DAY_IN_SECONDS = 60 * 60 * 24
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """
    Information and departures for bus services in Kent (UK).
    """


@click.command()
@click.argument("query_string")
def search(query_string):
    """Search for bus stops containing QUERY_STRING."""
    ui.list_stations(kent.stations_by_string(query_string))


@click.command(name="next")
@click.argument("stop_code")
def next_services(stop_code):
    """
    Get next services at stop STOP_CODE.

    Use search to find the STOP_CODE for a stop.
    """
    try:
        services = kent.next_services(stop_code.upper())
    except commons.KentBusException as e:
        print(f"error: {str(e)}")
        return

    ui.list_services(services)


@click.command(name="board")
@click.argument("stop_code")
def start_board(stop_code):
    """
    Update a departure board with services at stop STOP_CODE.

    Use search to find the STOP_CODE for a stop.
    """
    stop_code = stop_code.upper()

    try:
        kent.check_params(stop_code)
    except commons.KentBusException as e:
        logger.warning("error: %s", str(e))
        return

    board_client_instance = board_client.BoardClient()
    board_client_instance.start(
        view_model.ViewModelKentBus_192_32_3_Rows_To_ProtocolBuffers,
        data_updater.DataUpdaterKentBus,
        {"stop_code": stop_code},
    )

    # run until interrupt
    try:
        while True:
            time.sleep(ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        logger.info("received interrupt")
        board_client_instance.stop()


cli.add_command(search)
cli.add_command(next_services)
cli.add_command(start_board)

if __name__ == "__main__":
    cli()
