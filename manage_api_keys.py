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
from datetime import datetime, timedelta, timezone
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


def generate_slug(name: str) -> str:
    """Generate URL-safe slug from organization name.

    Args:
        name: Organization name

    Returns:
        str: Lowercase slug with hyphens
    """
    import re
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug


def get_tier_limits(tier: str) -> dict:
    """Fetch rate limits for a given tier from database.

    Args:
        tier: Tier name (free, basic, professional, enterprise, custom)

    Returns:
        dict: Rate limits with keys: rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day
    """
    supabase = get_supabase_client()
    
    try:
        result = supabase.table("api_key_tiers").select("*").eq("tier_name", tier).execute()
        
        if result.data and len(result.data) > 0:
            tier_config = result.data[0]
            return {
                "rate_limit_per_minute": tier_config["rate_limit_per_minute"],
                "rate_limit_per_hour": tier_config["rate_limit_per_hour"],
                "rate_limit_per_day": tier_config["rate_limit_per_day"]
            }
        else:
            # Fallback to basic tier defaults if tier not found
            console.print(f"[yellow]Warning: Tier '{tier}' not found in database. Using basic tier defaults.[/yellow]")
            return {
                "rate_limit_per_minute": 60,
                "rate_limit_per_hour": 1000,
                "rate_limit_per_day": 10000
            }
    except Exception as e:
        console.print(f"[yellow]Warning: Could not fetch tier limits: {e}. Using defaults.[/yellow]")
        return {
            "rate_limit_per_minute": 60,
            "rate_limit_per_hour": 1000,
            "rate_limit_per_day": 10000
        }


def get_or_create_individual_org(email: str, tier: str = "free") -> str:
    """Get or create a personal organization for an individual user.

    This creates a hidden "personal" organization (Notion-style approach).
    The organization is not shown in the UI for the individual user.

    Args:
        email: User's email address
        tier: Subscription tier (default: free)

    Returns:
        str: Organization ID (UUID)
    """
    supabase = get_supabase_client()

    try:
        # Call database function to get or create individual org
        result = supabase.rpc("get_or_create_individual_org", {
            "user_email": email,
            "user_tier": tier
        }).execute()

        return result.data

    except Exception as e:
        console.print(f"[red]Error creating individual organization: {e}[/red]")
        raise


def get_or_create_organization(
    name: str,
    tier: str = "free",
    email: Optional[str] = None,
    is_individual: bool = False
) -> str:
    """Get existing organization by name or create new one.

    Args:
        name: Organization name
        tier: Subscription tier
        email: Primary contact email
        is_individual: If True, creates a personal org (hidden from UI)

    Returns:
        str: Organization ID (UUID)
    """
    supabase = get_supabase_client()

    # If this is for an individual user, use the individual org function
    if is_individual or name.lower() in ["individual", "individuals", "personal", "solo"]:
        if not email:
            console.print("[red]Error: Email required for individual organizations[/red]")
            raise ValueError("Email required for individual organizations")
        return get_or_create_individual_org(email, tier)

    # Generate slug for real organization
    slug = generate_slug(name)

    try:
        # Check if organization exists by slug
        result = supabase.table("organizations").select("id").eq("slug", slug).eq("is_individual", False).execute()

        if result.data:
            return result.data[0]["id"]

        # Create new REAL organization (not individual)
        data = {
            "name": name,
            "slug": slug,
            "tier": tier,
            "primary_contact_email": email,
            "is_individual": False  # Explicitly mark as real org
        }

        result = supabase.table("organizations").insert(data).execute()
        return result.data[0]["id"]

    except Exception as e:
        console.print(f"[red]Error with organization: {e}[/red]")
        raise


