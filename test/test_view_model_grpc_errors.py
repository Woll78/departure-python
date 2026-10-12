import glob
import pathlib
from unittest import mock

import grpc
import pytest

PROVIDER_DIR = pathlib.Path(__file__).parent.parent / "departure" / "provider"
VIEW_MODEL_FILES = sorted(glob.glob(str(PROVIDER_DIR / "*" / "view_model.py")))


class FakeRpcError(grpc.RpcError):
    pass


def test_national_rail_update_survives_board_connection_failure():
    try:
        from departure.provider.national_rail import (  # pylint: disable=import-outside-toplevel
            view_model as national_rail_view_model,
        )
    except TypeError:  # stale generated departure_pb2 vs. new protobuf
        pytest.skip("departure_pb2 incompatible with installed protobuf")

    stub = mock.Mock()
    stub.BoardSectionsUpdate.side_effect = FakeRpcError()
    model = national_rail_view_model.ViewModelNationalRail_192_32_3_Rows_To_ProtocolBuffers(
        stub
    )

    model.update([])  # must log a warning, not raise

    stub.BoardSectionsUpdate.assert_called_once()


@pytest.mark.parametrize("path", VIEW_MODEL_FILES)
def test_view_models_catch_public_rpc_error_only(path):
    source = pathlib.Path(path).read_text()
    assert "grpc._channel" not in source
    assert "except grpc.RpcError" in source
