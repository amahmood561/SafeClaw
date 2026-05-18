import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import WORKSPACE, SQLITE_DATABASES

DEFAULT_ROW_LIMIT = 50
MAX_ROW_LIMIT = 500
WRITE_SQL_PATTERN = re.compile(
    r"\b(attach|alter|create|delete|detach|drop|insert|pragma|replace|truncate|update|vacuum)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DatabaseConfig:
    name: str
    type: str
    path: Path


def _parse_sqlite_databases(raw: str | None = None) -> list[DatabaseConfig]:
    raw = SQLITE_DATABASES if raw is None else raw
    databases: list[DatabaseConfig] = []
    for item in raw.split(","):
        if not item.strip():
            continue
        if "=" not in item:
            continue
        name, path = item.split("=", 1)
        name = name.strip()
        path = path.strip()
        if not name or not path:
            continue
        target = _safe_database_path(path)
        databases.append(DatabaseConfig(name=name, type="sqlite", path=target))
    return databases


def _safe_database_path(path: str) -> Path:
    target = (WORKSPACE / path).resolve()
    try:
        target.relative_to(WORKSPACE)
    except ValueError:
        raise ValueError("Database path escapes workspace")
    return target


def list_databases() -> str:
    databases = _parse_sqlite_databases()
    if not databases:
        return "No databases configured. Set SAFECLAW_SQLITE_DATABASES='name=relative/path.db'."
    lines = ["Configured databases:"]
    for database in databases:
        relative = database.path.relative_to(WORKSPACE)
        exists = "exists" if database.path.exists() else "missing"
        lines.append(f"- {database.name} ({database.type}) {relative} [{exists}]")
    return "\n".join(lines)


def _get_database(name: str) -> DatabaseConfig:
    for database in _parse_sqlite_databases():
        if database.name == name:
            return database
    raise ValueError(f"Unknown database: {name}")


def _connect_readonly(database: DatabaseConfig) -> sqlite3.Connection:
    if database.type != "sqlite":
        raise ValueError(f"Unsupported database type: {database.type}")
    if not database.path.exists():
        raise FileNotFoundError(f"Database not found: {database.path.relative_to(WORKSPACE)}")
    uri = f"file:{database.path.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def test_database(name: str) -> str:
    database = _get_database(name)
    with _connect_readonly(database) as connection:
        connection.execute("select 1").fetchone()
    return f"Database ok: {name}"


def _list_table_names(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "select name from sqlite_master where type = 'table' and name not like 'sqlite_%' order by name"
    ).fetchall()
    return [str(row["name"]) for row in rows]


def describe_database(name: str) -> str:
    database = _get_database(name)
    with _connect_readonly(database) as connection:
        tables = _list_table_names(connection)
        if not tables:
            return f"Database {name} has no tables."
        lines = [f"Database: {name}", "Tables:"]
        for table in tables:
            count = connection.execute(f"select count(*) as count from {_quote_identifier(table)}").fetchone()["count"]
            lines.append(f"- {table} ({count} rows)")
    return "\n".join(lines)


def describe_table(name: str, table: str) -> str:
    database = _get_database(name)
    with _connect_readonly(database) as connection:
        tables = set(_list_table_names(connection))
        if table not in tables:
            return f"Table not found: {table}"
        columns = connection.execute(f"pragma table_info({_quote_identifier(table)})").fetchall()
        if not columns:
            return f"Table {table} has no columns."
        lines = [f"Table: {table}", "Columns:"]
        for column in columns:
            nullable = "not null" if column["notnull"] else "nullable"
            pk = " primary key" if column["pk"] else ""
            lines.append(f"- {column['name']} {column['type'] or 'unknown'} {nullable}{pk}")
    return "\n".join(lines)


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _is_readonly_query(query: str) -> bool:
    stripped = query.strip().rstrip(";").strip()
    if not stripped:
        return False
    if ";" in stripped:
        return False
    if not re.match(r"^(select|with|explain)\b", stripped, flags=re.IGNORECASE):
        return False
    return WRITE_SQL_PATTERN.search(stripped) is None


def run_readonly_query(name: str, query: str, limit: int = DEFAULT_ROW_LIMIT) -> str:
    if not _is_readonly_query(query):
        return "Blocked: only one read-only SELECT/WITH/EXPLAIN query is allowed."
    bounded_limit = max(1, min(int(limit), MAX_ROW_LIMIT))
    database = _get_database(name)
    with _connect_readonly(database) as connection:
        cursor = connection.execute(query)
        rows = cursor.fetchmany(bounded_limit + 1)
    trimmed = len(rows) > bounded_limit
    rows = rows[:bounded_limit]
    payload: dict[str, Any] = {
        "database": name,
        "rows_returned": len(rows),
        "limit": bounded_limit,
        "trimmed": trimmed,
        "rows": [dict(row) for row in rows],
    }
    return json.dumps(payload, indent=2, default=str)