def create_api_key(
    name: str,
    email: Optional[str] = None,
    organization: Optional[str] = None,
    tier: str = "free",
    description: Optional[str] = None,
    expires_days: Optional[int] = None,
    rate_limit_minute: Optional[int] = None,
    rate_limit_hour: Optional[int] = None,
    rate_limit_day: Optional[int] = None,
    created_by: str = "admin"
):
    """Create a new API key.

    Args:
        name: Client name for the key (e.g., "Production Server")
        email: User email address (for identification)
        organization: Organization name (e.g., "The Jo Law Firm")
        tier: Subscription tier (applies to organization, not individual key)
        description: Optional description
        expires_days: Number of days until expiration (None = never expires)
        rate_limit_minute: Requests per minute limit
        rate_limit_hour: Requests per hour limit
        rate_limit_day: Requests per day limit
        created_by: Who created this key
    """
    supabase = get_supabase_client()

    # Validate email is provided for individuals
    if not organization and not email:
        console.print("[red]Error: Email is required when no organization is specified[/red]")
        sys.exit(1)

    # Get or create organization
    if organization:
        # User specified an organization name - create a real org
        organization_id = get_or_create_organization(organization, tier, email, is_individual=False)
    else:
        # No organization specified - create personal org for this individual
        organization_id = get_or_create_individual_org(email, tier)
        organization = "Individual"  # Display name (for backward compatibility)

    # Generate key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    key_prefix = get_key_prefix(api_key)

    # Calculate expiration
    expires_at = None
    if expires_days:
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()

    # Get tier-based rate limits if custom limits not specified
    tier_limits = get_tier_limits(tier)
    final_rate_limit_minute = rate_limit_minute if rate_limit_minute is not None else tier_limits["rate_limit_per_minute"]
    final_rate_limit_hour = rate_limit_hour if rate_limit_hour is not None else tier_limits["rate_limit_per_hour"]
    final_rate_limit_day = rate_limit_day if rate_limit_day is not None else tier_limits["rate_limit_per_day"]

    # Insert into database
    data = {
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "client_name": name,
        "email": email,
        "organization": organization,  # Display name (kept for backward compatibility)
        "organization_id": organization_id,  # NEW: Foreign key to organizations table
        "tier": tier,
        "description": description,
        "expires_at": expires_at,
        "rate_limit_per_minute": final_rate_limit_minute,
        "rate_limit_per_hour": final_rate_limit_hour,
        "rate_limit_per_day": final_rate_limit_day,
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
            f"[bold]Tier:[/bold] {tier.upper()}\n"
            f"[bold]ID:[/bold] {result.data[0]['id']}\n"
            f"[bold]Expires:[/bold] {expires_at if expires_at else 'Never'}\n"
            f"[bold]Rate Limits:[/bold] {final_rate_limit_minute}/min, {final_rate_limit_hour}/hour, {final_rate_limit_day}/day",
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
            now = datetime.now(timezone.utc)
            keys = [k for k in keys if k.get("expires_at") and datetime.fromisoformat(k["expires_at"].replace("Z", "+00:00")) < now]

        if not keys:
            console.print("[yellow]No API keys found.[/yellow]")
            return

        # Create table
        table = Table(title=f"API Keys ({len(keys)} total)", box=box.ROUNDED)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Prefix", style="magenta")
        table.add_column("Client Name", style="green")
        table.add_column("Email", style="blue")
        table.add_column("Organization", style="cyan")
        table.add_column("Tier", style="yellow")
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
                if exp_date < datetime.now(timezone.utc):
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
                key.get("email", "-") or "-",
                key.get("organization", "-") or "-",
                key.get("tier", "free") or "free",
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


def list_organizations():
    """List all organizations with usage statistics."""
    supabase = get_supabase_client()

    try:
        # Call database function
        result = supabase.rpc("list_organizations_with_usage").execute()
        orgs = result.data

        if not orgs:
            console.print("[yellow]No organizations found.[/yellow]")
            return

        # Create table
        table = Table(title="Organizations", box=box.ROUNDED)
        table.add_column("Name", style="green")
        table.add_column("Slug", style="cyan")
        table.add_column("Tier", style="yellow")
        table.add_column("Keys Used", justify="right")
        table.add_column("Keys Limit", justify="right")
        table.add_column("Users", justify="right", style="blue")
        table.add_column("Requests", justify="right", style="magenta")
        table.add_column("Status", style="yellow")

        for org in orgs:
            # Skip individual personal orgs (hidden from UI)
            if org.get("is_individual", False):
                continue

            status = "🟢 Active" if org["is_active"] else "🔴 Inactive"
            usage = f"{org['keys_used']}/{org['keys_limit']}"

            table.add_row(
                org["name"],
                org["slug"],
                org["tier"].upper(),
                str(org["keys_used"]),
                str(org["keys_limit"]),
                str(org["unique_users"]),
                str(org["total_requests"]),
                status
            )

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]Error listing organizations: {e}[/red]")
        sys.exit(1)


def create_organization(
    name: str,
    tier: str = "free",
    email: Optional[str] = None,
    website: Optional[str] = None
):
    """Create a new organization.

    Args:
        name: Organization name
        tier: Subscription tier
        email: Primary contact email
        website: Organization website
    """
    supabase = get_supabase_client()

    slug = generate_slug(name)

    try:
        # Check if slug already exists
        result = supabase.table("organizations").select("id").eq("slug", slug).execute()

        if result.data:
            console.print(f"[yellow]Organization with slug '{slug}' already exists.[/yellow]")
            return

        # Create organization
        data = {
            "name": name,
            "slug": slug,
            "tier": tier,
            "primary_contact_email": email,
            "website": website
        }

        result = supabase.table("organizations").insert(data).execute()

        console.print()
        console.print(Panel(
            f"[green]✅ Organization created successfully![/green]\n\n"
            f"Name: {name}\n"
            f"Slug: {slug}\n"
            f"Tier: {tier}\n"
            f"ID: {result.data[0]['id']}",
            title="Organization Created",
            border_style="green"
        ))
        console.print()

    except Exception as e:
        console.print(f"[red]Error creating organization: {e}[/red]")
        sys.exit(1)


