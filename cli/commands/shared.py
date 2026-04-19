"""Shared utilities for CLI commands."""
import os
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"
DOCKER_COMPOSE = PROJECT_ROOT / "docker-compose.yml"


def check_mark(ok: bool) -> str:
    return "[green]\u2713[/green]" if ok else "[red]\u2717[/red]"


def run_cmd(cmd: list[str], capture: bool = True, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=capture, text=True, cwd=str(PROJECT_ROOT), **kwargs)


def load_env() -> dict[str, str]:
    """Parse .env file into a dict."""
    env = {}
    if not ENV_PATH.exists():
        return env
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip()
    return env


def write_env(env: dict[str, str]):
    """Write env dict to .env file, preserving comments from .env.example."""
    lines = []
    if ENV_EXAMPLE_PATH.exists():
        for line in ENV_EXAMPLE_PATH.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                lines.append(line)
                continue
            if "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in env:
                    lines.append(f"{key}={env[key]}")
                else:
                    lines.append(f"# {line}")
            else:
                lines.append(line)
    # Add any keys not in .env.example
    existing_keys = {l.split("=", 1)[0].strip() for l in lines if "=" in l and not l.strip().startswith("#")}
    for key, val in env.items():
        if key not in existing_keys:
            lines.append(f"{key}={val}")
    ENV_PATH.write_text("\n".join(lines) + "\n")


def docker_compose_cmd() -> list[str]:
    """Return the docker compose command (v2 preferred)."""
    result = run_cmd(["docker", "compose", "version"])
    if result.returncode == 0:
        return ["docker", "compose"]
    return ["docker-compose"]
