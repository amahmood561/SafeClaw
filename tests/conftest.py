import pytest


@pytest.fixture(autouse=True)
def isolated_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    import safeclaw.agent as agent
    import safeclaw.config as config
    import safeclaw.doctor as doctor
    import safeclaw.sessions as sessions
    import safeclaw.tools as tools

    monkeypatch.setattr(config, "WORKSPACE", workspace)
    monkeypatch.setattr(tools, "WORKSPACE", workspace)
    monkeypatch.setattr(agent, "WORKSPACE", workspace)
    monkeypatch.setattr(doctor, "WORKSPACE", workspace)
    monkeypatch.setattr(sessions, "SESSIONS_DIR", workspace / ".safeclaw_sessions")
    monkeypatch.setattr(sessions, "MEMORY_DIR", workspace / ".safeclaw_memory")
    monkeypatch.setattr(sessions, "EXPORTS_DIR", workspace / ".safeclaw_exports")
    yield


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="run live/unmocked tests that may depend on local config or services",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-live"):
        return
    skip_live = pytest.mark.skip(reason="need --run-live to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
