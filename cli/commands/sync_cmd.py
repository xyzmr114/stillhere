"""stillhere sync-numbers — Pull latest non-emergency numbers from db.stillherehq.com."""
import click
from rich.console import Console

from commands.shared import console, check_mark, load_env

NE_API_URL = "https://db.stillherehq.com/v1/numbers"
FALLBACK_URL = "http://localhost:8900/v1/numbers"


@click.command("sync-numbers")
@click.option("--url", default=NE_API_URL, help="Override API URL")
def sync_numbers(url: str):
    """Pull latest non-emergency numbers from the public API."""
    import httpx

    console.print("\n[bold]Syncing non-emergency numbers...[/bold]")

    env = load_env()
    db_url = env.get("DATABASE_URL", "")
    if not db_url:
        console.print("  [red]\u2717 DATABASE_URL not found in .env[/red]")
        return

    # Fetch from API
    console.print(f"  [dim]Fetching from {url}...[/dim]")
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        numbers = data.get("numbers", [])
    except Exception:
        if url == NE_API_URL:
            console.print(f"  [yellow]\u26a0 Primary API unreachable, trying local fallback...[/yellow]")
            try:
                resp = httpx.get(FALLBACK_URL, timeout=5)
                resp.raise_for_status()
                data = resp.json()
                numbers = data.get("numbers", [])
            except Exception as e2:
                console.print(f"  [red]\u2717 Both APIs unreachable: {e2}[/red]")
                return
        else:
            console.print(f"  [red]\u2717 API unreachable[/red]")
            return

    if not numbers:
        console.print("  [yellow]No numbers returned from API.[/yellow]")
        return

    console.print(f"  [dim]Received {len(numbers)} numbers. Inserting into database...[/dim]")

    # Insert into database
    try:
        import psycopg2
        conn = psycopg2.connect(db_url, connect_timeout=10)
        cur = conn.cursor()

        # Ensure table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS non_emergency_numbers (
                id SERIAL PRIMARY KEY,
                state TEXT NOT NULL,
                city TEXT NOT NULL,
                phone TEXT NOT NULL,
                department TEXT,
                source_url TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        inserted = 0
        updated = 0
        for n in numbers:
            cur.execute(
                "SELECT id FROM non_emergency_numbers WHERE LOWER(city) = LOWER(%s) AND LOWER(state) = LOWER(%s)",
                (n["city"], n["state"]),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    "UPDATE non_emergency_numbers SET phone = %s, department = %s, source_url = %s, updated_at = NOW() "
                    "WHERE id = %s",
                    (n["phone"], n.get("department", ""), n.get("source_url", ""), existing[0]),
                )
                updated += 1
            else:
                cur.execute(
                    "INSERT INTO non_emergency_numbers (state, city, phone, department, source_url) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (n["state"], n["city"], n["phone"], n.get("department", ""), n.get("source_url", "")),
                )
                inserted += 1

        conn.commit()
        cur.close()
        conn.close()

        console.print(f"  {check_mark(True)} Done: {inserted} inserted, {updated} updated")
    except Exception as e:
        console.print(f"  [red]\u2717 Database error: {e}[/red]")
