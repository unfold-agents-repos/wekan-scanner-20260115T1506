"""
Utility functions for wekan scanner.

Provides helpers for common API patterns.
"""

from typing import Any


def compact_dict(**kwargs: Any) -> dict[str, Any]:
    """
    Build a dictionary excluding None values.

    Useful for building API params/payloads where None means "omit field".

    Example:
        # Instead of:
        params: dict[str, Any] = {}
        if team_id:
            params['teamId'] = team_id
        if team_name:
            params['teamName'] = team_name

        # Use:
        params = compact_dict(teamId=team_id, teamName=team_name)

    Args:
        **kwargs: Key-value pairs to include (None values are excluded)

    Returns:
        Dict with only non-None values
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def require_one_of(**kwargs: Any) -> dict[str, Any]:
    """
    Build a compact dict, but raise ValueError if all values are None.

    Useful for API endpoints that require at least one identifier.

    Example:
        params = require_one_of(teamId=team_id, teamName=team_name)
        # Raises ValueError if both are None

    Args:
        **kwargs: Key-value pairs (at least one must be non-None)

    Returns:
        Dict with only non-None values

    Raises:
        ValueError: If all values are None
    """
    result = compact_dict(**kwargs)
    if not result:
        keys = ', '.join(kwargs.keys())
        raise ValueError(f"At least one of ({keys}) must be provided")
    return result
