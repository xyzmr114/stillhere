"""stillhere logs — Tail container logs."""
import subprocess

import click
from rich.console import Console

from commands.shared import PROJECT_ROOT, docker_compose_cmd

console = Console()

SERVICES = ["api", "worker", "beat", "redis"]


@click.command()
@click.argument("service", required=False, default=None)
@click.option("-n", "--lines", default=100, help="Number of lines to show")
@click.option("-f", "--follow", is_flag=True, default=True, help="Follow log output")
def logs(service: str, lines: int, follow: bool):
    """Tail container logs. Optionally specify a service (api, worker, beat, redis)."""
    dc = docker_compose_cmd()

    if service and service not in SERVICES:
        console.print(f"[red]Unknown service '{service}'. Choose from: {', '.join(SERVICES)}[/red]")
        return

    cmd = dc + ["logs", f"--tail={lines}"]
    if follow:
        cmd.append("-f")
    if service:
        cmd.append(service)

    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")
    subprocess.run(cmd, cwd=str(PROJECT_ROOT))
