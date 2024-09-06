import asyncio
import pytest
from asyncio import ensure_future
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from app.routing.middleware import token_validator, user_id_extractor
from app.services import ChatService
from app import app
from uuid import uuid4
from domain.enums.chat_enums import PromptType

client = TestClient(app)

@patch("app.services.ChatService", autospec=True)
@patch("app.routing.middleware.token_validator", autospec=True)
@pytest.mark.asyncio
async def test_create_session(mock_token_validator, mock_chat_service):
    """
    Test the /chat/session endpoint.

    Assertions:
    1. Ensure the correct response status code (200).
    2. Ensure the correct session_id is returned in the response.
    3. Ensure the ChatService.create_session method is called with the correct arguments.
    """
    # Mock the create_session method
    mock_chat_service.create_session = AsyncMock(return_value=str(uuid4()))
    
    # Override dependencies
    app.dependency_overrides[ChatService] = lambda: mock_chat_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator
    app.dependency_overrides[user_id_extractor] = lambda: "mock_user_id"

    # Define the request parameters
    prompt_type = PromptType.LESSON

    response = client.get(f"/api/chat/session?type={prompt_type.value}")

    # 1. Assert the status code
    assert response.status_code == 200

    # 2. Assert the correct response structure
    assert "session_id" in response.json()

    # 3. Assert that the service method was called with the correct arguments
    mock_chat_service.create_session.assert_awaited_once_with(
        user_id="mock_user_id", 
        prompt_type=prompt_type,
        resource_id=None
    )

@patch("app.services.ChatService", autospec=True)
@patch("app.routing.middleware.token_validator", autospec=True)
@pytest.mark.asyncio
@pytest.mark.skip("Need to figure out how to properly test the StreamingResponse")
async def test_send_message(mock_token_validator, mock_chat_service):
    """
    Test the /chat/{session_id} endpoint (message stream).

    Assertions:
    1. Ensure the correct response status code (200).
    2. Ensure the response is a StreamingResponse.
    3. Ensure the ChatService.get_response method is called with the correct arguments.
    4. Ensure the response stream contains the expected messages.
    """

    # Override dependencies
    app.dependency_overrides[ChatService] = lambda: mock_chat_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator
    app.dependency_overrides[user_id_extractor] = lambda: "mock_user_id"
    
    async def mock_stream():
        for i in range(3):
            yield f"message {i}\n\n"
            await asyncio.sleep(0.01)
            
    mock_chat_service.get_response = AsyncMock(side_effect=mock_stream)

    # Define the request parameters
    session_id = uuid4()
    payload = {
        "message": "Hello!"
    }

    # Send the request
    response = client.post(f"/api/chat/{session_id}", json=payload)

    # 1. Assert the status code
    assert response.status_code == 200

    # 2. Assert that the response is a StreamingResponse
    assert response.headers["content-type"] == "text/event-stream"

    # 3. Assert the service method was called with the correct arguments
    mock_chat_service.get_response.assert_called_once_with(
        user_id="mock_user_id",
        session_id=session_id,
        message="Hello!"
    )

    # 4. Check the stream data (consume the stream)
    content = ""
    for chunk in response.iter_content():
        content += chunk.decode()

    assert "message 0" in content
    assert "message 1" in content
    assert "message 2" in content

@patch("app.services.ChatService", autospec=True)
@patch("app.routing.middleware.token_validator", autospec=True)
@pytest.mark.asyncio
async def test_get_chat_history(mock_token_validator, mock_chat_service):
    """
    Test the /chat/{session_id}/history endpoint.

    Assertions:
    1. Ensure the correct response status code (200).
    2. Ensure the correct chat history is returned in the response.
    3. Ensure the ChatService.get_history method is called with the correct arguments.
    """
    # Mock the get_history method
    mock_chat_service.get_history = AsyncMock(return_value=[{"message": "Hello!"}, {"message": "Hi!"}])

    # Override dependencies
    app.dependency_overrides[ChatService] = lambda: mock_chat_service
    app.dependency_overrides[token_validator] = lambda: mock_token_validator
    app.dependency_overrides[user_id_extractor] = lambda: "mock_user_id"

    # Define the request parameters
    session_id = uuid4()

    response = client.get(f"/api/chat/{session_id}/history")

    # 1. Assert the status code
    assert response.status_code == 200

    # 2. Assert the correct response structure
    assert response.json() == [{"message": "Hello!"}, {"message": "Hi!"}]

    # 3. Assert that the service method was called with the correct arguments
    mock_chat_service.get_history.assert_awaited_once_with(
        user_id="mock_user_id",
        session_id=session_id
    )
