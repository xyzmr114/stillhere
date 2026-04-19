"""stillhere doctor — Diagnose configuration and connectivity issues."""
import os
import re
import shutil
import subprocess
import socket

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from commands.shared import (
    PROJECT_ROOT, ENV_PATH, DOCKER_COMPOSE, MIGRATIONS_DIR,
    console, check_mark, load_env, run_cmd, docker_compose_cmd,
)

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "JWT_SECRET",
    "REDIS_URL",
    "BASE_URL",
]

RECOMMENDED_ENV_VARS = [
    "EMAIL_PROVIDER",
    "EMAIL_FROM",
    "PUSH_PROVIDER",
    "CORS_ORIGINS",
]

CONTAINERS = ["stillhere-api", "stillhere-worker", "stillhere-beat", "stillhere-redis"]


def _check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def _test_db(url: str) -> tuple[bool, str]:
    try:
        import psycopg2
        conn = psycopg2.connect(url, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        return True, version.split(",")[0]
    except Exception as e:
        return False, str(e)[:80]


def _test_redis(url: str) -> tuple[bool, str]:
    try:
        host_part = url.split("://")[1].split("/")[0]
        h, _, p = host_part.partition(":")
        s = socket.create_connection((h, int(p or 6379)), timeout=3)
        s.send(b"PING\r\n")
        resp = s.recv(64).decode().strip()
        s.close()
        return "+PONG" in resp, resp
    except Exception as e:
        return False, str(e)[:80]


def _check_migrations(db_url: str) -> tuple[int, int, list[str]]:
    """Check which migrations have been applied. Returns (total, pending, pending_names)."""
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    total = len(sql_files)
    pending = []
    try:
        import psycopg2
        conn = psycopg2.connect(db_url, connect_timeout=5)
        cur = conn.cursor()
        for f in sql_files:
            name = f.stem
            if name.startswith("005_seed"):
                cur.execute("SELECT COUNT(*) FROM non_emergency_numbers")
                count = cur.fetchone()[0]
                if count == 0:
                    pending.append(f.name)
            elif "timezone" in name:
                try:
                    cur.execute("SELECT timezone FROM users LIMIT 1")
                except Exception:
                    conn.rollback()
                    pending.append(f.name)
            elif "non_emergency" in name:
                try:
                    cur.execute("SELECT non_emergency_number FROM users LIMIT 1")
                except Exception:
                    conn.rollback()
                    pending.append(f.name)
            elif "email_verified" in name:
                try:
                    cur.execute("SELECT email_verified FROM users LIMIT 1")
                except Exception:
                    conn.rollback()
                    pending.append(f.name)
            elif "accepted_tos" in name:
                try:
                    cur.execute("SELECT accepted_tos FROM users LIMIT 1")
                except Exception:
                    conn.rollback()
                    pending.append(f.name)
            elif "waitlist" in name:
                try:
                    cur.execute("SELECT 1 FROM waitlist LIMIT 1")
                except Exception:
                    conn.rollback()
                    pending.append(f.name)
        cur.close()
        conn.close()
    except Exception:
        pending = [f.name for f in sql_files]
    return total, len(pending), pending


def _check_containers() -> dict[str, dict]:
    """Check Docker container status."""
    results = {}
    for name in CONTAINERS:
        r = run_cmd(["docker", "inspect", "--format",
                      "{{.State.Status}} {{.State.Health.Status}}", name])
        if r.returncode != 0:
            results[name] = {"running": False, "healthy": False, "status": "not found"}
        else:
            parts = r.stdout.strip().split()
            running = parts[0] == "running" if parts else False
            healthy = parts[1] == "healthy" if len(parts) > 1 else False
            results[name] = {"running": running, "healthy": healthy, "status": " ".join(parts)}
    return results


def _check_env_syntax(env_text: str) -> list[str]:
    """Check .env for common syntax errors."""
    issues = []
    for i, line in enumerate(env_text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            issues.append(f"Line {i}: missing '=' — not a valid env entry")
        else:
            key, _, val = stripped.partition("=")
            if " " in key.strip():
                issues.append(f"Line {i}: key '{key.strip()}' contains spaces")
            if val.startswith('"') and not val.endswith('"'):
                issues.append(f"Line {i}: unclosed double quote")
            if val.startswith("'") and not val.endswith("'"):
                issues.append(f"Line {i}: unclosed single quote")
    return issues


def _check_disk() -> tuple[str, str, bool]:
    """Check disk space. Returns (total, avail, ok)."""
    try:
        st = os.statvfs(str(PROJECT_ROOT))
        total_gb = (st.f_blocks * st.f_frsize) / (1024**3)
        avail_gb = (st.f_bavail * st.f_frsize) / (1024**3)
        return f"{total_gb:.1f}GB", f"{avail_gb:.1f}GB", avail_gb > 1.0
    except Exception:
        return "?", "?", True


@click.command()
def doctor():
    """Diagnose configuration and connectivity issues."""
    console.print()
    console.print(Panel.fit(
        "[bold green]Still Here[/bold green] \u2014 Doctor\n"
        "[dim]Checking your setup...[/dim]",
        border_style="green",
    ))

    issues = []
    warnings = []

    # ── Section 1: Prerequisites ──
    console.print("\n[bold]1. Prerequisites[/bold]")

    docker_ok = _check_tool("docker")
    console.print(f"  {check_mark(docker_ok)} Docker installed")
    if not docker_ok:
        issues.append("Docker is not installed. Install from https://docs.docker.com/get-docker/")

    dc_ok = run_cmd(["docker", "compose", "version"]).returncode == 0 if docker_ok else False
    console.print(f"  {check_mark(dc_ok)} Docker Compose v2")
    if not dc_ok:
        issues.append("Docker Compose v2 not found. Update Docker or install docker-compose-plugin.")

    compose_exists = DOCKER_COMPOSE.exists()
    console.print(f"  {check_mark(compose_exists)} docker-compose.yml found")

    total_gb, avail_gb, disk_ok = _check_disk()
    console.print(f"  {check_mark(disk_ok)} Disk space ({avail_gb} free of {total_gb})")
    if not disk_ok:
        warnings.append(f"Low disk space: {avail_gb} free. Consider cleaning up.")

    # ── Section 2: Environment ──
    console.print("\n[bold]2. Environment (.env)[/bold]")

    env_exists = ENV_PATH.exists()
    console.print(f"  {check_mark(env_exists)} .env file exists")
    if not env_exists:
        issues.append(".env file missing. Run [bold]stillhere init[/bold] to create one.")
        console.print(f"\n  [red]Cannot continue without .env. Run 'stillhere init' first.[/red]")
        _print_summary(issues, warnings)
        return

    env_text = ENV_PATH.read_text()
    syntax_issues = _check_env_syntax(env_text)
    console.print(f"  {check_mark(len(syntax_issues) == 0)} .env syntax valid")
    for issue in syntax_issues:
        console.print(f"    [red]\u2022 {issue}[/red]")
        issues.append(f".env syntax: {issue}")

    env = load_env()

    for var in REQUIRED_ENV_VARS:
        present = bool(env.get(var))
        console.print(f"  {check_mark(present)} {var}")
        if not present:
            issues.append(f"Required variable {var} is missing or empty.")

    for var in RECOMMENDED_ENV_VARS:
        present = bool(env.get(var))
        if not present:
            console.print(f"  [yellow]\u26a0[/yellow]  {var} [dim](recommended)[/dim]")
            warnings.append(f"{var} not set — feature may not work.")

    jwt = env.get("JWT_SECRET", "")
    jwt_weak = jwt in ("", "change-me-use-a-long-random-string") or len(jwt) < 32
    console.print(f"  {check_mark(not jwt_weak)} JWT_SECRET is strong")
    if jwt_weak:
        issues.append("JWT_SECRET is weak or default. Generate a new one: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\"")

    cors = env.get("CORS_ORIGINS", "")
    cors_open = cors == "*" or cors == ""
    console.print(f"  {check_mark(not cors_open)} CORS_ORIGINS is restricted")
    if cors_open:
        warnings.append("CORS_ORIGINS is unrestricted ('*'). Set it to your domain.")

    # ── Section 3: Database ──
    console.print("\n[bold]3. Database[/bold]")

    db_url = env.get("DATABASE_URL", "")
    if db_url:
        db_ok, db_info = _test_db(db_url)
        console.print(f"  {check_mark(db_ok)} Connection {'[green]OK[/green]' if db_ok else '[red]FAILED[/red]'}")
        if db_ok:
            console.print(f"    [dim]{db_info}[/dim]")
            total, pending, pending_names = _check_migrations(db_url)
            console.print(f"  {check_mark(pending == 0)} Migrations ({total - pending}/{total} applied)")
            if pending > 0:
                for name in pending_names:
                    console.print(f"    [yellow]\u2022 Pending: {name}[/yellow]")
                warnings.append(f"{pending} pending migrations. Run [bold]stillhere migrate[/bold].")
        else:
            console.print(f"    [red]{db_info}[/red]")
            issues.append(f"Database connection failed: {db_info}")
    else:
        console.print(f"  {check_mark(False)} DATABASE_URL not configured")

    # ── Section 4: Redis ──
    console.print("\n[bold]4. Redis[/bold]")

    redis_url = env.get("REDIS_URL", "")
    if redis_url:
        redis_ok, redis_info = _test_redis(redis_url)
        console.print(f"  {check_mark(redis_ok)} Connection {'[green]OK[/green]' if redis_ok else '[red]FAILED[/red]'}")
        if not redis_ok:
            # Redis might only be accessible from inside Docker
            console.print(f"    [dim]If using bundled Redis, this is OK \u2014 only reachable inside Docker network.[/dim]")
    else:
        console.print(f"  {check_mark(False)} REDIS_URL not configured")

    # ── Section 5: Containers ──
    console.print("\n[bold]5. Containers[/bold]")

    if docker_ok:
        containers = _check_containers()
        for name, info in containers.items():
            if info["running"] and info["healthy"]:
                console.print(f"  {check_mark(True)} {name} [dim]({info['status']})[/dim]")
            elif info["running"]:
                console.print(f"  [yellow]\u26a0[/yellow]  {name} [dim]({info['status']})[/dim]")
                warnings.append(f"{name} is running but not healthy.")
            else:
                console.print(f"  {check_mark(False)} {name} [dim]({info['status']})[/dim]")
                issues.append(f"{name} is not running.")
    else:
        console.print(f"  [dim]Skipped \u2014 Docker not available.[/dim]")

    # ── Section 6: Services ──
    console.print("\n[bold]6. Service Configuration[/bold]")

    email_provider = env.get("EMAIL_PROVIDER", "")
    email_ok = bool(email_provider)
    console.print(f"  {check_mark(email_ok)} Email: {email_provider or 'not configured'}")
    if email_provider == "smtp":
        smtp_preset = env.get("SMTP_PRESET", "")
        smtp_user = env.get("SMTP_USER", "")
        if not smtp_user:
            warnings.append("SMTP_USER not set — emails won't send.")
        if not smtp_preset and not env.get("SMTP_HOST"):
            warnings.append("Neither SMTP_PRESET nor SMTP_HOST set.")

    push_provider = env.get("PUSH_PROVIDER", "")
    push_ok = bool(push_provider)
    console.print(f"  {check_mark(push_ok)} Push: {push_provider or 'not configured'}")

    twilio_ok = bool(env.get("TWILIO_ACCOUNT_SID")) and bool(env.get("TWILIO_AUTH_TOKEN"))
    console.print(f"  {check_mark(twilio_ok)} Twilio: {'configured' if twilio_ok else 'not configured'}")
    if not twilio_ok:
        warnings.append("Twilio not configured. SMS/voice escalation will be logged only.")

    stripe_ok = bool(env.get("STRIPE_SECRET_KEY"))
    console.print(f"  {check_mark(stripe_ok)} Stripe: {'configured' if stripe_ok else 'not configured'}")
    if not stripe_ok:
        warnings.append("Stripe not configured. Payments won't work.")

    _print_summary(issues, warnings)


def _print_summary(issues: list[str], warnings: list[str]):
    console.print()
    if not issues and not warnings:
        console.print(Panel.fit(
            "[bold green]\u2713 All checks passed![/bold green]\n"
            "[dim]Your Still Here instance looks healthy.[/dim]",
            border_style="green",
        ))
    elif not issues:
        console.print(Panel.fit(
            f"[bold yellow]\u26a0 {len(warnings)} warning(s)[/bold yellow]\n" +
            "\n".join(f"  \u2022 {w}" for w in warnings),
            border_style="yellow",
        ))
    else:
        console.print(Panel.fit(
            f"[bold red]\u2717 {len(issues)} issue(s), {len(warnings)} warning(s)[/bold red]\n\n"
            "[bold]Issues (must fix):[/bold]\n" +
            "\n".join(f"  [red]\u2022 {i}[/red]" for i in issues) +
            ("\n\n[bold]Warnings:[/bold]\n" +
             "\n".join(f"  [yellow]\u2022 {w}[/yellow]" for w in warnings) if warnings else ""),
            border_style="red",
        ))
