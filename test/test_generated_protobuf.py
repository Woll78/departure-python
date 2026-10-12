import departure.board.departure_pb2 as departure_pb2
import departure.board.departure_pb2_grpc as departure_pb2_grpc
from departure.board import protobuf


def test_generated_code_loads_and_roundtrips():
    request = departure_pb2.BoardSectionsUpdateRequest(
        requests=[
            departure_pb2.BoardSectionUpdateRequest(
                section_index=1,
                content=departure_pb2.BoardSectionContent(
                    pixels=protobuf.serialise_pixels([(1, 2, (3, 4, 5))]),
                    content_w=1,
                    content_h=1,
                ),
                continue_movement=True,
            )
        ]
    )

    decoded = departure_pb2.BoardSectionsUpdateRequest.FromString(
        request.SerializeToString()
    )

    assert decoded == request
    assert decoded.requests[0].content.pixels[0].b == 5


def test_grpc_stub_exposes_board_sections_update():
    assert hasattr(departure_pb2_grpc.BoardManagerStub, "__init__")
    assert "BoardSectionsUpdate" in departure_pb2.DESCRIPTOR.services_by_name[
        "BoardManager"
    ].methods_by_name
