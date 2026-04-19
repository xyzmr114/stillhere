"""stillhere init — Interactive setup wizard."""
import os
import re
import secrets
import subprocess
import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from commands.shared import (
    PROJECT_ROOT, ENV_PATH, console, write_env, docker_compose_cmd,
)

REQUIRED_VARS = {
    "DATABASE_URL": "PostgreSQL connection string",
    "JWT_SECRET": "Secret key for JWT token signing",
    "REDIS_URL": "Redis URL for Celery broker",
    "BASE_URL": "Public URL of your Still Here instance",
}

SMTP_PRESETS = {
    "brevo": ("smtp-relay.brevo.com", 587),
    "gmail": ("smtp.gmail.com", 587),
    "mailgun": ("smtp.mailgun.org", 587),
    "sendgrid": ("smtp.sendgrid.net", 587),
    "zoho": ("smtp.zoho.com", 465),
    "mailjet": ("in-v3.mailjet.com", 587),
}


def _banner():
    console.print()
    console.print(Panel.fit(
        "[bold green]Still Here[/bold green] \u2014 Setup Wizard\n"
        "[dim]This will walk you through configuring your self-hosted instance.[/dim]",
        border_style="green",
    ))
    console.print()


def _step(num: int, total: int, title: str):
    console.print(f"\n[bold cyan]Step {num}/{total}[/bold cyan] \u2014 [bold]{title}[/bold]")
    console.print("[dim]\u2500" * 50 + "[/dim]")


def _prompt(label: str, default: str = None, password: bool = False) -> str:
    return Prompt.ask(f"  {label}", default=default, password=password, console=console)


def _test_db(url: str) -> bool:
    """Test PostgreSQL connection."""
    try:
        import psycopg2
        conn = psycopg2.connect(url, connect_timeout=5)
        conn.close()
        return True
    except Exception:
        return False


def _test_redis(url: str) -> bool:
    """Test Redis connection."""
    try:
        import socket
        # Parse redis://host:port
        host = url.split("://")[1].split("/")[0]
        h, _, p = host.partition(":")
        s = socket.create_connection((h, int(p or 6379)), timeout=3)
        s.close()
        return True
    except Exception:
        return False


