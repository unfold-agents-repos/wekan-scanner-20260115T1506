
"""Card Comments API endpoints."""

from typing import TYPE_CHECKING

import logfire
from pydantic import Field

from scanner.models import APIModel
from scanner.utils import compact_dict
from scanner.registry import action, all_action

if TYPE_CHECKING:
    from scanner.client import WekanClient


class BoardResponse(APIModel):
    id: str = Field(alias='_id')


class ListResponse(APIModel):
    id: str = Field(alias='_id')


class CardResponse(APIModel):
    id: str = Field(alias='_id')


class SwimlaneResponse(APIModel):
    id: str = Field(alias='_id')


class CardComment(APIModel):
    """Card Comment model."""
    id: str = Field(alias='_id')
    card_id: str = Field(alias='cardId')
    board_id: str = Field(alias='boardId')
    text: str
    created_at: str = Field(alias='createdAt')
    updated_at: str | None = Field(default=None, alias='updatedAt')
    user_id: str = Field(alias='userId')


@action()
async def get_all_comments(client: 'WekanClient', *, card_id: str) -> list[CardComment]:
    """
    Get all comments for a specific card.

    :param card_id: The ID of the card
    """
    return (await client.get(f'api/cards/{card_id}/comments')).as_list(CardComment, 'comments')


@action()
async def new_comment(
    client: 'WekanClient',
    *,
    card_id: str,
    board_id: str,
    text: str,
    user_id: str
) -> CardComment:
    """
    Add a new comment to a card.

    :param card_id: The ID of the card
    :param board_id: The ID of the board the card belongs to
    :param text: The comment text
    :param user_id: The ID of the user creating the comment
    """
    payload = compact_dict(cardId=card_id, boardId=board_id, text=text, userId=user_id)
    return (await client.post(f'api/cards/{card_id}/comments', json=payload)).as_model(CardComment)


@action()
async def get_comment(client: 'WekanClient', *, card_id: str, comment_id: str) -> CardComment:
    """
    Get a specific comment by ID.

    :param card_id: The ID of the card
    :param comment_id: The ID of the comment
    """
    return (await client.get(f'api/cards/{card_id}/comments/{comment_id}')).as_model(CardComment)


@action()
async def delete_comment(client: 'WekanClient', *, card_id: str, comment_id: str) -> bool:
    """
    Delete a specific comment.

    :param card_id: The ID of the card
    :param comment_id: The ID of the comment to delete
    """
    result = (await client.delete(f'api/cards/{card_id}/comments/{comment_id}')).success()
    if result:
        logfire.info(f'Deleted comment {comment_id} from card {card_id}')
    return result


