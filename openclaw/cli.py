import typer
from rich.console import Console
from rich.panel import Panel
from .agent import run_task
from .tools import available_tools
from .config import WORKSPACE

app = typer.Typer(help="OpenSafeClaw Local - self-hosted terminal agent")
console = Console()

@app.command()
def run(task: str):
    """Run one task."""
    console.print(Panel.fit("🦞 OpenSafeClaw Local", subtitle=str(WORKSPACE)))
    try:
        result = run_task(task)
        console.print(result)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")

@app.command()
def chat():
    """Interactive task loop."""
    console.print(Panel.fit("🦞 OpenSafeClaw Local Chat", subtitle="type exit to quit"))
    while True:
        task = console.input("[bold cyan]you>[/bold cyan] ")
        if task.lower().strip() in {"exit", "quit"}:
            break
        console.print(run_task(task))

@app.command()
def tools():
    """Show available tools."""
    console.print(available_tools())

if __name__ == "__main__":
    app()
