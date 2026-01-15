
"""Boards API endpoints."""

from typing import TYPE_CHECKING, Any
import logfire
from pydantic import Field

from scanner.models import APIModel
from scanner.utils import compact_dict
from scanner.registry import action, all_action

if TYPE_CHECKING:
    from scanner.client import WekanClient

class Board(APIModel):
    """Board model."""
    id: str = Field(alias='_id')
    title: str | None = None
    slug: str | None = None
    archived: bool | None = None
    created_at: str | None = Field(default=None, alias='createdAt')
    modified_at: str | None = Field(default=None, alias='modifiedAt')
    members: list[dict[str, Any]] | None = None
    labels: list[dict[str, Any]] | None = None
    permission: str | None = None
    sort: int | None = None
    color: str | None = None
    subtasks_by_card: str | None = Field(default=None, alias='subtasksByCard')
    date_settings: dict[str, Any] | None = Field(default=None, alias='dateSettings')
    _template_board_id: str | None = Field(default=None, alias='_templateBoardId')

class BoardAttachment(APIModel):
    """Board attachment model."""
    id: str = Field(alias='_id')
    name: str | None = None
    url: str | None = None
    content_type: str | None = Field(default=None, alias='contentType')
    created_at: str | None = Field(default=None, alias='createdAt')
    user_id: str | None = Field(default=None, alias='userId')

class BoardLabel(APIModel):
    """Board label model."""
    id: str = Field(alias='_id')
    name: str | None = None
    color: str | None = None

class BoardMember(APIModel):
    """Board member model."""
    id: str = Field(alias='_id')
    user_id: str | None = Field(default=None, alias='userId')
    is_admin: bool | None = Field(default=None, alias='isAdmin')
    is_active: bool | None = Field(default=None, alias='isActive')
    is_no_comments: bool | None = Field(default=None, alias='isNoComments')
    is_comment_only: bool | None = Field(default=None, alias='isCommentOnly')
    is_worker: bool | None = Field(default=None, alias='isWorker')
    is_manager: bool | None = Field(default=None, alias='isManager')

@action()
async def get_public_boards(client: 'WekanClient') -> list[Board]:
    """
    Get all public boards.
    """
    return (await client.get('api/boards')).as_list(Board, 'boards')

@action()
async def new_board(
    client: 'WekanClient',
    *,
    title: str,
    permission: str = 'public',
    color: str = 'belize'
) -> Board:
    """
    Create a new board.

    :param title: Board title.
    :param permission: Board permission (e.g., 'public', 'private').
    :param color: Board color.
    """
    payload = compact_dict(title=title, permission=permission, color=color)
    return (await client.post('api/boards', json=payload)).as_model(Board, 'board')

@action()
async def get_board(client: 'WekanClient', *, board_id: str) -> Board:
    """
    Get a specific board by ID.

    :param board_id: The ID of the board.
    """
    return (await client.get(f'api/boards/{board_id}')).as_model(Board, 'board')

@action()
async def delete_board(client: 'WekanClient', *, board_id: str) -> bool:
    """
    Delete a board by ID.

    :param board_id: The ID of the board to delete.
    """
    result = (await client.delete(f'api/boards/{board_id}')).success()
    if result:
        logfire.info(f'Deleted board {board_id}')
    else:
        logfire.error(f'Failed to delete board {board_id}')
    return result

@action()
async def get_board_attachments(client: 'WekanClient', *, board_id: str) -> list[BoardAttachment]:
    """
    Get attachments for a specific board.

    :param board_id: The ID of the board.
    """
    return (await client.get(f'api/boards/{board_id}/attachments')).as_list(BoardAttachment, 'attachments')

@action()
async def export_board_json(client: 'WekanClient', *, board_id: str) -> dict[str, Any]:
    """
    Export a board as JSON.

    :param board_id: The ID of the board.
    """
    return (await client.get(f'api/boards/{board_id}/export.json')).json

@action()
async def copy_board(
    client: 'WekanClient',
    *,
    board_id: str,
    title: str,
    from_board: str = 'copyBoard'
) -> Board:
    """
    Copy a board.

    :param board_id: The ID of the board to copy.
    :param title: The title for the new board.
    :param from_board: Source board option (e.g., 'copyBoard').
    """
    payload = compact_dict(title=title, fromBoard=from_board)
    return (await client.post(f'api/boards/{board_id}/copy', json=payload)).as_model(Board, 'board')

@action()
async def add_board_label(
    client: 'WekanClient',
    *,
    board_id: str,
    name: str,
    color: str
) -> BoardLabel:
    """
    Add a label to a board.

    :param board_id: The ID of the board.
    :param name: The name of the label.
    :param color: The color of the label.
    """
    payload = compact_dict(name=name, color=color)
    return (await client.post(f'api/boards/{board_id}/labels', json=payload)).as_model(BoardLabel, 'label')

