# scanner/api/checklists.py
"""Checklists API endpoints."""

from typing import TYPE_CHECKING, Any

import logfire
from pydantic import Field

from scanner.models import APIModel
from scanner.utils import compact_dict
from scanner.registry import action, all_action

if TYPE_CHECKING:
    from scanner.client import WekanClient

# --- Models ---
class ChecklistItem(APIModel):
    """Checklist Item model."""
    id: str = Field(alias='_id')
    title: str
    checklist_id: str = Field(alias='checklistId')
    card_id: str = Field(alias='cardId')
    board_id: str = Field(alias='boardId')
    is_finished: bool = Field(alias='isFinished')
    sort: int
    created_at: str | None = Field(default=None, alias='createdAt')
    modified_at: str | None = Field(default=None, alias='modifiedAt')

class Checklist(APIModel):
    """Checklist model."""
    id: str = Field(alias='_id')
    card_id: str = Field(alias='cardId')
    board_id: str = Field(alias='boardId')
    title: str
    finished: bool
    created_at: str | None = Field(default=None, alias='createdAt')
    modified_at: str | None = Field(default=None, alias='modifiedAt')
    sort: int
    checklist_items: list[ChecklistItem] | None = Field(default_factory=list, alias='checklistItems')

# --- Helper Models for all_action (not exposed as actions) ---
class Board(APIModel):
    """Minimal Board model for all_action."""
    id: str = Field(alias='_id')
    title: str

class List(APIModel):
    """Minimal List model for all_action."""
    id: str = Field(alias='_id')
    title: str

class Card(APIModel):
    """Minimal Card model for all_action."""
    id: str = Field(alias='_id')
    title: str
    board_id: str = Field(alias='boardId')
    list_id: str = Field(alias='listId')
    swimlane_id: str = Field(alias='swimlaneId') # swimlaneId is required for new_card, need to fetch it or default to a board's default swimlane.

# --- API Actions for Checklists ---

@action()
async def get_all_checklists(client: 'WekanClient', *, card_id: str) -> list[Checklist]:
    """
    Get all checklists for a specific card.

    :param card_id: The ID of the card.
    """
    return (await client.get(f'api/cards/{card_id}/checklists')).as_list(Checklist)

@action()
async def new_checklist(client: 'WekanClient', *, card_id: str, title: str) -> Checklist:
    """
    Create a new checklist for a specific card.

    :param card_id: The ID of the card.
    :param title: The title of the new checklist.
    """
    payload = compact_dict(title=title)
    return (await client.post(f'api/cards/{card_id}/checklists', json=payload)).as_model(Checklist)

@action()
async def get_checklist(client: 'WekanClient', *, card_id: str, checklist_id: str) -> Checklist:
    """
    Get a specific checklist by ID.

    :param card_id: The ID of the card the checklist belongs to.
    :param checklist_id: The ID of the checklist.
    """
    return (await client.get(f'api/cards/{card_id}/checklists/{checklist_id}')).as_model(Checklist)

@action()
async def delete_checklist(client: 'WekanClient', *, card_id: str, checklist_id: str) -> bool:
    """
    Delete a specific checklist.

    :param card_id: The ID of the card the checklist belongs to.
    :param checklist_id: The ID of the checklist to delete.
    """
    result = (await client.delete(f'api/cards/{card_id}/checklists/{checklist_id}')).success()
    if result:
        logfire.info(f'Deleted checklist {checklist_id} from card {card_id}')
    return result

# --- API Actions for Checklist Items ---

@action()
async def new_checklist_item(
    client: 'WekanClient',
    *,
    card_id: str,
    checklist_id: str,
    title: str
) -> ChecklistItem:
    """
    Create a new item for a specific checklist.

    :param card_id: The ID of the card.
    :param checklist_id: The ID of the checklist.
    :param title: The title of the new checklist item.
    """
    payload = compact_dict(title=title)
    return (await client.post(f'api/cards/{card_id}/checklists/{checklist_id}/items', json=payload)).as_model(ChecklistItem)

@action()
async def get_checklist_item(
    client: 'WekanClient',
    *,
    card_id: str,
    checklist_id: str,
    item_id: str
) -> ChecklistItem:
    """
    Get a specific checklist item by ID.

    :param card_id: The ID of the card.
    :param checklist_id: The ID of the checklist the item belongs to.
    :param item_id: The ID of the checklist item.
    """
    return (await client.get(f'api/cards/{card_id}/checklists/{checklist_id}/items/{item_id}')).as_model(ChecklistItem)

