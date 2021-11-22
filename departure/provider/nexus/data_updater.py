import time
import threading
import logging

import departure.board.data_updater as data_updater
from departure.commons.log import log_function_stdout_to_debug
from . import nexus, view_model, ui

logger = logging.getLogger(__name__)


class DataUpdaterNexusBus(data_updater.DataUpdater):
    def __init__(
        self,
        target_view_model: view_model.ViewModelNexusBus,
        data_refresh_delay_in_s: int,
        end_event: threading.Event,
        stop_code: str,
    ):
        super().__init__(target_view_model, data_refresh_delay_in_s, end_event)
        self.stop_code = stop_code
        self.services = None

    def update(self):
        update_start_time = time.monotonic()
        logger.info("data refresh started at %s", update_start_time)

        try:
            services = nexus.next_services(self.stop_code)

            # debugging: capture list of services to string, then log
            log_function_stdout_to_debug(logger, ui.list_services, services)

            # update board only if there were changes
            if services == self.services:
                logger.info("no change - no update sent to board")
            else:
                self.view_model.update(services)
                self.services = services

        except ConnectionError:
            logger.warning(
                "connection to Nexus Bus failed after %s",
                time.monotonic() - update_start_time,
            )

        logger.info("data refresh duration %s", time.monotonic() - update_start_time)