@action()
async def set_board_member_permission(
    client: 'WekanClient',
    *,
    board_id: str,
    member_id: str,
    permission: str
) -> BoardMember:
    """
    Set a member's permission on a board.

    :param board_id: The ID of the board.
    :param member_id: The ID of the member.
    :param permission: The new permission level (e.g., 'normal', 'admin').
    """
    payload = compact_dict(permission=permission)
    return (await client.post(f'api/boards/{board_id}/members/{member_id}/permission', json=payload)).as_model(BoardMember, 'member')

@action()
async def update_board_title(
    client: 'WekanClient',
    *,
    board_id: str,
    title: str
) -> Board:
    """
    Update the title of a board.

    :param board_id: The ID of the board.
    :param title: The new title for the board.
    """
    payload = compact_dict(title=title)
    return (await client.put(f'api/boards/{board_id}/title', json=payload)).as_model(Board, 'board')

@action()
async def get_boards_count(client: 'WekanClient') -> int:
    """
    Get the total count of boards.
    """
    response = await client.get('api/boards/count')
    return response.json().get('count', 0)

@action()
async def get_boards_from_user(client: 'WekanClient', *, user_id: str) -> list[Board]:
    """
    Get all boards for a specific user.

    :param user_id: The ID of the user.
    """
    return (await client.get(f'api/users/{user_id}/boards')).as_list(Board, 'boards')


@all_action
async def all(client: 'WekanClient') -> int:
    """
    Run all board tests and clean up created resources.

    Creates test resources, runs all operations, then cleans up.
    """
    created_board = None
    copied_board = None
    test_user_id = "test_user_id" # Placeholder for testing get_boards_from_user if a user_id is needed

    try:
        logfire.info('Testing boards API')

        # Test get_public_boards
        boards = await get_public_boards(client)
        logfire.info(f'✓ Listed {len(boards)} public boards')

        # Test new_board
        created_board = await new_board(client, title='Test Board (cleanup)')
        logfire.info(f'✓ Created board: {created_board.id} with title "{created_board.title}"')

        # Test get_board
        board = await get_board(client, board_id=created_board.id)
        logfire.info(f'✓ Got board: {board.title}')

        # Test copy_board
        copied_board = await copy_board(client, board_id=created_board.id, title='Copied Test Board (cleanup)')
        logfire.info(f'✓ Copied board: {copied_board.id} with title "{copied_board.title}"')

        # Test update_board_title
        await update_board_title(client, board_id=created_board.id, title='Updated Test Board (cleanup)')
        updated_board = await get_board(client, board_id=created_board.id)
        logfire.info(f'✓ Updated board title to: "{updated_board.title}"')

        # Test add_board_label
        label = await add_board_label(client, board_id=created_board.id, name='Test Label', color='green')
        logfire.info(f'✓ Added label: {label.name} with color {label.color}')

        # Test get_boards_count
        boards_count = await get_boards_count(client)
        logfire.info(f'✓ Total boards count: {boards_count}')

        # Test get_board_attachments (assuming no attachments initially)
        attachments = await get_board_attachments(client, board_id=created_board.id)
        logfire.info(f'✓ Retrieved {len(attachments)} attachments for board {created_board.id}')

        # Test export_board_json
        exported_json = await export_board_json(client, board_id=created_board.id)
        logfire.info(f'✓ Exported board JSON for {created_board.id} (keys: {list(exported_json.keys())})')

        # Test set_board_member_permission - requires a valid member ID, skipping for now as it's not straightforward to create a member in a self-contained test
        logfire.warn("Skipping set_board_member_permission test as it requires a valid member ID.")

        # Test get_boards_from_user - requires a valid user ID, skipping for now
        logfire.warn("Skipping get_boards_from_user test as it requires a valid user ID.")


        logfire.info('✓ All board tests passed!')
        return 0

    except Exception as e:
        logfire.error(f'✗ Board tests failed: {e}')
        return 1

    finally:
        # ALWAYS clean up, even on failure
        if created_board:
            try:
                await delete_board(client, board_id=created_board.id)
                logfire.info(f'✓ Cleaned up primary test board: {created_board.id}')
            except Exception as cleanup_error:
                logfire.warn(f'Failed to cleanup primary test board {created_board.id}: {cleanup_error}')
        if copied_board:
            try:
                await delete_board(client, board_id=copied_board.id)
                logfire.info(f'✓ Cleaned up copied test board: {copied_board.id}')
            except Exception as cleanup_error:
                logfire.warn(f'Failed to cleanup copied test board {copied_board.id}: {cleanup_error}')
