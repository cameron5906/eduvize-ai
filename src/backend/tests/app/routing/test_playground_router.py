import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app import app
from app.routing.middleware import user_id_extractor
from app.services import PlaygroundService

client = TestClient(app)

@patch("app.routing.playground_router.user_id_extractor", autospec=True)
@patch("app.services.PlaygroundService", autospec=True)
@pytest.mark.asyncio
async def test_create_playground_instance(mock_playground_service, mock_user_id_extractor):
    """
    Tests the /playground/ endpoint:
    1. Status code is 200
    2. Response contains the correct session_id and token
    3. PlaygroundService.create_playground is called with the correct user_id
    """
    # Mock the user_id extractor to return a specific user ID
    mock_user_id_extractor.return_value = "user123"

    # Mock the create_playground method of PlaygroundService
    mock_playground_service_instance = mock_playground_service.return_value
    mock_playground_service_instance.create_playground = AsyncMock(return_value=("session_abc123", "token_xyz456"))

    # Override dependencies
    app.dependency_overrides[user_id_extractor] = mock_user_id_extractor
    app.dependency_overrides[PlaygroundService] = lambda: mock_playground_service_instance

    # Call the endpoint
    response = client.post("/api/playground/")

    # Assertions
    assert response.status_code == 200
    assert response.json() == {
        "session_id": "session_abc123",
        "token": "token_xyz456"
    }

    # Assert that create_playground was called with the correct user_id
    mock_playground_service_instance.create_playground.assert_awaited_once_with("user123")
