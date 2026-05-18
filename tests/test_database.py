import json
import sqlite3

from safeclaw import database
from safeclaw import cli
from safeclaw.tools import run_tool
from typer.testing import CliRunner


runner = CliRunner()


def invoke(*args):
    return runner.invoke(cli.app, list(args))


def make_database(path):
    connection = sqlite3.connect(path)
    connection.execute("create table users (id integer primary key, name text not null)")
    connection.execute("insert into users (name) values ('Ada'), ('Grace'), ('Linus')")
    connection.commit()
    connection.close()


def configure_database(monkeypatch, workspace, name="app", filename="app.db"):
    db_path = workspace / filename
    make_database(db_path)
    monkeypatch.setattr(database, "SQLITE_DATABASES", f"{name}={filename}")
    return db_path


def test_list_and_test_database(monkeypatch, workspace):
    configure_database(monkeypatch, workspace)

    assert "app (sqlite) app.db [exists]" in database.list_databases()
    assert database.test_database("app") == "Database ok: app"


def test_describe_database_and_table(monkeypatch, workspace):
    configure_database(monkeypatch, workspace)

    schema = database.describe_database("app")
    assert "Database: app" in schema
    assert "- users (3 rows)" in schema

    table = database.describe_table("app", "users")
    assert "Table: users" in table
    assert "- id INTEGER nullable primary key" in table
    assert "- name TEXT not null" in table


def test_readonly_query_returns_json_with_limit(monkeypatch, workspace):
    configure_database(monkeypatch, workspace)

    payload = json.loads(database.run_readonly_query("app", "select id, name from users order by id", limit=2))

    assert payload["database"] == "app"
    assert payload["rows_returned"] == 2
    assert payload["trimmed"] is True
    assert payload["rows"] == [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Grace"}]


def test_readonly_query_blocks_writes_and_multiple_statements(monkeypatch, workspace):
    configure_database(monkeypatch, workspace)

    assert "Blocked" in database.run_readonly_query("app", "delete from users")
    assert "Blocked" in database.run_readonly_query("app", "select * from users; select * from users")
    assert "Blocked" in database.run_readonly_query("app", "pragma table_info(users)")


def test_database_path_must_stay_inside_workspace(monkeypatch):
    monkeypatch.setattr(database, "SQLITE_DATABASES", "bad=../outside.db")

    try:
        database.list_databases()
    except ValueError as exc:
        assert "escapes workspace" in str(exc)
    else:
        raise AssertionError("Database path escape should be blocked")


def test_database_tools_require_db_profile(monkeypatch, workspace):
    configure_database(monkeypatch, workspace)

    blocked = run_tool("describe_database", {"name": "app"}, permission_profile="readonly", interactive=False)
    assert "Blocked by permission profile" in blocked

    allowed = run_tool("describe_database", {"name": "app"}, permission_profile="db-readonly", interactive=False)
    assert "- users (3 rows)" in allowed


def test_db_list_command_shows_configured_database(monkeypatch, workspace):
    configure_database(monkeypatch, workspace)

    result = invoke("db-list")

    assert result.exit_code == 0
    assert "Configured databases:" in result.output
    assert "app (sqlite) app.db [exists]" in result.output


def test_db_list_command_shows_empty_config_message(monkeypatch):
    monkeypatch.setattr(database, "SQLITE_DATABASES", "")

    result = invoke("db-list")

    assert result.exit_code == 0
    assert "No databases configured" in result.output
    assert "SAFECLAW_SQLITE_DATABASES" in result.output


def test_db_test_command_validates_connection(monkeypatch, workspace):
    configure_database(monkeypatch, workspace)

    result = invoke("db-test", "app")

    assert result.exit_code == 0
    assert "Database ok: app" in result.output


def test_db_schema_command_outputs_tables(monkeypatch, workspace):
    configure_database(monkeypatch, workspace)

    result = invoke("db-schema", "app")

    assert result.exit_code == 0
    assert "Database: app" in result.output
    assert "- users (3 rows)" in result.output


def test_db_table_command_outputs_columns(monkeypatch, workspace):
    configure_database(monkeypatch, workspace)

    result = invoke("db-table", "app", "users")

    assert result.exit_code == 0
    assert "Table: users" in result.output
    assert "- id INTEGER nullable primary key" in result.output
    assert "- name TEXT not null" in result.output


def test_db_query_command_outputs_limited_json(monkeypatch, workspace):
    configure_database(monkeypatch, workspace)

    result = invoke("db-query", "app", "select id, name from users order by id", "--limit", "2")

    assert result.exit_code == 0
    assert '"database": "app"' in result.output
    assert '"rows_returned": 2' in result.output
    assert '"trimmed": true' in result.output
    assert '"name": "Ada"' in result.output
    assert '"name": "Grace"' in result.output
    assert '"name": "Linus"' not in result.output


def test_db_query_command_blocks_write_sql(monkeypatch, workspace):
    configure_database(monkeypatch, workspace)

    result = invoke("db-query", "app", "delete from users")

    assert result.exit_code == 0
    assert "Blocked: only one read-only" in result.output


def test_db_commands_validate_unknown_database(monkeypatch):
    monkeypatch.setattr(database, "SQLITE_DATABASES", "")

    result = invoke("db-test", "missing")

    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    assert "Unknown database: missing" in str(result.exception)
