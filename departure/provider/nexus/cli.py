"""
CLI for Nexus bus
"""

import threading
import time
import logging

import click

from departure.board import board_client

from . import ui, nexus, commons, view_model, data_updater

ONE_DAY_IN_SECONDS = 60 * 60 * 24
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """
    Information and departures for Nexus bus services (UK).
    """


@click.command()
@click.argument("query_string")
def search(query_string):
    """Search for bus stops containing QUERY_STRING."""
    stations = nexus.stations_by_string(query_string)
    ui.list_stations(stations)


@click.command(name="next")
@click.argument("station_id")
def next_services(station_id):
    """
    Get next services at stop STATION_ID.

    Use search to find the STATION_ID for a stop.
    """

    services = nexus.next_services(station_id.upper())
    ui.list_services(services)


@click.command(name="board")
@click.argument("station_id")
def start_board(station_id):
    """
    Update a departure board with services at station STATION_ID.

    Use search to find the STATION_ID for a station.
    """

    station_id = station_id.upper()

    try:
        nexus.check_params(station_id)
    except commons.NexusBusException as e:
        logger.warning("error: %s", str(e))

    # start board
    board_client_instance = board_client.BoardClient()

    threading.Thread(
        target=board_client_instance.run,
        args=[
            view_model.ViewModelNexusBus_192_32_3_Rows_To_ProtocolBuffers,
            data_updater.DataUpdaterNexusBus,
            {
                "station_id": station_id,
            },
        ],
    ).start()

    # run until interrupt
    try:
        while True:
            time.sleep(ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        logger.info("received interrupt")
        board_client_instance.running = False


cli.add_command(search)
cli.add_command(next_services)
cli.add_command(start_board)

if __name__ == "__main__":
    cli()
