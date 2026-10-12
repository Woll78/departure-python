import threading
import os
import logging

import grpc

import departure.board.departure_pb2_grpc as departure_pb2_grpc

from . import data_updater, view_model

logger = logging.getLogger(__name__)


class BoardGate:
    """
    Forwards calls to a view model until closed, then drops them.

    A stopped data updater may still be in the middle of a poll (HTTP or SOAP
    call); closing the gate stops that poll from reaching the board once a
    new client has taken over.
    """

    def __init__(self, target_view_model: view_model.ViewModel):
        self._view_model = target_view_model
        self._lock = threading.Lock()
        self._open = True

    def __getattr__(self, name):
        method = getattr(self._view_model, name)

        def forward(*args, **kwargs):
            with self._lock:
                if self._open:
                    return method(*args, **kwargs)
            return None

        return forward

    def close(self) -> None:
        # waits for any call in progress, so nothing reaches the board after
        with self._lock:
            self._open = False


class BoardClient:
    def __init__(self):
        self._lock = threading.Lock()
        self._channel = None
        self._view_model = None
        self._gate = None
        self._end_event = None

    @property
    def running(self) -> bool:
        return self._gate is not None

    def start(
        self,
        view_model_class: view_model.ViewModel,
        data_updater_class: data_updater.DataUpdater,
        data_updater_extra_arguments: dict,
    ) -> None:
        with self._lock:
            # replace any client already running
            self._stop()

            # set departure board server
            if "DEPARTURE_BOARD_SERVER" in os.environ:
                departure_board_server = os.environ["DEPARTURE_BOARD_SERVER"]
                server_info_str = "DEPARTURE_BOARD_SERVER env var set - "
            else:
                server_info_str = "DEPARTURE_BOARD_SERVER env var not set - "
                departure_board_server = "127.0.0.1"
            logger.info(
                "%s using %s as server", server_info_str, departure_board_server
            )

            # open channel to board server
            self._channel = grpc.insecure_channel(f"{departure_board_server}:50051")

            # set up client parameters
            board_manager_stub = departure_pb2_grpc.BoardManagerStub(self._channel)
            self._view_model = view_model_class(board_manager_stub)
            self._gate = BoardGate(self._view_model)
            self._end_event = threading.Event()

            # init and run updater thread
            data_updater_thread = data_updater_class(
                target_view_model=self._gate,
                data_refresh_delay_in_s=15,
                end_event=self._end_event,
                **data_updater_extra_arguments,
            )
            # a poll in flight must not keep the process alive on exit
            data_updater_thread.daemon = True
            data_updater_thread.start()

    def stop(self) -> None:
        with self._lock:
            self._stop()

    def _stop(self) -> None:
        if self._gate is None:
            return

        logger.info("stopping")

        # the updater thread ends after its current poll, if any; the closed
        # gate stops that poll reaching the board, so there's no need to wait
        self._end_event.set()
        self._gate.close()

        # clear board
        self._view_model.update(None)
        self._channel.close()

        self._channel = None
        self._view_model = None
        self._gate = None
        self._end_event = None
