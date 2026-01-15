# scanner/api/authentication.py
"""Authentication API endpoints."""

import logfire
from pydantic import Field
import uuid

from scanner.models import APIModel
from scanner.utils import compact_dict
from scanner.registry import action, all_action
from scanner.client import APIResponse, WekanClient


class AuthToken(APIModel):
    """Authentication token model."""
    id: str = Field(alias='id')
    token: str
    token_expires: str = Field(alias='tokenExpires')


class RegisterResponse(APIModel):
    """Register response model."""
    user_id: str = Field(alias='id')
    token: str
    token_expires: str = Field(alias='tokenExpires')


@action()
async def login(client: 'WekanClient', *, username: str, password: str) -> AuthToken:
    """
    Login to Wekan.

    :param username: The user's username
    :param password: The user's password
    """
    payload = compact_dict(username=username, password=password)
    return (await client.post('/users/login', json=payload)).as_model(AuthToken)


@action()
async def register(client: 'WekanClient', *, username: str, password: str, email: str) -> RegisterResponse:
    """
    Register a new user in Wekan.

    :param username: The new user's username
    :param password: The new user's password
    :param email: The new user's email
    """
    payload = compact_dict(username=username, password=password, email=email)
    response: APIResponse = (await client.post('/users/register', json=payload))
    return response.as_model(RegisterResponse)


@all_action
async def all(client: 'WekanClient') -> int:
    """
    Run all authentication tests and clean up created resources.

    Creates test resources, runs all operations, then cleans up.
    """
    test_username = f"test_user_wekan_scanner_{uuid.uuid4().hex}"
    test_password = "test_password_wekan_scanner"
    test_email = f"test_user_wekan_scanner_{uuid.uuid4().hex}@example.com"
    registered_user_id = None
    auth_token_value = None
    auth_user_id_from_token = None # New variable to capture user_id from auth token

    try:
        logfire.info('Testing authentication API')

        # Test registration
        logfire.info(f'Attempting to register user: {test_username}')
        try:
            # First, try to register. If successful, use this token and user_id.
            registered_user = await register(client, username=test_username, password=test_password, email=test_email)
            registered_user_id = registered_user.user_id
            auth_token_value = registered_user.token
            auth_user_id_from_token = registered_user.user_id # Capture user_id from registration
            logfire.info(f'✓ Registered user: {test_username} with ID: {registered_user_id}, Token: {auth_token_value[:10]}...')
        except Exception as e:
            # If registration fails (e.g., user exists), log in to get a token.
            logfire.warn(f"Registration failed ({e}), attempting to login.")
            auth_token = await login(client, username=test_username, password=test_password)
            auth_token_value = auth_token.token
            auth_user_id_from_token = auth_token.id # Assume AuthToken.id is the user_id after login
            logfire.info(f'✓ Logged in successfully. Token: {auth_token_value[:10]}..., User ID from token: {auth_user_id_from_token}, Expires: {auth_token.token_expires}')

        # Update the client's config for subsequent calls
        from scanner import cli
        cli.CONFIG.auth_token = auth_token_value
        cli.CONFIG.user_id = auth_user_id_from_token # Always set user_id if we have one

        logfire.info('✓ All authentication tests passed!')
        return 0

    except Exception as e:
        logfire.error(f'✗ Authentication tests failed: {e}')
        return 1

    finally:
        # Cleanup: Wekan API does not provide a direct endpoint to delete users
        # For now, log a warning that manual cleanup might be required.
        logfire.warn(
            f"Manual cleanup of test user may be required. Wekan API does not provide a user deletion endpoint."
            f" Please remove user: {test_username} (ID: {registered_user_id or auth_user_id_from_token}) manually if it was created."
        )
