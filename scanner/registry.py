"""
Registry for wekan API actions.

Provides decorators for registering API functions as CLI actions.
Category writers only need to decorate their functions - no CLI code needed.

Usage:
    from scanner.registry import action, all_action

    @action()
    async def list_boards(client, limit: int = 50) -> list[Board]:
        '''List all boards.'''
        ...

    @action("archive")  # Custom action name
    async def archive_board(client, board_id: str) -> Board:
        '''Archive a board.'''
        ...

    @all_action
    async def all(client) -> int:
        '''Run all tests and clean up created resources.'''
        ...
"""

from __future__ import annotations


from typing import TYPE_CHECKING, Callable, TypeVar

if TYPE_CHECKING:
    pass

F = TypeVar('F', bound=Callable)

# Registry: {category_name: {action_name: func}}
_actions: dict[str, dict[str, Callable]] = {}

# All functions: {category_name: func}
_all_funcs: dict[str, Callable] = {}


def action(name: str | None = None):
    """
    Register a function as a CLI action.

    The function will be exposed as a CLI command under its category.
    The first argument must be `client` - it will be injected by the CLI.
    All other arguments become CLI options.

    Args:
        name: Optional custom action name. If not provided, uses the function name
              with the category prefix/suffix removed.
              E.g., `list_boards` in boards.py becomes `list`

    Example:
        @action()
        async def list_boards(client, limit: int = 50) -> list[Board]:
            '''List all boards.'''
            response = await client.request('GET', '/api/boards', params={'limit': limit})
            return [Board(**b) for b in response.json()]

        # CLI: wekan-scanner boards list --limit 100
    """
    def decorator(func: F) -> F:
        # Get category from module name (scanner.api.boards -> boards)
        module = func.__module__
        category = module.split('.')[-1]

        # Determine action name
        if name:
            action_name = name
        else:
            # Auto-derive from function name by removing category prefix/suffix
            func_name = func.__name__
            # Try removing: {category}_, _{category}, {category}
            for pattern in [f'{category}_', f'_{category}']:
                if func_name.startswith(pattern):
                    action_name = func_name[len(pattern):]
                    break
                elif func_name.endswith(pattern):
                    action_name = func_name[:-len(pattern)]
                    break
            else:
                action_name = func_name

        # Register the function
        if category not in _actions:
            _actions[category] = {}
        _actions[category][action_name] = func

        return func
    return decorator


def all_action(func: F) -> F:
    """
    Register a function as the 'all' action for a category.

    This function runs all tests for the category and should:
    1. Create any required test resources
    2. Run all test operations
    3. Clean up created resources (even on failure)

    The function takes only `client` as argument and returns an exit code (0 for success).

    Example:
        @all_action
        async def all(client) -> int:
            '''Run all board tests and clean up.'''
            board = None
            try:
                # Create test resources
                board = await create_board(client, title="Test Board")

                # Run tests
                boards = await list_boards(client)
                logfire.info(f"Found {len(boards)} boards")

                board = await get_board(client, board.id)
                logfire.info(f"Got board: {board.title}")

                return 0
            except Exception as e:
                logfire.error(f"Test failed: {e}")
                return 1
            finally:
                # Always clean up
                if board:
                    try:
                        await delete_board(client, board.id)
                    except Exception:
                        pass

        # CLI: wekan-scanner boards all
    """
    module = func.__module__
    category = module.split('.')[-1]
    _all_funcs[category] = func
    return func


def get_actions(category: str) -> dict[str, Callable]:
    """Get all registered actions for a category."""
    return _actions.get(category, {})


def get_all_func(category: str) -> Callable | None:
    """Get the 'all' function for a category."""
    return _all_funcs.get(category)


def get_categories() -> list[str]:
    """Get all registered categories."""
    # Return unique categories from both registries
    return list(set(_actions.keys()) | set(_all_funcs.keys()))


def list_actions(category: str) -> list[str]:
    """List all available actions for a category."""
    actions = list(get_actions(category).keys())
    if category in _all_funcs:
        actions.insert(0, 'all')
    return actions
