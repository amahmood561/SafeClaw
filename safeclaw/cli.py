import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from .agent import run_task
from .database import describe_database, describe_table, list_databases, run_readonly_query, test_database
from .doctor import doctor_summary, run_doctor
from .sessions import (
    compact_session,
    edit_memory,
    export_session,
    forget_memory,
    import_session,
    list_sessions,
    recall,
    reset_session,
    search_memory,
    session_status,
    update_session_settings,
)
from .service import (
    install_macos_whatsapp_service,
    macos_whatsapp_service_status,
    start_macos_whatsapp_service,
    stop_macos_whatsapp_service,
    uninstall_macos_whatsapp_service,
)
from .tools import available_tools
from .config import WORKSPACE
from .whatsapp import serve_whatsapp, whatsapp_setup_status

app = typer.Typer(help="SafeClaw: a self-hosted agent with explicit permissions")
console = Console()

@app.command()
def run(task: str, session: str = "default", model: str = "", permission_profile: str = ""):
    """Run one task."""
    console.print(Panel.fit("SafeClaw", subtitle=str(WORKSPACE)))
    try:
        result = run_task(
            task,
            session_id=session,
            model=model or None,
            permission_profile=permission_profile or None,
            interactive=True,
        )
        console.print(result)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")

@app.command()
def chat(session: str = "default", model: str = "", permission_profile: str = ""):
    """Interactive task loop."""
    console.print(Panel.fit("SafeClaw Chat", subtitle="type exit/reset/memory to quit/reset/show memory"))
    while True:
        task = console.input("[bold cyan]you>[/bold cyan] ")
        command = task.lower().strip()
        if command in {"exit", "quit"}:
            break
        if command in {"reset", "/reset", "new", "/new"}:
            reset_session(session)
            console.print("[green]Session reset.[/green]")
            continue
        if command in {"memory", "/memory"}:
            console.print(recall(session))
            continue
        console.print(
            run_task(
                task,
                session_id=session,
                model=model or None,
                permission_profile=permission_profile or None,
                interactive=True,
            )
        )

@app.command()
def tools():
    """Show available tools."""
    console.print(available_tools())

@app.command("doctor")
def doctor(port: int = 8080, strict: bool = False):
    """Check local setup, config, WhatsApp, and service readiness."""
    checks = run_doctor(port=port)
    table = Table(title="SafeClaw Doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    table.add_column("Fix")
    colors = {"ok": "green", "warn": "yellow", "fail": "red"}
    labels = {"ok": "OK", "warn": "WARN", "fail": "FAIL"}
    for check in checks:
        table.add_row(
            check.name,
            f"[{colors[check.status]}]{labels[check.status]}[/{colors[check.status]}]",
            check.detail,
            check.fix,
        )
    console.print(table)
    summary = doctor_summary(checks)
    console.print(f"Summary: {summary}")
    if strict and any(check.status == "fail" for check in checks):
        raise typer.Exit(1)

@app.command("sessions")
def show_sessions():
    """List saved sessions."""
    for item in list_sessions():
        console.print(item)

@app.command("status")
def status(session: str = "default"):
    """Show session status."""
    console.print(session_status(session))

@app.command("session-config")
def session_config(session: str = "default", model: str | None = None, permission_profile: str | None = None):
    """Update per-session model or permission profile metadata."""
    console.print(update_session_settings(session, model=model, permission_profile=permission_profile))

@app.command("reset")
def reset(session: str = "default"):
    """Reset a session."""
    reset_session(session)
    console.print(f"Reset session: {session}")

@app.command("compact")
def compact(session: str = "default", keep_last: int = 12):
    """Compact older session history."""
    console.print(compact_session(session, keep_last=keep_last))

@app.command("memory")
def memory(session: str = "default"):
    """Show saved memory for a session."""
    console.print(recall(session))

@app.command("memory-search")
def memory_search(query: str, session: str = "default"):
    """Search saved memory for a session."""
    console.print(search_memory(session, query))

@app.command("memory-forget")
def memory_forget(target: str, session: str = "default"):
    """Forget memory by id or matching text."""
    console.print(forget_memory(session, target))

@app.command("memory-edit")
def memory_edit(memory_id: int, note: str, session: str = "default"):
    """Edit a saved memory note by id."""
    console.print(edit_memory(session, memory_id, note))

@app.command("export")
def export(session: str = "default", output: str = ""):
    """Export a session and its memory."""
    console.print(export_session(session, output or None))

@app.command("import")
def import_(path: str, session: str = ""):
    """Import a session export."""
    console.print(import_session(path, session or None))

@app.command("db-list")
def db_list():
    """List configured read-only databases."""
    console.print(list_databases(), markup=False)

@app.command("db-test")
def db_test(name: str):
    """Test a configured read-only database connection."""
    console.print(test_database(name), markup=False)

@app.command("db-schema")
def db_schema(name: str):
    """Show tables and row counts for a configured database."""
    console.print(describe_database(name), markup=False)

@app.command("db-table")
def db_table(name: str, table: str):
    """Describe a table in a configured database."""
    console.print(describe_table(name, table), markup=False)

@app.command("db-query")
def db_query(name: str, query: str, limit: int = 50):
    """Run one read-only query against a configured database."""
    console.print(run_readonly_query(name, query, limit=limit), markup=False)

@app.command("whatsapp")
def whatsapp(host: str = "0.0.0.0", port: int = 8080):
    """Run a Twilio-compatible WhatsApp webhook."""
    serve_whatsapp(host=host, port=port)

@app.command("whatsapp-setup")
def whatsapp_setup(public_url: str = "https://your-public-url"):
    """Show easy WhatsApp setup instructions and config status."""
    console.print(whatsapp_setup_status(public_url))

@app.command("service-install")
def service_install(host: str = "0.0.0.0", port: int = 8080, start: bool = True):
    """Install the macOS LaunchAgent for persistent WhatsApp mode."""
    console.print(install_macos_whatsapp_service(host=host, port=port, start=start))

@app.command("service-start")
def service_start():
    """Start the persistent WhatsApp service."""
    console.print(start_macos_whatsapp_service())

@app.command("service-stop")
def service_stop():
    """Stop the persistent WhatsApp service."""
    console.print(stop_macos_whatsapp_service())

@app.command("service-status")
def service_status():
    """Show persistent WhatsApp service status."""
    console.print(macos_whatsapp_service_status())

@app.command("service-uninstall")
def service_uninstall():
    """Uninstall the persistent WhatsApp service."""
    console.print(uninstall_macos_whatsapp_service())

if __name__ == "__main__":
    app()
