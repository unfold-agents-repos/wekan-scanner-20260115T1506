"""
CLI for wekan API Scanner

Auto-discovers registered API actions and exposes them as CLI commands.
Category writers only need to use @action and @all_action decorators.

Usage:
    wekan-scanner --url <URL> <category> <action> [args...]

Examples:
    wekan-scanner --url http://localhost:8080 boards list --limit 50
    wekan-scanner --url http://localhost:8080 boards get --board-id abc123
    wekan-scanner --url http://localhost:8080 boards all
    wekan-scanner --url http://localhost:8080 all  # Run all categories
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import argparse
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Callable

import defopt
import logfire

from .client import WekanClient, WekanClientConfig

if TYPE_CHECKING:
    pass

logfire.configure(send_to_logfire="if-token-present", scrubbing=False)


# =============================================================================
# Global Configuration
# =============================================================================

@dataclass
class GlobalConfig:
    """Global configuration set before subcommand dispatch."""

    url: str
    """Base URL for the API."""

    verbose: bool = False
    """Enable verbose logging."""

    verify_ssl: bool = True
    """Verify SSL certificates."""

    token: str | None = None
    """Authentication token for the API."""


# Singleton instance - set by parse_global_args()
CONFIG: GlobalConfig | None = None


def create_global_parser() -> "argparse.ArgumentParser":
    """Create the global argument parser with all options."""


    parser = argparse.ArgumentParser(
        prog="wekan-scanner",
        description="CLI for wekan API Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,  # We'll handle help manually to append category info
    )
    parser.add_argument("--url", "-u", default=os.getenv("WEKAN_URL"),
                        help="Base URL for the API (or set WEKAN_URL env var)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--no-verify-ssl", action="store_true",
                        help="Disable SSL certificate verification")
    parser.add_argument("--help", "-h", action="store_true",
                        help="Show this help message and exit")
    parser.add_argument("--token", default=os.getenv("WEKAN_API_TOKEN"),
                        help="API token for authentication (or set WEKAN_API_TOKEN env var)")

    return parser


def print_global_help(parser: "argparse.ArgumentParser"):
    """Print argparse help plus available categories and actions."""
    import_all_categories()
    from .registry import get_categories, list_actions

    # Print argparse-generated help
    parser.print_help()

    # Append category/action info
    cats = get_categories()
    print("\nCommands:")
    print("    all                    Run all actions across all categories")
    print("    <category> all         Run all actions in a category")
    print("    <category> <action>    Run a specific action")

    if cats:
        print("\nCategories:")
        for cat in sorted(cats):
            actions = list_actions(cat)
            print(f"    {cat:<20} Actions: {', '.join(actions) or 'all'}")
    else:
        print("\nCategories: none registered yet")

    print(f"""
Examples:
    wekan-scanner --url http://localhost:8080 boards list --limit 50
    wekan-scanner --url http://localhost:8080 boards all
    wekan-scanner --url http://localhost:8080 all
""")


def parse_global_args(argv: list[str]) -> tuple[GlobalConfig, list[str]]:
    """
    Parse global arguments before subcommand.

    Args:
        argv: Command line arguments (sys.argv[1:])

    Returns:
        Tuple of (GlobalConfig, remaining_argv)
    """
    parser = create_global_parser()
    args, remaining = parser.parse_known_args(argv)

    # Handle help flag - show full help with categories
    if args.help:
        print_global_help(parser)
        sys.exit(0)

    if not args.url:
        print("Error: --url is required (or set WEKAN_URL)", file=sys.stderr)
        sys.exit(1)

    return GlobalConfig(
        url=args.url,
        verbose=args.verbose,
        verify_ssl=not args.no_verify_ssl,
        token=args.token,
    ), remaining


# =============================================================================
# Client Factory
# =============================================================================

async def get_client() -> WekanClient:
    """
    Create and return a configured API client.

    Returns:
        Configured WekanClient instance
    """
    if CONFIG is None:
        raise RuntimeError("Global config not initialized")

    config = WekanClientConfig(
        base_url=CONFIG.url,
        verify_ssl=CONFIG.verify_ssl,
        token=CONFIG.token,
    )

    return WekanClient(config)


# =============================================================================
# Action Wrapper for defopt
# =============================================================================

def create_action_wrapper(func: Callable) -> Callable:
    """
    Wrap an async action function for use with defopt.

    - Removes the `client` parameter (injected automatically)
    - Converts async to sync via asyncio.run
    - Preserves signature, docstring, and type hints for defopt
    """
    # Get the original signature
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Remove 'client' parameter (should be first)
    if params and params[0].name == 'client':
        params = params[1:]

    # Create new signature without client
    new_sig = sig.replace(parameters=params)

    @wraps(func)
    def wrapper(*args, **kwargs):
        async def _run():
            async with await get_client() as client:
                result = await func(client, *args, **kwargs)
                # Print result if it's not None and not an int (exit code)
                if result is not None and not isinstance(result, int):
                    if hasattr(result, 'model_dump'):
                        print(json.dumps(result.model_dump(mode='json'), indent=2))
                    elif isinstance(result, list):
                        for item in result:
                            if hasattr(item, 'model_dump'):
                                print(json.dumps(item.model_dump(mode='json'), indent=2))
                            else:
                                print(item)
                    else:
                        print(result)
                return result if isinstance(result, int) else 0

        return asyncio.run(_run())

    # Update wrapper signature for defopt
    wrapper.__signature__ = new_sig  # type: ignore
    return wrapper


# =============================================================================
# Category Discovery and Import
# =============================================================================

def import_all_categories():
    """Import all category modules to trigger registration."""
    # Import the api package which auto-imports all categories
    from scanner import api  # noqa: F401

    # Also explicitly import any modules that might be added
    import importlib
    import pkgutil

    for _, module_name, _ in pkgutil.iter_modules(api.__path__):
        try:
            importlib.import_module(f"scanner.api.{module_name}")
        except ImportError:
            pass


# =============================================================================
# Main Entry Point
# =============================================================================

def run_action(func: Callable, args: list[str] = []) -> int:
    """Run an action function with defopt argument parsing."""
    wrapped = create_action_wrapper(func)
    return defopt.run(wrapped, argv=args) if args else wrapped()


def main() -> int:
    """Main entry point."""
    global CONFIG

    import_all_categories()
    from .registry import get_actions, get_all_func, get_categories, list_actions

    CONFIG, remaining = parse_global_args(sys.argv[1:])

    if not remaining:
        cats = get_categories()
        print(f"Usage: wekan-scanner --url <URL> <category> <action> [args...]", file=sys.stderr)
        print(f"Categories: {', '.join(sorted(cats)) or 'none'}", file=sys.stderr)
        return 1

    category, *remaining = remaining
    action = remaining[0] if remaining else "all"
    action_args = remaining[1:] if remaining else []

    try:
        # Run all categories
        if category == "all":
            return max((run_action(f) for c in get_categories() if (f := get_all_func(c))), default=0)

        # Validate category
        if category not in get_categories():
            print(f"Unknown category: {category}. Available: {', '.join(sorted(get_categories()))}", file=sys.stderr)
            return 1

        # Run category's "all" action
        if action == "all":
            if func := get_all_func(category):
                return run_action(func)
            print(f"No 'all' action for {category}", file=sys.stderr)
            return 1

        # Run specific action
        actions = get_actions(category)
        if action not in actions:
            print(f"Unknown action: {action}. Available: {', '.join(list_actions(category))}", file=sys.stderr)
            return 1

        return run_action(actions[action], action_args)

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    except Exception as e:
        logfire.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
