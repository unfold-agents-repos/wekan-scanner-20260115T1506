"""Custom Fields API endpoints."""

from typing import TYPE_CHECKING

import logfire
from pydantic import Field

from scanner.models import APIModel
from scanner.utils import compact_dict
from scanner.registry import action, all_action

# Import the client for TYPE_CHECKING and WekanClientConfig
from scanner.client import WekanClientConfig, WekanClient

if TYPE_CHECKING:
    from scanner.api.authentication import AuthToken # For login response


class CustomFieldDropdownItem(APIModel):
    """Custom field dropdown item model."""
    id: str = Field(alias='_id')
    name: str
    color: str | None = None


class CustomFieldSettings(APIModel):
    """Custom field settings model."""
    type: str
    dropdown_items: list[CustomFieldDropdownItem] = Field(default_factory=list, alias='dropdownItems')
    min: float | None = None
    max: float | None = None
    decimal_places: int | None = Field(default=None, alias='decimalPlaces')
    unit: str | None = None
    default: str | None = None
    show_on_card: bool | None = Field(default=None, alias='showOnCard')
    show_label_on_mini_card: bool | None = Field(default=None, alias='showLabelOnMiniCard')
    always_show: bool | None = Field(default=None, alias='alwaysShow')
    show_sum: bool | None = Field(default=None, alias='showSum')


class CustomField(APIModel):
    """Custom field model."""
    id: str = Field(alias='_id')
    board_ids: list[str] = Field(default_factory=list, alias='boardIds')
    name: str
    type: str
    settings: CustomFieldSettings
    created_at: str | None = Field(default=None, alias='createdAt')
    updated_at: str | None = Field(default=None, alias='updatedAt')
    modified_at: str | None = Field(default=None, alias='modifiedAt')
    is_active: bool | None = Field(default=None, alias='isActive')
    is_collapsed: bool | None = Field(default=None, alias='isCollapsed')
    is_multi_select: bool | None = Field(default=None, alias='isMultiSelect')


@action()
async def get_all_custom_fields(client: 'WekanClient') -> list[CustomField]:
    """
    Get all custom fields.
    """
    return (await client.get('api/custom-fields')).as_list(CustomField, key='customFields')


@action()
async def new_custom_field(
    client: 'WekanClient',
    *,
    board_id: str,
    name: str,
    type: str,
    settings: CustomFieldSettings
) -> CustomField:
    """
    Create a new custom field.

    :param board_id: The ID of the board to associate the custom field with.
    :param name: The name of the custom field.
    :param type: The type of the custom field (e.g., 'text', 'number', 'dropdown').
    :param settings: Custom field settings.
    """
    payload = {
        'boardId': board_id,
        'name': name,
        'type': type,
        'settings': settings.model_dump(by_alias=True, exclude_unset=True)
    }
    return (await client.post('api/custom-fields', json=payload)).as_model(CustomField)


@action()
async def get_custom_field(client: 'WekanClient', *, custom_field_id: str) -> CustomField:
    """
    Get a specific custom field by ID.

    :param custom_field_id: The ID of the custom field.
    """
    return (await client.get(f'api/custom-fields/{custom_field_id}')).as_model(CustomField)


@action()
async def edit_custom_field(
    client: 'WekanClient',
    *,
    custom_field_id: str,
    name: str | None = None,
    type: str | None = None,
    settings: CustomFieldSettings | None = None
) -> CustomField:
    """
    Edit an existing custom field.

    :param custom_field_id: The ID of the custom field to edit.
    :param name: The new name of the custom field.
    :param type: The new type of the custom field.
    :param settings: New custom field settings.
    """
    payload = compact_dict(
        name=name,
        type=type,
        settings=settings.model_dump(by_alias=True, exclude_unset=True) if settings else None
    )
    return (await client.put(f'api/custom-fields/{custom_field_id}', json=payload)).as_model(CustomField)


@action()
async def delete_custom_field(client: 'WekanClient', *, custom_field_id: str) -> bool:
    """
    Delete a custom field.

    :param custom_field_id: The ID of the custom field to delete.
    """
    result = (await client.delete(f'api/custom-fields/{custom_field_id}')).success()
    if result:
        logfire.info(f'Deleted custom field {custom_field_id}')
    return result


