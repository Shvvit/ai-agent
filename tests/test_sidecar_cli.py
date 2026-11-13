from __future__ import annotations

import json

from apps.sidecar_cli import (
    SIDECAR_VERSION,
    main,
    registration_path,
    remove_owned_registration,
    write_registration,
)


def test_registration_path_matches_opencode_fallback(tmp_path):
    assert registration_path({}, tmp_path) == tmp_path / ".local" / "state" / "opencode" / "service.json"
    assert registration_path({"XDG_STATE_HOME": str(tmp_path / "state")}, tmp_path) == (
        tmp_path / "state" / "opencode" / "service.json"
    )


def test_registration_is_atomic_contract_and_only_owner_removes_it(tmp_path):
    path = tmp_path / "opencode" / "service.json"
    write_registration(path, pid=42, url="http://127.0.0.1:1234")
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": SIDECAR_VERSION,
        "url": "http://127.0.0.1:1234",
        "pid": 42,
    }
    remove_owned_registration(path, pid=41, url="http://127.0.0.1:1234")
    assert path.exists()
    remove_owned_registration(path, pid=42, url="http://127.0.0.1:1234")
    assert not path.exists()


def test_cli_reports_pinned_version_and_rejects_open_code_engine(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"opencode v{SIDECAR_VERSION}"
    assert main(["run"]) == 2

