from fastapi.testclient import TestClient

from departure.web import admin, api_server


def test_shutdown_web_server_route_needs_no_token(monkeypatch):
    # the web UI's shutdown button posts with no body (home network use)
    system_calls = []
    monkeypatch.setattr(admin.os, "system", system_calls.append)

    response = TestClient(api_server.app).post("/shutdown-web-server")

    assert response.json() == {"status": "OK"}
    assert system_calls == ["sudo shutdown -h now"]