def list_tiers():
    """List all available subscription tiers."""
    supabase = get_supabase_client()

    try:
        result = supabase.table("api_key_tiers").select("*").order("max_keys_per_email").execute()
        tiers = result.data

        if not tiers:
            console.print("[yellow]No tiers configured.[/yellow]")
            return

        # Create table
        table = Table(title="Subscription Tiers", box=box.ROUNDED)
        table.add_column("Tier", style="cyan")
        table.add_column("Max Keys", justify="right", style="green")
        table.add_column("Rate/Min", justify="right")
        table.add_column("Rate/Hour", justify="right")
        table.add_column("Rate/Day", justify="right")
        table.add_column("Price/Month", justify="right", style="yellow")
        table.add_column("Description", style="blue")

        for tier in tiers:
            price = f"${tier['price_monthly']}" if tier['price_monthly'] else "Custom"
            table.add_row(
                tier["tier_name"].upper(),
                str(tier["max_keys_per_email"]),
                str(tier["rate_limit_per_minute"]),
                str(tier["rate_limit_per_hour"]),
                str(tier["rate_limit_per_day"]),
                price,
                tier.get("description", "-")
            )

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]Error listing tiers: {e}[/red]")
        sys.exit(1)


def change_organization_tier(org_slug: str, new_tier: str):
    """Change an organization's subscription tier.

    Args:
        org_slug: Organization slug (e.g., "acme-corp")
        new_tier: New tier name
    """
    supabase = get_supabase_client()

    try:
        # Get organization ID from slug
        result = supabase.table("organizations").select("id").eq("slug", org_slug).execute()

        if not result.data:
            console.print(f"[red]Organization '{org_slug}' not found.[/red]")
            return

        org_id = result.data[0]["id"]

        # Call database function
        result = supabase.rpc("change_organization_tier", {
            "org_id": org_id,
            "new_tier": new_tier
        }).execute()

        message = result.data if result.data else "Tier changed successfully"
        
        if "Cannot downgrade" in str(message):
            console.print(f"[red]{message}[/red]")
        else:
            console.print(f"[green]✅ {message}[/green]")
            console.print(f"\n[yellow]Note: Restart the server to apply new rate limits.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error changing tier: {e}[/red]")
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
    create_parser.add_argument("--name", required=True, help="Client name (e.g., 'Production Server')")
    create_parser.add_argument("--email", help="User email address (unique identifier)")
    create_parser.add_argument("--organization", help="Organization name (e.g., 'The Jo Law Firm')")
    create_parser.add_argument("--tier", default="free", choices=["free", "basic", "professional", "enterprise", "custom"], help="Subscription tier (default: free)")
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

    # Tiers command
    tiers_parser = subparsers.add_parser("tiers", help="List all subscription tiers")

    # Organizations command
    orgs_parser = subparsers.add_parser("orgs", help="List all organizations")

    # Create organization command
    create_org_parser = subparsers.add_parser("create-org", help="Create a new organization")
    create_org_parser.add_argument("--name", required=True, help="Organization name")
    create_org_parser.add_argument("--tier", default="free", choices=["free", "basic", "professional", "enterprise", "custom"], help="Subscription tier (default: free)")
    create_org_parser.add_argument("--email", help="Primary contact email")
    create_org_parser.add_argument("--website", help="Organization website")

    # Change tier command
    change_tier_parser = subparsers.add_parser("change-tier", help="Change organization's subscription tier")
    change_tier_parser.add_argument("org_slug", help="Organization slug (e.g., 'acme-corp')")
    change_tier_parser.add_argument("tier", choices=["free", "basic", "professional", "enterprise", "custom"], help="New tier")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "create":
        create_api_key(
            name=args.name,
            email=args.email,
            organization=args.organization,
            tier=args.tier,
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
    elif args.command == "tiers":
        list_tiers()
    elif args.command == "orgs":
        list_organizations()
    elif args.command == "create-org":
        create_organization(
            name=args.name,
            tier=args.tier,
            email=args.email,
            website=args.website
        )
    elif args.command == "change-tier":
        change_organization_tier(args.org_slug, args.tier)


if __name__ == "__main__":
    main()
