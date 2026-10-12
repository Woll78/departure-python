import pytest
from fastapi.testclient import TestClient

from departure.web import admin, api_server

TOKEN_ENV_VAR = "DEPARTURE_BOARD_RSHUTDOWN_TOKEN"


@pytest.fixture
def system_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(admin.os, "system", calls.append)
    return calls


def test_shutdown_web_server_with_valid_token(monkeypatch, system_calls):
    monkeypatch.setenv(TOKEN_ENV_VAR, "s3cret")
    assert admin.shutdown_web_server("s3cret") == {"status": "OK"}
    assert system_calls == ["sudo shutdown -h now"]


def test_shutdown_web_server_with_invalid_token(monkeypatch, system_calls):
    monkeypatch.setenv(TOKEN_ENV_VAR, "s3cret")
    assert admin.shutdown_web_server("wrong") == {
        "status": "error",
        "message": "invalid token",
    }
    assert system_calls == []


def test_shutdown_web_server_with_non_ascii_token(monkeypatch, system_calls):
    monkeypatch.setenv(TOKEN_ENV_VAR, "s3cret")
    assert admin.shutdown_web_server("sécret")["status"] == "error"
    assert system_calls == []


@pytest.mark.parametrize("env_value", [None, ""])
def test_shutdown_web_server_refuses_without_configured_token(
    monkeypatch, system_calls, env_value
):
    # fail closed: no token configured must never mean "no token required"
    if env_value is None:
        monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(TOKEN_ENV_VAR, env_value)

    response = admin.shutdown_web_server("")

    assert response["status"] == "error"
    assert TOKEN_ENV_VAR in response["message"]
    assert system_calls == []


def test_shutdown_route_requires_token_in_body(monkeypatch, system_calls):
    monkeypatch.setenv(TOKEN_ENV_VAR, "s3cret")
    client = TestClient(api_server.app)

    assert client.post("/shutdown-web-server").status_code == 422
    assert client.post("/shutdown-web-server", json={"token": "wrong"}).json() == {
        "status": "error",
        "message": "invalid token",
    }
    assert system_calls == []

    assert client.post("/shutdown-web-server", json={"token": "s3cret"}).json() == {
        "status": "OK"
    }
    assert system_calls == ["sudo shutdown -h now"]