@action()
async def edit_checklist_item(
    client: 'WekanClient',
    *,
    card_id: str,
    checklist_id: str,
    item_id: str,
    title: str,
    is_finished: bool
) -> ChecklistItem:
    """
    Edit a specific checklist item.

    :param card_id: The ID of the card.
    :param checklist_id: The ID of the checklist the item belongs to.
    :param item_id: The ID of the checklist item to edit.
    :param title: The new title for the checklist item.
    :param is_finished: The new finished status for the checklist item.
    """
    payload = compact_dict(title=title, isFinished=is_finished)
    return (await client.put(f'api/cards/{card_id}/checklists/{checklist_id}/items/{item_id}', json=payload)).as_model(ChecklistItem)

@action()
async def delete_checklist_item(
    client: 'WekanClient',
    *,
    card_id: str,
    checklist_id: str,
    item_id: str
) -> bool:
    """
    Delete a specific checklist item.

    :param card_id: The ID of the card.
    :param checklist_id: The ID of the checklist the item belongs to.
    :param item_id: The ID of the checklist item to delete.
    """
    result = (await client.delete(f'api/cards/{card_id}/checklists/{checklist_id}/items/{item_id}')).success()
    if result:
        logfire.info(f'Deleted checklist item {item_id} from checklist {checklist_id} on card {card_id}')
    return result

# --- All Action for testing and cleanup ---

