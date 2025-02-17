import logging

import grpc

import departure.board.view_model as view_model
import departure.board.contents as contents

import departure.board.departure_pb2 as departure_pb2
import departure.board.departure_pb2_grpc as departure_pb2_grpc  # for type hinting
import departure.board.protobuf as protobuf
from departure.provider.nexus.bus_data_model import BusData

logger = logging.getLogger(__name__)


# pylint: disable=abstract-method
class ViewModelNexusBus(view_model.ViewModel):
    pass


# pylint: disable=abstract-method
class ViewModelNexusBus_192_32(ViewModelNexusBus):
    def __init__(self):
        self.board_text = contents.BoardText(
            font=contents.read_bdf_font("fonts/6x10_proportional.bdf"),
            colour_map={
                "orange": (255, 204, 0),
                "red": (255, 0, 0),
                "green": (0, 255, 0),
                "white": (255, 255, 255),
            },
            tabs=[[0, "l"], [38, "r"], [43, "l"], [191, "r"]],
        )

    def pixels_single_line(self, bus:BusData, pos: str):
        return self.board_text.colour_text_tabbed_row_pixels(
            [
                [pos, "orange"],
                [bus.number, "white"],
                [bus.destination, "orange", 95],
                [bus.timeLiteral, "green"],
            ]
        )

    def next_content(self, next_busses):
        # empty board if called with None
        if next_busses is None:
            return [], (0, 0), [], (0, 0), [], (0, 0)

        # sort trains by time to station
        # next_trains = sorted(next_trains.values(), key=lambda a: a["time_to_station"])

       # next_busses = [] 
       # next_busses.append(BusData(99, "Hermagor", "2 mins", "Postbus"))

        # top section
        if len(next_busses) == 0:  # "No service" if no service
            (
                top_section_content_pixels,
                top_section_content_pixels_size,
            ) = self.board_text.colour_text_pixels([["No service.", "orange"]])
        else:  # otherwise: 1st train
            (
                top_section_content_pixels,
                top_section_content_pixels_size,
            ) = self.pixels_single_line(next_busses[0], "1st")

        # middle section
        if len(next_busses) < 2:  # nothing if fewer than 2 trains
            middle_section_content_pixels = []
            middle_section_content_pixels_size = (0, 0)
        else:  # otherwise: 2nd train
            (
                middle_section_content_pixels,
                middle_section_content_pixels_size,
            ) = self.pixels_single_line(next_busses[1], "2nd")

        # bottom section
        if len(next_busses) < 3:  # nothing if fewer than 3 trains
            bottom_section_content_pixels = []
            bottom_section_content_pixels_size = (0, 0)

        elif len(next_busses) == 3:  # 3rd train (if only 3 trains)
            (
                bottom_section_content_pixels,
                bottom_section_content_pixels_size,
            ) = self.pixels_single_line(next_busses[2], "3rd")

        else:  # 3rd-4th trains (if more than 3 trains)
            (
                bottom_section_content_pixels,
                bottom_section_content_pixels_size,
            ) = self.board_text.colour_text_tabbed_rows_pixels(
                [
                    [
                        ["3rd", "orange"],
                        [next_busses[2].number, "white"],
                        [next_busses[2].destination, "orange", 95],
                        [
                            next_busses[2].timeLiteral,
                            "green",
                        ],
                    ],
                    [
                        ["4th", "orange"],
                        [next_busses[3].number, "white"],
                        [next_busses[3].destination, "orange", 95],
                        [
                            next_busses[3].timeLiteral,
                            "green",
                        ],
                    ],
                ],
                row_height=11,
            )

        return (
            top_section_content_pixels,
            top_section_content_pixels_size,
            middle_section_content_pixels,
            middle_section_content_pixels_size,
            bottom_section_content_pixels,
            bottom_section_content_pixels_size,
        )


class ViewModelNexusBus_192_32_3_Rows_To_ProtocolBuffers(ViewModelNexusBus_192_32):
    def __init__(self, board_manager_stub: departure_pb2_grpc.BoardManagerStub):
        super().__init__()
        self.board_manager_stub = board_manager_stub

        self.next_service_tracker = [
            departure_pb2.Movement(
                static_content=departure_pb2.StaticContent(total_duration=2000)
            ),
            departure_pb2.Movement(
                scrolling_content=departure_pb2.ScrollingContent(
                    step_duration=100,
                    total_steps=11,
                    delta_x_per_step=0,
                    delta_y_per_step=-1,
                )
            ),
        ]

        self.no_movement = [
            departure_pb2.Movement(no_movement=departure_pb2.NoMovement())
        ]

    def update(self, next_trains):  # pylint: disable=arguments-differ
        requests_data = []

        (
            top_section_content_pixels,
            top_section_content_pixels_size,
            middle_section_content_pixels,
            middle_section_content_pixels_size,
            bottom_section_content_pixels,
            bottom_section_content_pixels_size,
        ) = self.next_content(next_trains)

        # top section: 1st train
        requests_data.append(
            departure_pb2.BoardSectionUpdateRequest(
                section_index=0,
                content=departure_pb2.BoardSectionContent(
                    pixels=protobuf.serialise_pixels(top_section_content_pixels),
                    content_w=top_section_content_pixels_size[0],
                    content_h=top_section_content_pixels_size[1],
                    repeat_x=False,
                    repeat_y=False,
                ),
                movement=self.no_movement,
                continue_movement=False,  # force reset
            )
        )

        # middle section: 2nd train
        requests_data.append(
            departure_pb2.BoardSectionUpdateRequest(
                section_index=1,
                content=departure_pb2.BoardSectionContent(
                    pixels=protobuf.serialise_pixels(middle_section_content_pixels),
                    content_w=middle_section_content_pixels_size[0],
                    content_h=middle_section_content_pixels_size[1],
                    repeat_x=False,
                    repeat_y=False,
                ),
                movement=self.no_movement,
                continue_movement=False,  # force reset
            )
        )

        # bottom section: 3rd train onwards
        if next_trains is None or len(next_trains) <= 3:
            next_movement = self.no_movement
        else:
            next_movement = self.next_service_tracker

        requests_data.append(
            departure_pb2.BoardSectionUpdateRequest(
                section_index=2,
                content=departure_pb2.BoardSectionContent(
                    pixels=protobuf.serialise_pixels(bottom_section_content_pixels),
                    content_w=bottom_section_content_pixels_size[0],
                    content_h=bottom_section_content_pixels_size[1],
                    repeat_x=False,
                    repeat_y=True,
                ),
                movement=next_movement,
                continue_movement=True,
            )
        )

        # send gRPC message
        try:
            self.board_manager_stub.BoardSectionsUpdate(
                departure_pb2.BoardSectionsUpdateRequest(requests=requests_data)
            )
        # pylint: disable=protected-access
        except (grpc._channel._Rendezvous, grpc._channel._InactiveRpcError):
            logger.warning("connection to board failed")
