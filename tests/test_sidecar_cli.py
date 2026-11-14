from __future__ import annotations

import json
import base64

from apps.sidecar_cli import (
    SIDECAR_VERSION,
    main,
    registration_path,
    remove_owned_registration,
    write_registration,
)
from api.auth import SidecarBasicAuthMiddleware
from api.app import create_app
from fastapi.testclient import TestClient


def test_registration_path_matches_opencode_fallback(tmp_path):
    assert registration_path({}, tmp_path) == tmp_path / ".local" / "state" / "opencode" / "service.json"
    assert registration_path({"XDG_STATE_HOME": str(tmp_path / "state")}, tmp_path) == (
        tmp_path / "state" / "opencode" / "service.json"
    )


def test_registration_is_atomic_contract_and_only_owner_removes_it(tmp_path):
    path = tmp_path / "opencode" / "service.json"
    write_registration(path, pid=42, url="http://127.0.0.1:1234", password="generated-secret", service_id="svc-42")
    registration = json.loads(path.read_text(encoding="utf-8"))
    assert registration == {
        "id": "svc-42",
        "version": SIDECAR_VERSION,
        "url": "http://127.0.0.1:1234",
        "pid": 42,
        "password": "generated-secret",
    }
    remove_owned_registration(path, pid=41, url="http://127.0.0.1:1234")
    assert path.exists()
    remove_owned_registration(path, pid=42, url="http://127.0.0.1:1234")
    assert not path.exists()


def test_sidecar_api_uses_the_password_registered_with_opencode(tmp_path):
    app = create_app(tmp_path)
    app.add_middleware(SidecarBasicAuthMiddleware, password="generated-secret")
    authorization = "Basic " + base64.b64encode(b"opencode:generated-secret").decode("ascii")

    with TestClient(app) as client:
        assert client.get("/api/info").status_code == 401
        response = client.get("/api/info", headers={"Authorization": authorization})

    assert response.status_code == 200
    assert response.json()["version"] == "0.1.0"


def test_cli_reports_pinned_version_and_rejects_open_code_engine(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"opencode v{SIDECAR_VERSION}"
    assert main(["run"]) == 2