@all_action
async def all(client: 'WekanClient') -> int:
    """
    Run all checklist tests and clean up created resources.

    Creates test resources (board, list, card, checklist, checklist items),
    runs all operations, then cleans up.
    """
    logfire.info('Starting all checklist API tests.')
    test_board: Board | None = None
    test_list: List | None = None
    test_card: Card | None = None
    test_checklist: Checklist | None = None
    test_checklist_item: ChecklistItem | None = None

    try:
        # 1. Create a Board for testing
        logfire.info('Creating a test board...')
        board_payload = compact_dict(title='Test Board for Checklists', perm='private')
        
        # --- DEBUG START ---
        response = await client.post('api/boards', json=board_payload)
        logfire.info(f"DEBUG: Board creation response status: {response.status_code}")
        logfire.info(f"DEBUG: Board creation response text: {response.response.text}")
        test_board = response.as_model(Board, 'board')
        # --- DEBUG END ---
        
        logfire.info(f'✓ Created test board: {test_board.id} - {test_board.title}')

        # 2. Get a default swimlane for the board
        logfire.info('Getting board swimlanes...')
        swimlanes = (await client.get(f'api/boards/{test_board.id}/swimlanes')).as_list(APIModel) # APIModel for generic parsing
        default_swimlane_id = None
        if swimlanes:
            # Assuming the first swimlane is a default one
            default_swimlane_id = swimlanes[0].id
            logfire.info(f'✓ Found default swimlane: {default_swimlane_id}')
        else:
            logfire.error('✗ No swimlanes found for the board. Cannot create card.')
            return 1

        # 3. Create a List on the board
        logfire.info('Creating a test list...')
        list_payload = compact_dict(title='Test List for Checklists', boardId=test_board.id)
        test_list = (await client.post(f'api/boards/{test_board.id}/lists', json=list_payload)).as_model(List, 'list')
        logfire.info(f'✓ Created test list: {test_list.id} - {test_list.title}')

        # 4. Create a Card in the list
        logfire.info('Creating a test card...')
        card_payload = compact_dict(
            title='Test Card for Checklists',
            listId=test_list.id,
            boardId=test_board.id,
            swimlaneId=default_swimlane_id,
            # authorId is needed, but client._config.token is not always the authorId.
            # For simplicity, will try without authorId first, if fails, might need to implement login
            # or fetch current user's ID. Assuming API handles default author for now or doesn't strictly require it on this endpoint.
        )
        test_card = (await client.post(f'api/lists/{test_list.id}/cards', json=card_payload)).as_model(Card, 'card')
        logfire.info(f'✓ Created test card: {test_card.id} - {test_card.title}')

        # --- Checklist Tests ---

        # Test new_checklist
        logfire.info('Testing new_checklist...')
        test_checklist = await new_checklist(client, card_id=test_card.id, title='My Test Checklist')
        logfire.info(f'✓ Created checklist: {test_checklist.id} - {test_checklist.title}')

        # Test get_checklist
        logfire.info('Testing get_checklist...')
        fetched_checklist = await get_checklist(client, card_id=test_card.id, checklist_id=test_checklist.id)
        logfire.info(f'✓ Fetched checklist: {fetched_checklist.id} - {fetched_checklist.title}')
        assert fetched_checklist.id == test_checklist.id

        # Test get_all_checklists
        logfire.info('Testing get_all_checklists...')
        all_checklists = await get_all_checklists(client, card_id=test_card.id)
        logfire.info(f'✓ Found {len(all_checklists)} checklists on card {test_card.id}')
        assert any(c.id == test_checklist.id for c in all_checklists)

        # --- Checklist Item Tests ---

        # Test new_checklist_item
        logfire.info('Testing new_checklist_item...')
        test_checklist_item = await new_checklist_item(
            client,
            card_id=test_card.id,
            checklist_id=test_checklist.id,
            title='First Checklist Item'
        )
        logfire.info(f'✓ Created checklist item: {test_checklist_item.id} - {test_checklist_item.title}')

        # Test get_checklist_item
        logfire.info('Testing get_checklist_item...')
        fetched_item = await get_checklist_item(
            client,
            card_id=test_card.id,
            checklist_id=test_checklist.id,
            item_id=test_checklist_item.id
        )
        logfire.info(f'✓ Fetched checklist item: {fetched_item.id} - {fetched_item.title}')
        assert fetched_item.id == test_checklist_item.id

        # Test edit_checklist_item
        logfire.info('Testing edit_checklist_item...')
        edited_item = await edit_checklist_item(
            client,
            card_id=test_card.id,
            checklist_id=test_checklist.id,
            item_id=test_checklist_item.id,
            title='Updated Checklist Item',
            is_finished=True
        )
        logfire.info(f'✓ Edited checklist item: {edited_item.id} - {edited_item.title}, Finished: {edited_item.is_finished}')
        assert edited_item.title == 'Updated Checklist Item'
        assert edited_item.is_finished is True

        # Test delete_checklist_item
        logfire.info('Testing delete_checklist_item...')
        deleted_item_success = await delete_checklist_item(
            client,
            card_id=test_card.id,
            checklist_id=test_checklist.id,
            item_id=test_checklist_item.id
        )
        logfire.info(f'✓ Deleted checklist item: {deleted_item_success}')
        assert deleted_item_success

        # Verify item is deleted
        try:
            await get_checklist_item(client, card_id=test_card.id, checklist_id=test_checklist.id, item_id=test_checklist_item.id)
            logfire.error('✗ Checklist item was not deleted.')
            return 1
        except Exception as e:
            logfire.info(f'✓ Confirmed checklist item deletion (expected error: {e})')


        # Test delete_checklist
        logfire.info('Testing delete_checklist...')
        deleted_checklist_success = await delete_checklist(client, card_id=test_card.id, checklist_id=test_checklist.id)
        logfire.info(f'✓ Deleted checklist: {deleted_checklist_success}')
        assert deleted_checklist_success

        # Verify checklist is deleted
        try:
            await get_checklist(client, card_id=test_card.id, checklist_id=test_checklist.id)
            logfire.error('✗ Checklist was not deleted.')
            return 1
        except Exception as e:
            logfire.info(f'✓ Confirmed checklist deletion (expected error: {e})')


        logfire.info('All checklist tests passed!')
        return 0

    except Exception as e:
        logfire.error(f'✗ Checklist tests failed: {e}')
        return 1

    finally:
        logfire.info('Starting cleanup of test resources...')
        # Clean up in reverse order of creation
        if test_card:
            try:
                logfire.info(f'Deleting test card {test_card.id}...')
                # The documentation has delete_card under /api/cards/{cardId}, assuming the simple path.
                await client.delete(f'api/cards/{test_card.id}')
                logfire.info(f'✓ Cleaned up test card: {test_card.id}')
            except Exception as cleanup_error:
                logfire.warn(f'Failed to cleanup card {test_card.id}: {cleanup_error}')
        if test_list:
            try:
                logfire.info(f'Deleting test list {test_list.id}...')
                # The documentation has delete_list under /api/lists/{listId}
                await client.delete(f'api/lists/{test_list.id}')
                logfire.info(f'✓ Cleaned up test list: {test_list.id}')
            except Exception as cleanup_error:
                logfire.warn(f'Failed to cleanup list {test_list.id}: {cleanup_error}')
        if test_board:
            try:
                logfire.info(f'Deleting test board {test_board.id}...')
                # The documentation has delete_board under /api/boards/{boardId}
                await client.delete(f'api/boards/{test_board.id}')
                logfire.info(f'✓ Cleaned up test board: {test_board.id}')
            except Exception as cleanup_error:
                logfire.warn(f'Failed to cleanup board {test_board.id}: {cleanup_error}')
        logfire.info('Cleanup complete.')