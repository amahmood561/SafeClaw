import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from .agent import emit_event, run_task
from .database import describe_database, describe_table, list_databases, run_readonly_query, test_database
from .doctor import REPO_ROOT, doctor_summary, group_checks, run_doctor
from .providers import PROVIDER_PRESETS
from .setup_wizard import apply_to_env, detect_ollama, hosted_choice, local_choice, suggest_local_model
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
from .llm import LLMError, provider_test as run_provider_test
from .providers import provider_presets_text
from .telegram import serve_telegram, telegram_setup_status
from .whatsapp import serve_whatsapp, whatsapp_setup_status

app = typer.Typer(help="SafeClaw: a self-hosted agent with explicit permissions")
console = Console()


def _provider_error_payload(exc: LLMError) -> dict[str, str | int | None]:
    return {
        "type": "provider_error",
        "message": str(exc),
        "error_type": exc.error_type,
        "code": exc.code,
        "status_code": exc.status_code,
    }


def _print_provider_error(exc: LLMError, events: bool = False) -> None:
    payload = _provider_error_payload(exc)
    if events:
        emit_event(payload)
        return
    console.print("[red]Provider error[/red]")
    console.print(str(exc))
    if exc.code == "insufficient_quota" or exc.error_type == "insufficient_quota":
        console.print("Fix: check OpenAI API billing and quota at https://platform.openai.com/settings/organization/billing/overview")

@app.command()
def init(force: bool = False):
    """Set up SafeClaw. Local by default, no API key required."""
    env_path = REPO_ROOT / ".env"
    if env_path.exists() and not force:
        console.print(f"[yellow]{env_path} already exists.[/yellow] Re-run with --force to reconfigure.")
        raise typer.Exit(0)
    if not env_path.exists():
        example = REPO_ROOT / ".env.example"
        if example.exists():
            env_path.write_text(example.read_text())

    detected = detect_ollama()
    suggested = suggest_local_model(detected["models"])

    console.print(Panel.fit("SafeClaw setup", subtitle="how should SafeClaw think?"))
    if detected["running"] and suggested:
        console.print(f"  [green]1[/green]  Local model ([bold]{suggested}[/bold]) — nothing leaves this machine  [dim]recommended[/dim]")
    elif detected["running"]:
        console.print("  [yellow]1[/yellow]  Local model — Ollama is running but has no models. Run: ollama pull qwen2.5")
    else:
        console.print("  [dim]1  Local model — Ollama not detected. Install from https://ollama.com[/dim]")
    console.print("  [cyan]2[/cyan]  Hosted API (OpenAI, Groq, OpenRouter) — faster, needs a key")

    default = "1" if (detected["running"] and suggested) else "2"
    choice = console.input(f"[bold cyan]choice [{default}]>[/bold cyan] ").strip() or default

    if choice == "1":
        values = local_choice(detected["models"])
        if not values:
            console.print("[red]No local model available.[/red] Run: ollama pull qwen2.5, then safeclaw init --force")
            raise typer.Exit(1)
        console.print(f"[green]Local mode.[/green] Model {values['OPENAI_MODEL']}. Nothing leaves this machine.")
    else:
        console.print("Providers: " + ", ".join(p for p in PROVIDER_PRESETS if p != "custom"))
        provider = console.input("[bold cyan]provider [openai]>[/bold cyan] ").strip() or "openai"
        api_key = console.input("[bold cyan]api key>[/bold cyan] ").strip()
        if not api_key:
            console.print("[red]A hosted provider needs a key.[/red]")
            raise typer.Exit(1)
        values = hosted_choice(provider, api_key)
        console.print(f"[green]Hosted mode.[/green] {values['OPENAI_MODEL']} via {values['OPENAI_BASE_URL']}")

    apply_to_env(env_path, values)
    console.print(f"Wrote {env_path}")
    console.print("\nNext:  [bold]safeclaw doctor[/bold]   then   [bold]safeclaw chat[/bold]")

@app.command()
def run(task: str, session: str = "default", model: str = "", permission_profile: str = "", events: bool = False):
    """Run one task."""
    if not events:
        console.print(Panel.fit("SafeClaw", subtitle=str(WORKSPACE)))
    try:
        kwargs = {}
        if events:
            kwargs["event_callback"] = emit_event
        result = run_task(
            task,
            session_id=session,
            model=model or None,
            permission_profile=permission_profile or None,
            interactive=True,
            **kwargs,
        )
        if not events:
            console.print(result)
    except LLMError as exc:
        _print_provider_error(exc, events=events)
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

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

@app.command("provider-presets")
def provider_presets():
    """Show supported OpenAI-compatible provider presets."""
    console.print(provider_presets_text(), markup=False)

@app.command("provider-test")
def provider_test(base_url: str = "", model: str = ""):
    """Test the configured OpenAI-compatible model provider."""
    try:
        result = run_provider_test(base_url=base_url or None, model=model or None)
    except LLMError as exc:
        _print_provider_error(exc)
        raise typer.Exit(1)
    console.print("Provider test passed")
    console.print(f"Base URL: {result['base_url']}")
    console.print(f"Model: {result['model']}")
    console.print(f"Response: {result['content']}")

@app.command("doctor")
def doctor(port: int = 8080, strict: bool = False, verbose: bool = False):
    """Check local setup, config, WhatsApp, and service readiness."""
    checks = run_doctor(port=port)
    grouped = group_checks(checks)
    colors = {"ok": "green", "warn": "yellow", "fail": "red"}
    labels = {"ok": "OK", "warn": "WARN", "fail": "FAIL"}

    # Grouped, not one flat list. A missing model and a missing Twilio token are
    # not the same kind of problem, and a fifteen-row table says they are.
    sections = [
        ("blocking", "Blocking", "red", "These stop SafeClaw working. Fix these first."),
        ("optional", "Optional", "yellow", "Integrations you can set up later, or never."),
        ("healthy", "Healthy", "green", ""),
    ]
    for key, title, colour, blurb in sections:
        items = grouped[key]
        if not items:
            continue
        if key == "healthy" and not verbose:
            console.print(f"[green]Healthy[/green]  {len(items)} check(s) passing. Use --verbose to list them.")
            continue
        table = Table(title=f"[{colour}]{title}[/{colour}] ({len(items)})", title_justify="left")
        table.add_column("Check")
        table.add_column("Status")
        table.add_column("Detail")
        table.add_column("Fix")
        for check in items:
            table.add_row(
                check.name,
                f"[{colors[check.status]}]{labels[check.status]}[/{colors[check.status]}]",
                check.detail,
                check.fix,
            )
        if blurb:
            console.print(f"[dim]{blurb}[/dim]")
        console.print(table)

    console.print(f"Summary: {doctor_summary(checks)}")
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

@app.command("telegram")
def telegram(once: bool = False):
    """Run Telegram bot polling for phone access without a webhook."""
    serve_telegram(once=once)

@app.command("telegram-setup")
def telegram_setup():
    """Show easy Telegram setup instructions and config status."""
    console.print(telegram_setup_status())

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
