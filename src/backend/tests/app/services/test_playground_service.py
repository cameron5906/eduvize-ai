import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.playground_service import PlaygroundService

# Sample data
user_id = "user123"
session_id = "session123"
token = "mocked_jwt_token"

@pytest.fixture
def playground_service():
    playground_repo = MagicMock()
    return PlaygroundService(playground_repo=playground_repo)

@pytest.mark.asyncio
@patch("app.services.playground_service.create_token", autospec=True)
@patch("app.services.playground_service.get_playground_token_secret", autospec=True)
async def test_create_playground(mock_get_playground_token_secret, mock_create_token, playground_service):
    """
    Test create_playground method:
    1. Should create a new playground session.
    2. Should generate a JWT token with the session ID and user ID.
    3. Should return the session ID and token.
    """
    # Mock repository method
    playground_service.playground_repo.create_playground_session = AsyncMock(return_value=session_id)
    
    # Mock the external function to get the token secret
    mock_get_playground_token_secret.return_value = "mocked_secret"
    
    # Mock JWT token creation
    mock_create_token.return_value = token
    
    result = await playground_service.create_playground(user_id=user_id)
    
    # Assertions
    playground_service.playground_repo.create_playground_session.assert_awaited_once_with("basic")
    mock_get_playground_token_secret.assert_called_once()
    mock_create_token.assert_called_once_with(
        data={"session_id": session_id, "user_id": user_id},
        secret="mocked_secret",
        expiration_minutes=5
    )
    
    assert result == (session_id, token)
