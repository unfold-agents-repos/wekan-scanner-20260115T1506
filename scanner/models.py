"""
Base models for wekan API responses.

Provides APIModel base class with camelCase alias support.
"""

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """
    Base model for all API responses.

    Features:
    - populate_by_name=True: Allows both camelCase and snake_case field access
    - Use Field(alias='camelCase') for API fields that use camelCase

    Example:
        class User(APIModel):
            user_id: str = Field(alias='userId')
            is_admin: bool = Field(alias='isAdmin')

        # Both work:
        user = User(userId='123', isAdmin=True)
        user = User(user_id='123', is_admin=True)
    """
    model_config = ConfigDict(populate_by_name=True)
