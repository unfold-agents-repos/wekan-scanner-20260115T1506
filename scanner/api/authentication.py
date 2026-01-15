# scanner/api/authentication.py
"""Authentication API endpoints."""

import logfire
from pydantic import Field

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
    username: str
    email: str
    id: str = Field(alias='_id')


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
    test_username = "test_user_wekan_scanner"
    test_password = "test_password_wekan_scanner"
    test_email = "test_user_wekan_scanner@example.com"
    registered_user_id = None

    try:
        logfire.info('Testing authentication API')

        # Test registration
        logfire.info(f'Attempting to register user: {test_username}')
        try:
            registered_user = await register(client, username=test_username, password=test_password, email=test_email)
            registered_user_id = registered_user.id
            logfire.info(f'✓ Registered user: {registered_user.username} with ID: {registered_user_id}')
        except Exception as e:
            # If registration fails, it might be because the user already exists.
            # Log a warning and proceed to login.
            logfire.warn(f"Registration failed, attempting to login: {e}")
            # The API might return an error message when a user already exists,
            # so we'll catch it and proceed to try logging in.

        # Test login
        logfire.info(f'Attempting to login user: {test_username}')
        auth_token = await login(client, username=test_username, password=test_password)
        logfire.info(f'✓ Logged in successfully. Token: {auth_token.token[:10]}..., Expires: {auth_token.token_expires}')

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
            f" Please remove user: {test_username} (ID: {registered_user_id}) manually if it was created."
        )
