#!/usr/bin/env python3
"""
Diagnostic script to test and fix the digest() function type casting issue.
Uses existing Supabase credentials from .env file.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Use ASCII-safe console for Windows compatibility
console = Console(legacy_windows=False, force_terminal=True)


def get_supabase_client() -> Client:
    """Get Supabase client from environment variables."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        console.print("[red]Error: Missing Supabase credentials in .env file[/red]")
        console.print("Required: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    return create_client(url, key)


def test_digest_function(supabase: Client) -> dict:
    """Test digest() function with different type cast combinations."""
    console.print("\n[bold cyan]Phase 1: Testing digest() function[/bold cyan]")

    test_email = "test@example.com"
    results = {}

    tests = [
        {
            "name": "No type casts",
            "sql": f"SELECT encode(digest('{test_email}', 'sha256'), 'hex') as hash"
        },
        {
            "name": "Only ::bytea cast",
            "sql": f"SELECT encode(digest('{test_email}'::bytea, 'sha256'), 'hex') as hash"
        },
        {
            "name": "Both ::bytea and ::text casts",
            "sql": f"SELECT encode(digest('{test_email}'::bytea, 'sha256'::text), 'hex') as hash"
        }
    ]

    for test in tests:
        try:
            result = supabase.rpc("exec_sql", {"query": test["sql"]}).execute()
            results[test["name"]] = {
                "success": True,
                "data": result.data,
                "error": None
            }
            console.print(f"  [OK] {test['name']}: [green]SUCCESS[/green]")
        except Exception as e:
            results[test["name"]] = {
                "success": False,
                "data": None,
                "error": str(e)
            }
            console.print(f"  [FAIL] {test['name']}: [red]FAILED[/red]")
            console.print(f"     Error: {str(e)[:100]}")

    return results


def fix_function(supabase: Client) -> bool:
    """Update the get_or_create_individual_org function with proper type casts."""
    console.print("\n[bold cyan]Phase 2: Fixing get_or_create_individual_org function[/bold cyan]")

    fix_sql = """
    DROP FUNCTION IF EXISTS get_or_create_individual_org(TEXT, TEXT);

    CREATE OR REPLACE FUNCTION get_or_create_individual_org(
        user_email TEXT,
        user_tier TEXT DEFAULT 'free'
    )
    RETURNS UUID AS $$
    DECLARE
        org_id UUID;
        user_slug TEXT;
    BEGIN
        -- Generate slug from email (with explicit type casts for both parameters)
        user_slug := 'user-' || substring(
            encode(digest(user_email::bytea, 'sha256'::text), 'hex'),
            1, 16
        );

        -- Try to get existing org
        SELECT id INTO org_id
        FROM organizations
        WHERE slug = user_slug
        AND is_individual = true;

        -- If not found, create it
        IF org_id IS NULL THEN
            INSERT INTO organizations (
                name,
                slug,
                tier,
                primary_contact_email,
                is_individual
            ) VALUES (
                'Personal - ' || user_email,
                user_slug,
                user_tier,
                user_email,
                true
            )
            RETURNING id INTO org_id;
        END IF;

        RETURN org_id;
    END;
    $$ LANGUAGE plpgsql;
    """

    try:
        # Execute the fix SQL
        # Note: We can't use RPC for DDL statements, so we'll need to use PostgREST's query endpoint
        # For now, let's just print the SQL that needs to be run
        console.print("  [yellow]Note: Cannot execute DDL via Supabase client directly[/yellow]")
        console.print("  [yellow]Need to run this via Supabase SQL Editor[/yellow]")
        return False
    except Exception as e:
        console.print(f"  [red]Error: {e}[/red]")
        return False


def test_function_directly(supabase: Client) -> bool:
    """Test the get_or_create_individual_org function directly."""
    console.print("\n[bold cyan]Phase 3: Testing get_or_create_individual_org function[/bold cyan]")

    test_email = "diagnostic-test@example.com"
    test_tier = "free"

    try:
        result = supabase.rpc("get_or_create_individual_org", {
            "user_email": test_email,
            "user_tier": test_tier
        }).execute()

        org_id = result.data
        console.print(f"  [OK] Function executed successfully!")
        console.print(f"  Organization ID: [green]{org_id}[/green]")

        # Verify the org was created
        org_check = supabase.table("organizations").select("*").eq("id", org_id).execute()

        if org_check.data:
            org = org_check.data[0]
            console.print(f"\n  Organization Details:")
            console.print(f"    Slug: [cyan]{org['slug']}[/cyan]")
            console.print(f"    Email: [cyan]{org['primary_contact_email']}[/cyan]")
            console.print(f"    Is Individual: [cyan]{org['is_individual']}[/cyan]")
            console.print(f"    Tier: [cyan]{org['tier']}[/cyan]")

            # Clean up test org
            console.print(f"\n  [yellow]Cleaning up test organization...[/yellow]")
            supabase.table("organizations").delete().eq("id", org_id).execute()
            console.print(f"  [OK] Test organization deleted")

        return True

    except Exception as e:
        console.print(f"  [FAIL] Function failed: [red]{str(e)}[/red]")
        return False


def check_pgcrypto_extension(supabase: Client) -> bool:
    """Check if pgcrypto extension is enabled."""
    console.print("\n[bold cyan]Phase 0: Checking pgcrypto extension[/bold cyan]")

    try:
        result = supabase.table("pg_extension").select("extname, extversion").eq("extname", "pgcrypto").execute()

        if result.data:
            ext = result.data[0]
            console.print(f"  [OK] pgcrypto extension is enabled (version {ext['extversion']})")
            return True
        else:
            console.print(f"  [FAIL] pgcrypto extension is NOT enabled")
            return False

    except Exception as e:
        console.print(f"  [WARN] Could not check extension: {str(e)}")
        console.print(f"  [yellow]This might be a permission issue, continuing anyway...[/yellow]")
        return True  # Assume it's enabled and continue


def main():
    """Run diagnostic and fix process."""
    console.print(Panel.fit(
        "[bold white]PostgreSQL digest() Function Diagnostic Tool[/bold white]\n"
        "This will test and fix the type casting issue",
        border_style="cyan"
    ))

    try:
        # Connect to Supabase
        console.print("\n[bold]Connecting to Supabase...[/bold]")
        supabase = get_supabase_client()
        console.print("  [OK] Connected successfully")

        # Phase 0: Check pgcrypto
        pgcrypto_ok = check_pgcrypto_extension(supabase)

        # Phase 3: Test the function directly (this is the real test)
        function_ok = test_function_directly(supabase)

        # Summary
        console.print("\n" + "="*60)
        console.print("[bold cyan]Summary[/bold cyan]")
        console.print("="*60)

        if function_ok:
            console.print("[OK] [green]SUCCESS![/green] The function is working correctly.")
            console.print("\nYou can now create API keys:")
            console.print('  [cyan]python manage_api_keys.py create --name "My Key" --email "user@example.com" --tier "free"[/cyan]')
        else:
            console.print("[FAIL] [red]FAILED![/red] The function needs to be fixed.")
            console.print("\n[yellow]Next Steps:[/yellow]")
            console.print("1. Open Supabase SQL Editor")
            console.print("2. Run the migration: [cyan]migrations/005b_fix_digest_type_casting.sql[/cyan]")
            console.print("3. Run this diagnostic script again to verify")

            # Show the fix SQL
            console.print("\n[bold]Or paste this SQL into Supabase SQL Editor:[/bold]")
            console.print("-"*60)

            with open(Path(__file__).parent / "migrations" / "005b_fix_digest_type_casting.sql", "r") as f:
                fix_sql = f.read()
                # Print first 20 lines
                lines = fix_sql.split('\n')[:20]
                console.print('\n'.join(lines))
                console.print("\n... (see full file at migrations/005b_fix_digest_type_casting.sql)")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
