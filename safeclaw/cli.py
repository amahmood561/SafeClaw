import typer
from rich.console import Console
from rich.panel import Panel
from .agent import run_task
from .sessions import compact_session, list_sessions, recall, reset_session
from .tools import available_tools
from .config import WORKSPACE
from .whatsapp import serve_whatsapp

app = typer.Typer(help="SafeClaw: a self-hosted agent with explicit permissions")
console = Console()

@app.command()
def run(task: str, session: str = "default", model: str = ""):
    """Run one task."""
    console.print(Panel.fit("SafeClaw", subtitle=str(WORKSPACE)))
    try:
        result = run_task(task, session_id=session, model=model or None)
        console.print(result)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")

@app.command()
def chat(session: str = "default", model: str = ""):
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
        console.print(run_task(task, session_id=session, model=model or None))

@app.command()
def tools():
    """Show available tools."""
    console.print(available_tools())

@app.command("sessions")
def show_sessions():
    """List saved sessions."""
    for item in list_sessions():
        console.print(item)

@app.command("reset")
def reset(session: str = "default"):
    """Reset a session."""
    reset_session(session)
    console.print(f"Reset session: {session}")

@app.command("compact")
def compact(session: str = "default", keep_last: int = 12):
    """Compact older session history."""
    console.print(compact_session(session, keep_last=keep_last))

@app.command("whatsapp")
def whatsapp(host: str = "0.0.0.0", port: int = 8080):
    """Run a Twilio-compatible WhatsApp webhook."""
    serve_whatsapp(host=host, port=port)

if __name__ == "__main__":
    app()
