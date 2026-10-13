from unittest import mock

import pytest

from departure.provider.national_rail import api


@pytest.fixture(autouse=True)
def ldb_token(monkeypatch):
    monkeypatch.setenv("LDB_TOKEN", "test-token")


def test_wsdl_url_is_https():
    # plain http to lite.realtime.nationalrail.co.uk times out, so the board
    # stays blank
    assert api.WSDL.startswith("https://")


def test_soap_client_fetches_wsdl_over_https():
    with mock.patch.object(api, "Client") as client:
        api.soap_client()

    assert client.call_args.kwargs["wsdl"].startswith("https://")