@action()
async def add_custom_field_dropdown_items(
    client: 'WekanClient',
    *,
    custom_field_id: str,
    name: str,
    color: str | None = None
) -> CustomFieldDropdownItem:
    """
    Add dropdown items to a custom field.

    :param custom_field_id: The ID of the custom field.
    :param name: The name of the dropdown item.
    :param color: The color of the dropdown item.
    """
    payload = compact_dict(name=name, color=color)
    return (await client.post(
        f'api/custom-fields/{custom_field_id}/dropdown-items',
        json=payload
    )).as_model(CustomFieldDropdownItem)


@action()
async def edit_custom_field_dropdown_item(
    client: 'WekanClient',
    *,
    custom_field_id: str,
    dropdown_item_id: str,
    name: str | None = None,
    color: str | None = None
) -> CustomFieldDropdownItem:
    """
    Edit a custom field dropdown item.

    :param custom_field_id: The ID of the custom field.
    :param dropdown_item_id: The ID of the dropdown item to edit.
    :param name: The new name of the dropdown item.
    :param color: The new color of the dropdown item.
    """
    payload = compact_dict(name=name, color=color)
    return (await client.put(
        f'api/custom-fields/{custom_field_id}/dropdown-items/{dropdown_item_id}',
        json=payload
    )).as_model(CustomFieldDropdownItem)


@action()
async def delete_custom_field_dropdown_item(
    client: 'WekanClient',
    *,
    custom_field_id: str,
    dropdown_item_id: str
) -> bool:
    """
    Delete a custom field dropdown item.

    :param custom_field_id: The ID of the custom field.
    :param dropdown_item_id: The ID of the dropdown item to delete.
    """
    result = (await client.delete(
        f'api/custom-fields/{custom_field_id}/dropdown-items/{dropdown_item_id}'
    )).success()
    if result:
        logfire.info(f'Deleted dropdown item {dropdown_item_id} from custom field {custom_field_id}')
    return result


