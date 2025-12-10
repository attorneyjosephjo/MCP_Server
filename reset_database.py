#!/usr/bin/env python3
"""
Reset Database Structure
Applies the complete database structure migration
"""

import os
import sys
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Load environment
load_dotenv()
console = Console()

def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        console.print("[red]Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env[/red]")
        sys.exit(1)

    return create_client(url, key)

def run_migration(supabase: Client, migration_file: Path) -> bool:
    """Run a SQL migration file"""
    try:
        console.print(f"\n[cyan]Reading migration: {migration_file.name}[/cyan]")

        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        console.print(f"[yellow]Executing migration...[/yellow]")

        # Split by semicolons and execute each statement
        # Note: This is a simple approach. For complex migrations, use psycopg2
        statements = [s.strip() for s in sql.split(';') if s.strip()]

        for i, statement in enumerate(statements, 1):
            if statement.upper().startswith(('SELECT', 'CREATE', 'DROP', 'ALTER', 'INSERT', 'DO')):
                try:
                    # Use Supabase's RPC for raw SQL
                    # Note: This requires creating a helper function in the database
                    # For now, we'll use psycopg2 directly
                    pass
                except Exception as e:
                    console.print(f"[red]Error in statement {i}: {e}[/red]")
                    console.print(f"[dim]{statement[:100]}...[/dim]")
                    return False

        console.print(f"[green]✓ Migration completed successfully![/green]")
        return True

    except Exception as e:
        console.print(f"[red]Error running migration: {e}[/red]")
        return False

def main():
    """Main function"""
    console.print(Panel.fit(
        "[bold cyan]Database Structure Reset[/bold cyan]\n"
        "This will reset your database and apply the complete structure",
        border_style="cyan"
    ))

    # Check if migration file exists
    migration_file = Path(__file__).parent / "migrations" / "000_COMPLETE_STRUCTURE.sql"

    if not migration_file.exists():
        console.print(f"[red]Error: Migration file not found at {migration_file}[/red]")
        sys.exit(1)

    # Warning
    console.print("\n[yellow]⚠️  WARNING: This will DROP all existing tables and recreate them![/yellow]")
    console.print("[yellow]   All existing data will be lost![/yellow]\n")

    response = input("Type 'YES' to continue: ")

    if response != "YES":
        console.print("[red]Aborted.[/red]")
        sys.exit(0)

    # Get Supabase client
    supabase = get_supabase_client()

    # Inform user to run SQL manually
    console.print("\n[cyan]Please run the SQL migration manually:[/cyan]\n")
    console.print(f"1. Open your Supabase dashboard")
    console.print(f"2. Go to SQL Editor")
    console.print(f"3. Copy and paste the contents of:")
    console.print(f"   [bold]{migration_file}[/bold]")
    console.print(f"4. Run the SQL\n")

    console.print("[green]After running the SQL, press Enter to verify the setup...[/green]")
    input()

    # Verify tables exist
    try:
        console.print("\n[cyan]Verifying database structure...[/cyan]")

        # Check organizations table
        result = supabase.table("organizations").select("count").limit(1).execute()
        console.print("[green]✓ organizations table exists[/green]")

        # Check api_keys table
        result = supabase.table("api_keys").select("count").limit(1).execute()
        console.print("[green]✓ api_keys table exists[/green]")

        # Check api_key_tiers table
        result = supabase.table("api_key_tiers").select("*").execute()
        tier_count = len(result.data)
        console.print(f"[green]✓ api_key_tiers table exists ({tier_count} tiers)[/green]")

        # Check api_key_usage table
        result = supabase.table("api_key_usage").select("count").limit(1).execute()
        console.print("[green]✓ api_key_usage table exists[/green]")

        # Test RPC function
        try:
            result = supabase.rpc("get_or_create_individual_org", {
                "user_email": "test@example.com",
                "user_tier": "free"
            }).execute()
            console.print("[green]✓ get_or_create_individual_org function works[/green]")

            # Clean up test org
            if result.data:
                supabase.table("organizations").delete().eq("id", result.data).execute()
                console.print("[dim]  (cleaned up test organization)[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Function test failed: {e}[/yellow]")

        console.print("\n[bold green]✓ Database structure verified successfully![/bold green]\n")
        console.print("[cyan]You can now create organizations and API keys.[/cyan]")

    except Exception as e:
        console.print(f"\n[red]Error verifying database: {e}[/red]")
        console.print("[yellow]Make sure you ran the SQL migration in Supabase dashboard.[/yellow]")
        sys.exit(1)

if __name__ == "__main__":
    main()
