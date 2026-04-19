"""stillhere migrate — Apply pending SQL migrations."""
import click
from rich.console import Console

from commands.shared import MIGRATIONS_DIR, ENV_PATH, console, check_mark, load_env

console = Console()


def _run_migrations(db_url: str):
    """Apply all SQL migration files in order."""
    import psycopg2

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        console.print("  [dim]No migration files found.[/dim]")
        return

    try:
        conn = psycopg2.connect(db_url, connect_timeout=10)
        conn.autocommit = True
        cur = conn.cursor()

        for f in sql_files:
            name = f.name
            sql = f.read_text().strip()
            if not sql:
                console.print(f"  [dim]\u2500 {name} (empty, skipped)[/dim]")
                continue
            try:
                cur.execute(sql)
                console.print(f"  {check_mark(True)} {name}")
            except psycopg2.errors.DuplicateColumn:
                conn.rollback()
                conn.autocommit = True
                console.print(f"  [dim]\u2500 {name} (already applied)[/dim]")
            except psycopg2.errors.DuplicateTable:
                conn.rollback()
                conn.autocommit = True
                console.print(f"  [dim]\u2500 {name} (already applied)[/dim]")
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                conn.autocommit = True
                console.print(f"  [dim]\u2500 {name} (data already seeded)[/dim]")
            except Exception as e:
                conn.rollback()
                conn.autocommit = True
                console.print(f"  {check_mark(False)} {name}: [red]{e}[/red]")

        cur.close()
        conn.close()
        console.print(f"\n  [green]\u2713 Migrations complete.[/green]")
    except Exception as e:
        console.print(f"  [red]\u2717 Database connection failed: {e}[/red]")


@click.command()
def migrate():
    """Apply pending SQL migrations to the database."""
    console.print("\n[bold]Running migrations...[/bold]")

    env = load_env()
    db_url = env.get("DATABASE_URL", "")
    if not db_url:
        console.print("  [red]\u2717 DATABASE_URL not found in .env[/red]")
        console.print("  [dim]Run 'stillhere init' to configure your database.[/dim]")
        return

    _run_migrations(db_url)
