# OpenClaw Local

A simple self-hosted OpenClaw-style terminal agent you can run on your own computer.

## What it does

- Runs from your terminal
- Takes a task like: `openclaw run "research RV parks near SF"`
- Uses an LLM provider through an API key
- Can read/write files inside a local workspace
- Has a simple tool system you can extend
- Keeps task logs locally

## Setup

```bash
cd openclaw-local
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add your API key.

## Run

```bash
python -m openclaw.cli run "make me a todo list app plan"
```

Or install as editable:

```bash
pip install -e .
openclaw run "summarize what files are in this folder"
```

## Commands

```bash
openclaw run "your task here"
openclaw chat
openclaw tools
```

## Safety

By default, shell command execution is disabled. To allow it:

```bash
ALLOW_SHELL=true openclaw run "list files"
```

Keep it disabled unless you trust the task.
