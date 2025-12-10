#!/usr/bin/env python3
"""
Admin CLI Tool for API Key Management

Provides commands to create, list, revoke, rotate, and monitor API keys
stored in Supabase database.

Usage:
    python manage_api_keys.py create --name "Client Name" [--expires 30] [--description "..."]
    python manage_api_keys.py list [--active-only] [--expired-only]
    python manage_api_keys.py revoke <key_id_or_name>
    python manage_api_keys.py rotate <key_id_or_name>
    python manage_api_keys.py usage <key_id_or_name> [--days 7]
    python manage_api_keys.py cleanup [--days 90]
"""

import argparse
import hashlib
import secrets
import sys
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Rich console for pretty output
console = Console()


def get_supabase_client() -> Client:
    """Get Supabase client from environment variables."""
    import os

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        console.print("[red]Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env[/red]")
        sys.exit(1)

    return create_client(url, key)


def generate_api_key() -> str:
    """Generate a cryptographically secure API key.

    Returns:
        str: 43-character URL-safe API key
    """
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256.

    Args:
        api_key: The plaintext API key

    Returns:
        str: Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_key_prefix(api_key: str) -> str:
    """Extract display prefix from API key.

    Args:
        api_key: The plaintext API key

    Returns:
        str: First 8 characters (e.g., "api_abc1")
    """
    return f"api_{api_key[:5]}"


def create_api_key(
    name: str,
    description: Optional[str] = None,
    expires_days: Optional[int] = None,
    rate_limit_minute: Optional[int] = None,
    rate_limit_hour: Optional[int] = None,
    rate_limit_day: Optional[int] = None,
    created_by: str = "admin"
):
    """Create a new API key.

    Args:
        name: Client name for the key
        description: Optional description
        expires_days: Number of days until expiration (None = never expires)
        rate_limit_minute: Requests per minute limit
        rate_limit_hour: Requests per hour limit
        rate_limit_day: Requests per day limit
        created_by: Who created this key
    """
    supabase = get_supabase_client()

    # Generate key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    key_prefix = get_key_prefix(api_key)

    # Calculate expiration
    expires_at = None
    if expires_days:
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()

    # Insert into database
    data = {
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "client_name": name,
        "description": description,
        "expires_at": expires_at,
        "rate_limit_per_minute": rate_limit_minute,
        "rate_limit_per_hour": rate_limit_hour,
        "rate_limit_per_day": rate_limit_day,
        "created_by": created_by
    }

    try:
        result = supabase.table("api_keys").insert(data).execute()

        # Display success message with key
        console.print()
        console.print(Panel.fit(
            f"[bold green]API Key Created Successfully![/bold green]\n\n"
            f"[yellow]⚠️  IMPORTANT: Save this key now - it cannot be retrieved later![/yellow]\n\n"
            f"[bold]API Key:[/bold] [cyan]{api_key}[/cyan]\n"
            f"[bold]Client:[/bold] {name}\n"
            f"[bold]ID:[/bold] {result.data[0]['id']}\n"
            f"[bold]Expires:[/bold] {expires_at if expires_at else 'Never'}\n"
            f"[bold]Rate Limits:[/bold] {rate_limit_minute or 60}/min, {rate_limit_hour or 1000}/hour, {rate_limit_day or 10000}/day",
            title="✅ Success",
            border_style="green"
        ))
        console.print()

    except Exception as e:
        console.print(f"[red]Error creating API key: {e}[/red]")
        sys.exit(1)


