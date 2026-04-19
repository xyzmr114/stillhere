#!/usr/bin/env python3
"""
stillhere — CLI tool for Still Here self-hosted deployments.

Commands:
    init            Interactive setup wizard (generates .env, runs migrations, creates admin)
    doctor          Diagnose configuration and connectivity issues
    migrate         Apply pending SQL migrations
    sync-numbers    Pull latest non-emergency numbers from db.stillherehq.com
    logs            Tail container logs
"""
import click

from commands.init_cmd import init
from commands.doctor_cmd import doctor
from commands.migrate_cmd import migrate
from commands.sync_cmd import sync_numbers
from commands.logs_cmd import logs


@click.group()
@click.version_option(version="1.0.0", prog_name="stillhere")
def cli():
    """Still Here — self-hosted safety check-in platform CLI."""
    pass


cli.add_command(init)
cli.add_command(doctor)
cli.add_command(migrate)
cli.add_command(sync_numbers)
cli.add_command(logs)

if __name__ == "__main__":
    cli()
