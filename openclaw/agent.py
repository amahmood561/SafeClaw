from datetime import datetime
from .llm import complete
from .tools import list_files, available_tools
from .config import WORKSPACE


def run_task(task: str) -> str:
    context = f"""
Workspace: {WORKSPACE}
Current files:
{list_files('.')}

{available_tools()}

User task:
{task}
"""
    messages = [{"role": "user", "content": context}]
    result = complete(messages)

    logs = WORKSPACE / ".openclaw_logs"
    logs.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (logs / f"task-{stamp}.md").write_text(f"# Task\n\n{task}\n\n# Result\n\n{result}\n")
    return result