@all_action
async def all(client: 'WekanClient') -> int:
    """
    Run all custom field tests and clean up created resources.

    Creates test resources, runs all operations, then cleans up.
    """
    logfire.info('Testing custom fields API')

    # Temporary variables to store created resource IDs for cleanup
    created_custom_field = None
    created_dropdown_item = None
    created_board = None
    auth_token_obj: AuthToken | None = None
    authenticated_client = None

    try:
        # 1. Login to get an authenticated client
        from scanner.api.authentication import login, register

        test_username = "test_user_for_custom_fields"
        test_password = "test_password_for_custom_fields"
        test_email = "test_user_custom_fields@example.com"

        logfire.info(f"Attempting to login as {test_username}")
        try:
            auth_token_obj = await login(client, username=test_username, password=test_password)
            logfire.info(f"Logged in as {test_username}")
        except Exception as e:
            logfire.warn(f"Login failed, attempting to register and then login: {e}")
            try:
                await register(client, username=test_username, password=test_password, email=test_email)
                auth_token_obj = await login(client, username=test_username, password=test_password)
                logfire.info(f"Registered and logged in as {test_username}")
            except Exception as reg_e:
                logfire.error(f"Registration and login failed: {reg_e}")
                return 1 # Cannot proceed without authentication

        if not auth_token_obj:
            logfire.error("Failed to obtain authentication token. Exiting.")
            return 1

        logfire.debug(f"Obtained token: {auth_token_obj.token}, User ID: {auth_token_obj.id}")

        # Create a new authenticated client for subsequent operations
        auth_config = WekanClientConfig(
            base_url=client.config.base_url,
            verify_ssl=client.config.verify_ssl,
            auth_token=auth_token_obj.token,
            user_id=auth_token_obj.id,
            timeout=client.config.timeout
        )
        authenticated_client = WekanClient(auth_config)
        await authenticated_client.__aenter__() # Manually enter the context

        # 2. Create a board first, as custom fields are associated with boards.
        class Board(APIModel):
            id: str = Field(alias='_id')
            title: str
            slug: str | None = None
            created_at: str | None = Field(default=None, alias='createdAt')

        async def create_temp_board(cli: 'WekanClient', title: str) -> Board:
            payload = {'title': title}
            return (await cli.post('api/boards', json=payload)).as_model(Board, 'board')

        async def delete_temp_board(cli: 'WekanClient', board_id: str) -> bool:
            return (await cli.delete(f'api/boards/{board_id}')).success()

        created_board = await create_temp_board(authenticated_client, title='Test Board for Custom Fields')
        test_board_id = created_board.id
        logfire.info(f"Created temporary board: {test_board_id}")

        # Test new_custom_field
        settings = CustomFieldSettings(type='text')
        created_custom_field = await new_custom_field(
            authenticated_client, board_id=test_board_id, name='Test Custom Field', type='text', settings=settings
        )
        logfire.info(f'✓ Created custom field: {created_custom_field.id}')

        # Test get_all_custom_fields
        all_custom_fields = await get_all_custom_fields(authenticated_client)
        assert any(cf.id == created_custom_field.id for cf in all_custom_fields)
        logfire.info(f'✓ Listed {len(all_custom_fields)} custom fields, found created one.')

        # Test get_custom_field
        fetched_custom_field = await get_custom_field(authenticated_client, custom_field_id=created_custom_field.id)
        assert fetched_custom_field.id == created_custom_field.id
        logfire.info(f'✓ Got custom field: {fetched_custom_field.name}')

        # Test edit_custom_field
        settings_payload = compact_dict(
            type='number',
            min=0.0,
            max=100.0,
            decimal_places=2
        )
        edited_settings = CustomFieldSettings(**settings_payload)
        edited_custom_field = await edit_custom_field(
            authenticated_client,
            custom_field_id=created_custom_field.id,
            name='Edited Custom Field',
            type='number',
            settings=edited_settings
        )
        assert edited_custom_field.name == 'Edited Custom Field'
        assert edited_custom_field.settings.type == 'number'
        assert edited_custom_field.settings.min == 0.0
        assert edited_custom_field.settings.max == 100.0
        assert edited_custom_field.settings.decimal_places == 2
        logfire.info(f'✓ Edited custom field: {edited_custom_field.name}')

        # Test add_custom_field_dropdown_items (requires editing custom field type to dropdown first)
        dropdown_settings = CustomFieldSettings(type='dropdown')
        await edit_custom_field(
            authenticated_client,
            custom_field_id=created_custom_field.id,
            type='dropdown',
            settings=dropdown_settings
        )
        created_dropdown_item = await add_custom_field_dropdown_items(
            authenticated_client, custom_field_id=created_custom_field.id, name='Dropdown Item 1', color='green'
        )
        logfire.info(f'✓ Added dropdown item: {created_dropdown_item.name}')

        # Test edit_custom_field_dropdown_item
        edited_dropdown_item = await edit_custom_field_dropdown_item(
            authenticated_client,
            custom_field_id=created_custom_field.id,
            dropdown_item_id=created_dropdown_item.id,
            name='Edited Dropdown Item',
            color='blue'
        )
        assert edited_dropdown_item.name == 'Edited Dropdown Item'
        assert edited_dropdown_item.color == 'blue'
        logfire.info(f'✓ Edited dropdown item: {edited_dropdown_item.name}')

        # Test delete_custom_field_dropdown_item
        deleted_dropdown = await delete_custom_field_dropdown_item(
            authenticated_client,
            custom_field_id=created_custom_field.id,
            dropdown_item_id=created_dropdown_item.id
        )
        assert deleted_dropdown is True
        logfire.info(f'✓ Deleted dropdown item: {created_dropdown_item.id}')

        logfire.info('✓ All custom field tests passed!')
        return 0

    except Exception as e:
        logfire.error(f'✗ Custom field tests failed: {e}')
        return 1

    finally:
        # ALWAYS clean up, even on failure
        if authenticated_client:
            await authenticated_client.__aexit__(None, None, None) # Manually exit the context

        if created_custom_field:
            try:
                # Use the authenticated client for cleanup
                if authenticated_client:
                    await delete_custom_field(authenticated_client, custom_field_id=created_custom_field.id)
                    logfire.info(f'✓ Cleaned up test custom field: {created_custom_field.id}')
            except Exception as cleanup_error:
                logfire.warn(f'Failed to cleanup custom field {created_custom_field.id}: {cleanup_error}')
        if created_board:
            try:
                # Use the authenticated client for cleanup
                if authenticated_client:
                    await delete_temp_board(authenticated_client, board_id=created_board.id)
                    logfire.info(f'✓ Cleaned up temporary board: {created_board.id}')
            except Exception as cleanup_error:
                logfire.warn(f'Failed to cleanup temporary board {created_board.id}: {cleanup_error}')
        # User cleanup is not provided by Wekan API, log a warning
        if auth_token_obj:
            logfire.warn(
                f"Manual cleanup of test user '{test_username}' (ID: {auth_token_obj.id}) "
                f"may be required. Wekan API does not provide a user deletion endpoint."
            )