def list_api_keys(active_only: bool = False, expired_only: bool = False):
    """List all API keys.

    Args:
        active_only: Show only active keys
        expired_only: Show only expired keys
    """
    supabase = get_supabase_client()

    try:
        query = supabase.table("api_keys").select("*").order("created_at", desc=True)

        if active_only:
            query = query.eq("is_active", True)

        result = query.execute()
        keys = result.data

        # Filter expired keys if requested
        if expired_only:
            now = datetime.now()
            keys = [k for k in keys if k.get("expires_at") and datetime.fromisoformat(k["expires_at"].replace("Z", "+00:00")) < now]

        if not keys:
            console.print("[yellow]No API keys found.[/yellow]")
            return

        # Create table
        table = Table(title=f"API Keys ({len(keys)} total)", box=box.ROUNDED)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Prefix", style="magenta")
        table.add_column("Client Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="blue")
        table.add_column("Last Used", style="blue")
        table.add_column("Expires", style="red")
        table.add_column("Requests", justify="right")

        for key in keys:
            # Determine status
            is_active = key.get("is_active", False)
            expires_at = key.get("expires_at")

            status = "🟢 Active" if is_active else "🔴 Inactive"

            if expires_at:
                exp_date = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if exp_date < datetime.now():
                    status = "⏰ Expired"

            # Format dates
            created = datetime.fromisoformat(key["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
            last_used = "Never"
            if key.get("last_used_at"):
                last_used = datetime.fromisoformat(key["last_used_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")

            expires = "Never"
            if expires_at:
                expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00")).strftime("%Y-%m-%d")

            table.add_row(
                str(key["id"])[:8] + "...",
                key["key_prefix"] + "***",
                key["client_name"],
                status,
                created,
                last_used,
                expires,
                str(key.get("total_requests", 0))
            )

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]Error listing API keys: {e}[/red]")
        sys.exit(1)


def revoke_api_key(key_id_or_name: str, reason: str = "Manual revocation"):
    """Revoke an API key.

    Args:
        key_id_or_name: Key ID or client name
        reason: Reason for revocation
    """
    supabase = get_supabase_client()

    try:
        # Try to find by ID first, then by name
        result = supabase.table("api_keys").select("*").eq("id", key_id_or_name).execute()

        if not result.data:
            result = supabase.table("api_keys").select("*").eq("client_name", key_id_or_name).execute()

        if not result.data:
            console.print(f"[red]Error: No API key found with ID or name '{key_id_or_name}'[/red]")
            sys.exit(1)

        key = result.data[0]

        # Update key status
        update_result = supabase.table("api_keys").update({
            "is_active": False,
            "revoked_at": datetime.now().isoformat(),
            "revoked_by": "admin",
            "revoked_reason": reason
        }).eq("id", key["id"]).execute()

        console.print()
        console.print(Panel.fit(
            f"[bold red]API Key Revoked[/bold red]\n\n"
            f"[bold]Client:[/bold] {key['client_name']}\n"
            f"[bold]ID:[/bold] {key['id']}\n"
            f"[bold]Reason:[/bold] {reason}",
            title="🚫 Revoked",
            border_style="red"
        ))
        console.print()

    except Exception as e:
        console.print(f"[red]Error revoking API key: {e}[/red]")
        sys.exit(1)


def rotate_api_key(key_id_or_name: str):
    """Rotate an API key (create new, revoke old).

    Args:
        key_id_or_name: Key ID or client name
    """
    supabase = get_supabase_client()

    try:
        # Find existing key
        result = supabase.table("api_keys").select("*").eq("id", key_id_or_name).execute()

        if not result.data:
            result = supabase.table("api_keys").select("*").eq("client_name", key_id_or_name).execute()

        if not result.data:
            console.print(f"[red]Error: No API key found with ID or name '{key_id_or_name}'[/red]")
            sys.exit(1)

        old_key = result.data[0]

        # Generate new key
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        key_prefix = get_key_prefix(api_key)

        # Create new key with same settings
        new_data = {
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "client_name": old_key["client_name"],
            "description": old_key.get("description"),
            "expires_at": old_key.get("expires_at"),
            "rate_limit_per_minute": old_key.get("rate_limit_per_minute"),
            "rate_limit_per_hour": old_key.get("rate_limit_per_hour"),
            "rate_limit_per_day": old_key.get("rate_limit_per_day"),
            "created_by": "admin (rotated)"
        }

        new_result = supabase.table("api_keys").insert(new_data).execute()

        # Revoke old key
        supabase.table("api_keys").update({
            "is_active": False,
            "revoked_at": datetime.now().isoformat(),
            "revoked_by": "admin",
            "revoked_reason": "Key rotation"
        }).eq("id", old_key["id"]).execute()

        console.print()
        console.print(Panel.fit(
            f"[bold green]API Key Rotated Successfully![/bold green]\n\n"
            f"[yellow]⚠️  IMPORTANT: Save this key now - it cannot be retrieved later![/yellow]\n\n"
            f"[bold]New API Key:[/bold] [cyan]{api_key}[/cyan]\n"
            f"[bold]Client:[/bold] {old_key['client_name']}\n"
            f"[bold]New ID:[/bold] {new_result.data[0]['id']}\n"
            f"[bold]Old ID:[/bold] {old_key['id']} (revoked)",
            title="🔄 Rotated",
            border_style="green"
        ))
        console.print()

    except Exception as e:
        console.print(f"[red]Error rotating API key: {e}[/red]")
        sys.exit(1)


def show_usage(key_id_or_name: str, days: int = 7):
    """Show usage statistics for an API key.

    Args:
        key_id_or_name: Key ID or client name
        days: Number of days to show
    """
    supabase = get_supabase_client()

    try:
        # Find key
        result = supabase.table("api_keys").select("*").eq("id", key_id_or_name).execute()

        if not result.data:
            result = supabase.table("api_keys").select("*").eq("client_name", key_id_or_name).execute()

        if not result.data:
            console.print(f"[red]Error: No API key found with ID or name '{key_id_or_name}'[/red]")
            sys.exit(1)

        key = result.data[0]

        # Get usage statistics using the database function
        stats_result = supabase.rpc("get_api_key_usage_stats", {
            "p_api_key_id": key["id"],
            "p_days": days
        }).execute()

        stats = stats_result.data

        if not stats:
            console.print(f"[yellow]No usage data found for the last {days} days.[/yellow]")
            return

        # Create usage table
        table = Table(
            title=f"Usage Statistics for '{key['client_name']}' (Last {days} days)",
            box=box.ROUNDED
        )
        table.add_column("Date", style="cyan")
        table.add_column("Total Requests", justify="right", style="green")
        table.add_column("Successful", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Avg Response (ms)", justify="right", style="blue")

        total_requests = 0
        total_successful = 0
        total_failed = 0

        for stat in stats:
            total_requests += stat["total_requests"]
            total_successful += stat["successful_requests"]
            total_failed += stat["failed_requests"]

            table.add_row(
                str(stat["date"]),
                str(stat["total_requests"]),
                str(stat["successful_requests"]),
                str(stat["failed_requests"]),
                str(stat["avg_response_time_ms"] or "N/A")
            )

        console.print()
        console.print(table)
        console.print()

        # Summary
        success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        console.print(Panel.fit(
            f"[bold]Total Requests:[/bold] {total_requests}\n"
            f"[bold]Successful:[/bold] {total_successful} ([green]{success_rate:.1f}%[/green])\n"
            f"[bold]Failed:[/bold] {total_failed}",
            title="📊 Summary",
            border_style="blue"
        ))
        console.print()

    except Exception as e:
        console.print(f"[red]Error showing usage: {e}[/red]")
        sys.exit(1)


def cleanup_keys(days: int = 90):
    """Delete expired/inactive keys older than specified days.

    Args:
        days: Delete keys inactive for this many days
    """
    supabase = get_supabase_client()

    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Find keys to delete
        result = supabase.table("api_keys").select("*").eq("is_active", False).lt("created_at", cutoff_date).execute()

        keys_to_delete = result.data

        if not keys_to_delete:
            console.print(f"[yellow]No keys found that are inactive for more than {days} days.[/yellow]")
            return

        console.print(f"[yellow]Found {len(keys_to_delete)} keys to delete:[/yellow]")
        for key in keys_to_delete:
            console.print(f"  - {key['client_name']} (ID: {key['id'][:8]}...)")

        # Confirm deletion
        response = input(f"\nDelete these {len(keys_to_delete)} keys? (yes/no): ")
        if response.lower() != "yes":
            console.print("[yellow]Cleanup cancelled.[/yellow]")
            return

        # Delete keys
        for key in keys_to_delete:
            supabase.table("api_keys").delete().eq("id", key["id"]).execute()

        console.print(f"[green]✅ Deleted {len(keys_to_delete)} keys successfully.[/green]")

    except Exception as e:
        console.print(f"[red]Error during cleanup: {e}[/red]")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Admin CLI Tool for API Key Management",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument("--name", required=True, help="Client name")
    create_parser.add_argument("--description", help="Optional description")
    create_parser.add_argument("--expires", type=int, help="Days until expiration (default: never)")
    create_parser.add_argument("--rate-limit-minute", type=int, help="Requests per minute")
    create_parser.add_argument("--rate-limit-hour", type=int, help="Requests per hour")
    create_parser.add_argument("--rate-limit-day", type=int, help="Requests per day")

    # List command
    list_parser = subparsers.add_parser("list", help="List all API keys")
    list_parser.add_argument("--active-only", action="store_true", help="Show only active keys")
    list_parser.add_argument("--expired-only", action="store_true", help="Show only expired keys")

    # Revoke command
    revoke_parser = subparsers.add_parser("revoke", help="Revoke an API key")
    revoke_parser.add_argument("key_id_or_name", help="Key ID or client name")
    revoke_parser.add_argument("--reason", default="Manual revocation", help="Reason for revocation")

    # Rotate command
    rotate_parser = subparsers.add_parser("rotate", help="Rotate an API key")
    rotate_parser.add_argument("key_id_or_name", help="Key ID or client name")

    # Usage command
    usage_parser = subparsers.add_parser("usage", help="Show usage statistics")
    usage_parser.add_argument("key_id_or_name", help="Key ID or client name")
    usage_parser.add_argument("--days", type=int, default=7, help="Number of days (default: 7)")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Delete old inactive keys")
    cleanup_parser.add_argument("--days", type=int, default=90, help="Delete keys inactive for N days (default: 90)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "create":
        create_api_key(
            name=args.name,
            description=args.description,
            expires_days=args.expires,
            rate_limit_minute=args.rate_limit_minute,
            rate_limit_hour=args.rate_limit_hour,
            rate_limit_day=args.rate_limit_day
        )
    elif args.command == "list":
        list_api_keys(
            active_only=args.active_only,
            expired_only=args.expired_only
        )
    elif args.command == "revoke":
        revoke_api_key(args.key_id_or_name, args.reason)
    elif args.command == "rotate":
        rotate_api_key(args.key_id_or_name)
    elif args.command == "usage":
        show_usage(args.key_id_or_name, args.days)
    elif args.command == "cleanup":
        cleanup_keys(args.days)


if __name__ == "__main__":
    main()