@click.command()
def init():
    """Interactive setup wizard \u2014 generates .env, runs migrations, creates admin."""
    _banner()

    if ENV_PATH.exists():
        if not Confirm.ask("  [yellow].env already exists. Overwrite?[/yellow]", default=False, console=console):
            console.print("  [dim]Keeping existing .env. Run [bold]stillhere doctor[/bold] to validate.[/dim]")
            return

    env = {}
    total_steps = 7

    # Step 1: Database
    _step(1, total_steps, "Database")
    console.print("  [dim]Your Supabase or PostgreSQL connection string.[/dim]")
    while True:
        db_url = _prompt("DATABASE_URL", "postgresql://postgres:password@db.supabase.co:5432/postgres")
        with Progress(SpinnerColumn(), TextColumn("[dim]Testing connection...[/dim]"), console=console, transient=True) as p:
            p.add_task("", total=None)
            ok = _test_db(db_url)
        if ok:
            console.print("  [green]\u2713 Connected successfully[/green]")
            break
        else:
            console.print("  [red]\u2717 Could not connect. Check the URL and try again.[/red]")
            if Confirm.ask("  Skip validation and use this URL anyway?", default=False, console=console):
                break
    env["DATABASE_URL"] = db_url

    # Step 2: Redis
    _step(2, total_steps, "Redis")
    console.print("  [dim]Redis is used for the task queue. The default works if using the bundled Redis container.[/dim]")
    redis_url = _prompt("REDIS_URL", "redis://redis:6379")
    env["REDIS_URL"] = redis_url
    env["CELERY_BROKER"] = redis_url + "/0"

    # Step 3: Domain & Security
    _step(3, total_steps, "Domain & Security")
    base_url = _prompt("Base URL (your domain)", "https://stillhere.example.com")
    env["BASE_URL"] = base_url
    env["CORS_ORIGINS"] = base_url
    jwt_secret = secrets.token_urlsafe(48)
    console.print(f"  [dim]Generated JWT secret: {jwt_secret[:12]}...[/dim]")
    env["JWT_SECRET"] = jwt_secret

    # Step 4: Email
    _step(4, total_steps, "Email")
    console.print("  [dim]Choose how to send emails.[/dim]")
    email_provider = Prompt.ask("  Email provider", choices=["smtp", "resend"], default="smtp", console=console)
    env["EMAIL_PROVIDER"] = email_provider

    if email_provider == "resend":
        env["RESEND_API_KEY"] = _prompt("Resend API key", password=True)
        env["EMAIL_FROM"] = _prompt("From address", f"Still Here <noreply@{base_url.split('//')[1].split('/')[0]}>")
    else:
        preset_names = ", ".join(SMTP_PRESETS.keys())
        console.print(f"  [dim]Available presets: {preset_names}[/dim]")
        preset = Prompt.ask("  SMTP preset", choices=list(SMTP_PRESETS.keys()) + ["custom"], default="brevo", console=console)
        if preset == "custom":
            env["SMTP_HOST"] = _prompt("SMTP host")
            env["SMTP_PORT"] = _prompt("SMTP port", "587")
        else:
            env["SMTP_PRESET"] = preset
        env["SMTP_USER"] = _prompt("SMTP username (email)")
        env["SMTP_PASSWORD"] = _prompt("SMTP password", password=True)
        env["EMAIL_FROM"] = _prompt("From address", f"Still Here <noreply@{base_url.split('//')[1].split('/')[0]}>")

    # Step 5: Push Notifications
    _step(5, total_steps, "Push Notifications")
    push_provider = Prompt.ask("  Push provider", choices=["webpush", "firebase", "none"], default="webpush", console=console)
    env["PUSH_PROVIDER"] = push_provider

    if push_provider == "webpush":
        console.print("  [dim]Generating VAPID keys...[/dim]")
        try:
            from py_vapid import Vapid
            v = Vapid()
            v.generate_keys()
            import base64
            raw_priv = v.private_pem()
            raw_pub = v.public_key
            # Use the vapid CLI approach
            result = subprocess.run(
                ["python", "-c", "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print(v.public_key); print(v.private_pem())"],
                capture_output=True, text=True,
            )
            console.print("  [yellow]Auto-generation requires py-vapid. Enter keys manually or install it.[/yellow]")
        except ImportError:
            pass
        env["WEBPUSH_VAPID_PUBLIC_KEY"] = _prompt("VAPID public key (base64)")
        env["WEBPUSH_VAPID_PRIVATE_KEY"] = _prompt("VAPID private key (base64)", password=True)
        env["WEBPUSH_VAPID_EMAIL"] = _prompt("VAPID contact email")
    elif push_provider == "firebase":
        env["FIREBASE_CRED_PATH"] = _prompt("Firebase credentials JSON path", "firebase/adminsdk.json")
        env["FIREBASE_API_KEY"] = _prompt("Firebase API key")
        env["FIREBASE_PROJECT_ID"] = _prompt("Firebase project ID")
        env["FIREBASE_MESSAGING_SENDER_ID"] = _prompt("Firebase messaging sender ID")
        env["FIREBASE_APP_ID"] = _prompt("Firebase app ID")
        env["FIREBASE_VAPID_KEY"] = _prompt("Firebase VAPID key")

    # Step 6: Twilio (optional)
    _step(6, total_steps, "SMS & Voice (Twilio)")
    console.print("  [dim]Optional \u2014 required for SMS/voice escalation. Press Enter to skip.[/dim]")
    twilio_sid = _prompt("Twilio Account SID (blank to skip)", "")
    if twilio_sid:
        env["TWILIO_ACCOUNT_SID"] = twilio_sid
        env["TWILIO_AUTH_TOKEN"] = _prompt("Twilio Auth Token", password=True)
        env["TWILIO_PHONE_NUMBER"] = _prompt("Twilio phone number (+1...)")
    else:
        console.print("  [dim]Skipped \u2014 SMS/voice will be logged but not sent.[/dim]")

    # Step 7: Payments (optional)
    _step(7, total_steps, "Payments (Stripe)")
    console.print("  [dim]Optional \u2014 required for the $5 lifetime payment. Press Enter to skip.[/dim]")
    stripe_key = _prompt("Stripe secret key (blank to skip)", "")
    if stripe_key:
        env["STRIPE_SECRET_KEY"] = stripe_key
        env["STRIPE_WEBHOOK_SECRET"] = _prompt("Stripe webhook secret")

    # Write .env
    console.print("\n[bold green]\u2713 Writing .env file...[/bold green]")
    write_env(env)
    console.print(f"  [dim]Saved to {ENV_PATH}[/dim]")

    # Run migrations
    if Confirm.ask("\n  Run database migrations now?", default=True, console=console):
        console.print("  [dim]Running migrations...[/dim]")
        from commands.migrate_cmd import _run_migrations
        _run_migrations(env.get("DATABASE_URL", ""))

    # Create admin account
    if Confirm.ask("\n  Create an admin account?", default=True, console=console):
        admin_email = _prompt("Admin email")
        admin_name = _prompt("Admin name")
        admin_pass = _prompt("Admin password (min 8 chars)", password=True)
        if len(admin_pass) < 8:
            console.print("  [red]Password too short. Skipping admin creation.[/red]")
        else:
            _create_admin(env.get("DATABASE_URL", ""), admin_email, admin_name, admin_pass)

    # Start containers
    if Confirm.ask("\n  Start containers now?", default=True, console=console):
        console.print("\n  [dim]Building and starting...[/dim]")
        dc = docker_compose_cmd()
        subprocess.run(dc + ["up", "-d", "--build"], cwd=str(PROJECT_ROOT))

    console.print()
    console.print(Panel.fit(
        "[bold green]Setup complete![/bold green]\n\n"
        f"Your instance is at: [bold]{env.get('BASE_URL', '')}[/bold]\n"
        "Run [bold]stillhere doctor[/bold] to verify everything is working.",
        border_style="green",
    ))


def _create_admin(db_url: str, email: str, name: str, password: str):
    """Create an admin user directly in the database."""
    try:
        import psycopg2
        import bcrypt
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        conn = psycopg2.connect(db_url, connect_timeout=5)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, name, password_hash, accepted_tos, has_paid, email_verified) "
            "VALUES (%s, %s, %s, TRUE, TRUE, TRUE) ON CONFLICT (email) DO NOTHING RETURNING id",
            (email, name, pw_hash),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if row:
            console.print(f"  [green]\u2713 Admin created: {email} (id: {row[0]})[/green]")
        else:
            console.print(f"  [yellow]User {email} already exists.[/yellow]")
    except Exception as e:
        console.print(f"  [red]\u2717 Failed to create admin: {e}[/red]")