@all_action
async def all(client: 'WekanClient') -> int:
    """
    Run all card comment tests and clean up created resources.

    Creates test resources, runs all operations, then cleans up.
    """
    test_board_id = None
    test_list_id = None
    test_card_id = None
    test_comment_id = None
    test_user_id = client.config.user_id # Access user_id from client.config

    # API endpoints from documentation start with /api/. Correcting this in calls.

    if not test_user_id:
        logfire.error("✗ Cannot run card comment tests: client.config.user_id is not set. Please provide --user-id to the CLI.")
        return 1

    try:
        logfire.info('Testing card comments API')

        # 1. Create a board
        board_payload = compact_dict(title='Test Board for Comments', color='blue', description='Board for card comment tests')
        board_response = await client.post('api/boards', json=board_payload)
        test_board = board_response.as_model(BoardResponse, 'board', 'data')
        if not test_board:
            logfire.error(f"Failed to create test board. Response: {board_response.response.text}")
            return 1
        test_board_id = test_board.id
        logfire.info(f'✓ Created test board: {test_board_id}')

        # 2. Create a list on the board
        list_payload = compact_dict(title='Test List for Comments', boardId=test_board_id)
        list_response = await client.post('api/lists', json=list_payload)
        test_list = list_response.as_model(ListResponse, 'list', 'data')
        if not test_list:
            logfire.error(f"Failed to create test list. Response: {list_response.response.text}")
            return 1
        test_list_id = test_list.id
        logfire.info(f'✓ Created test list: {test_list_id}')

        # 3. Create a card on the list
        # Get default swimlane, required for card creation
        swimlanes_response = await client.get(f'api/boards/{test_board_id}/swimlanes')
        swimlanes = swimlanes_response.as_list(SwimlaneResponse, 'swimlanes')
        test_swimlane_id = None
        if swimlanes:
            test_swimlane_id = swimlanes[0].id
            logfire.info(f'✓ Found swimlane: {test_swimlane_id}')
        else:
            logfire.error("No swimlanes found for the board. Cannot create card.")
            return 1

        card_payload = compact_dict(
            title='Test Card for Comments',
            boardId=test_board_id,
            listId=test_list_id,
            swimlaneId=test_swimlane_id
        )

        card_response = await client.post('api/cards', json=card_payload)
        test_card = card_response.as_model(CardResponse, 'card', 'data')
        if not test_card:
            logfire.error(f"Failed to create test card. Response: {card_response.response.text}")
            return 1
        test_card_id = test_card.id
        logfire.info(f'✓ Created test card: {test_card_id}')

        # Test new comment
        new_comment_text = "This is a test comment."
        created_comment = await new_comment(
            client,
            card_id=test_card_id,
            board_id=test_board_id,
            text=new_comment_text,
            user_id=test_user_id
        )
        test_comment_id = created_comment.id
        logfire.info(f'✓ Created comment: {created_comment.id} with text: "{created_comment.text}"')

        # Test get comment
        fetched_comment = await get_comment(client, card_id=test_card_id, comment_id=test_comment_id)
        assert fetched_comment.text == new_comment_text
        logfire.info(f'✓ Fetched comment: {fetched_comment.id}')

        # Test get all comments
        all_comments = await get_all_comments(client, card_id=test_card_id)
        assert any(comment.id == test_comment_id for comment in all_comments)
        logfire.info(f'✓ Got {len(all_comments)} comments for card {test_card_id}')

        logfire.info('✓ All card comment tests passed!')
        return 0

    except Exception as e:
        logfire.error(f'✗ Card comment tests failed: {e}')
        return 1

    finally:
        logfire.info('Cleaning up created resources...')
        if test_comment_id and test_card_id:
            try:
                await delete_comment(client, card_id=test_card_id, comment_id=test_comment_id)
                logfire.info(f'✓ Cleaned up test comment: {test_comment_id}')
            except Exception as cleanup_error:
                logfire.warn(f'Failed to cleanup comment {test_comment_id}: {cleanup_error}')
        if test_card_id:
            try:
                # Delete card: API path seems to be /api/cards/{cardId}
                await client.delete(f'api/cards/{test_card_id}', json=compact_dict(boardId=test_board_id, listId=test_list_id)) # Wekan requires boardId and listId for card deletion
                logfire.info(f'✓ Cleaned up test card: {test_card_id}')
            except Exception as cleanup_error:
                logfire.warn(f'Failed to cleanup card {test_card_id}: {cleanup_error}')
        if test_list_id:
            try:
                # Delete list: API path seems to be /api/lists/{listId}
                await client.delete(f'api/lists/{test_list_id}', json=compact_dict(boardId=test_board_id))
                logfire.info(f'✓ Cleaned up test list: {test_list_id}')
            except Exception as cleanup_error:
                logfire.warn(f'Failed to cleanup list {test_list_id}: {cleanup_error}')
        if test_board_id:
            try:
                # Delete board: API path seems to be /api/boards/{boardId}
                await client.delete(f'api/boards/{test_board_id}')
                logfire.info(f'✓ Cleaned up test board: {test_board_id}')
            except Exception as cleanup_error:
                logfire.warn(f'Failed to cleanup board {test_board_id}: {cleanup_error}')
