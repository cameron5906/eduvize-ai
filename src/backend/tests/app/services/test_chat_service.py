import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import uuid
from app.services.chat_service import ChatService
from domain.schema.chat.chat_message import ChatMessage
from domain.dto.ai.completion_chunk import CompletionChunk
from domain.dto.chat.chat_message import ChatMessageDto
from domain.enums.chat_enums import PromptType
from ai.common.base_message import BaseChatMessage, ChatRole

# Test data
user_id = "user123"
session_id = uuid.uuid4()
resource_id = uuid.uuid4()
prompt_type = PromptType.LESSON
message = "This is a test message."
mock_lesson = MagicMock()

@pytest.fixture
def chat_service():
    user_service = MagicMock()
    chat_repository = MagicMock()
    course_repository = MagicMock()
    return ChatService(user_service=user_service, chat_repository=chat_repository, course_repository=course_repository)

@pytest.mark.asyncio
async def test_create_session(chat_service):
    """
    Test creating a chat session
    1. Should call user_service.get_user to validate the user.
    2. Should call chat_repository.create_chat_session and return session ID.
    """
    mock_session = MagicMock(id=session_id)
    
    # Mock the user service and repository methods
    chat_service.user_service.get_user = AsyncMock(return_value=MagicMock(id=user_id))
    chat_service.chat_repository.create_chat_session = MagicMock(return_value=mock_session)
    
    result = await chat_service.create_session(user_id=user_id, prompt_type=prompt_type, resource_id=resource_id)
    
    chat_service.user_service.get_user.assert_awaited_once_with("id", user_id)
    chat_service.chat_repository.create_chat_session.assert_called_once_with(
        user_id=user_id,
        prompt_type=prompt_type.value,
        resource_id=resource_id
    )
    
    assert result == session_id

@pytest.mark.asyncio
async def test_get_history(chat_service):
    """
    Test retrieving chat history for a session.
    1. Should call user_service.get_user to validate the user.
    2. Should return the chat message history as ChatMessageDto list.
    """
    mock_messages = [MagicMock(spec=ChatMessage, content="Hello", is_user=True, session_id=session_id, id=uuid.uuid4())]
    
    chat_service.user_service.get_user = AsyncMock(return_value=MagicMock(id=user_id))
    chat_service.chat_repository.get_chat_messages = MagicMock(return_value=mock_messages)
    
    result = await chat_service.get_history(user_id=user_id, session_id=session_id)
    
    chat_service.user_service.get_user.assert_awaited_once_with("id", user_id)
    chat_service.chat_repository.get_chat_messages.assert_called_once_with(session_id)
    
    assert len(result) == len(mock_messages)
    assert isinstance(result[0], ChatMessageDto)

@pytest.mark.asyncio
@patch("app.services.chat_service.ChatService.get_prompt_generator")
async def test_get_response(mock_get_prompt_generator, chat_service):
    """
    Test getting chat response from AI.
    1. Should call user_service.get_user to validate the user.
    2. Should iterate over the response generator and yield CompletionChunks.
    3. Should add both user and AI messages to the chat repository.
    """
    mock_generator = MagicMock()
    mock_generator.__next__.side_effect = [
        CompletionChunk(message_id="message_id", text="chunk1"), 
        StopIteration([BaseChatMessage(role=ChatRole.AGENT, message="AI response")])
    ]
    mock_get_prompt_generator.return_value = mock_generator

    chat_service.user_service.get_user = AsyncMock(return_value=MagicMock(id=user_id))
    chat_service.chat_repository.get_session = MagicMock(return_value=MagicMock(id=session_id))
    
    response = [chunk async for chunk in chat_service.get_response(user_id=user_id, session_id=session_id, message=message)]
    
    chat_service.user_service.get_user.assert_awaited_once_with("id", user_id, ["profile.*"])
    chat_service.chat_repository.get_session.assert_called_once_with(session_id)
    mock_get_prompt_generator.assert_called_once()
    
    assert len(response) == 1
    assert response[0].message_id == "message_id"

def test_add_message(chat_service):
    """
    Test adding a message to a chat session.
    1. Should add a user or agent message to the chat repository.
    2. Should add tool calls if they exist.
    """
    chat_service.chat_repository.add_chat_message = MagicMock(return_value=MagicMock(id=uuid.uuid4()))
    
    chat_service._add_message(session_id=session_id, is_user=True, message="User message")
    
    chat_service.chat_repository.add_chat_message.assert_called_once_with(session_id=session_id, is_user=True, content="User message")

@patch("app.services.chat_service.LessonDiscussionPrompt", autospec=True)
def test_get_prompt_generator_lesson(mock_lesson_prompt, chat_service):
    """
    Test generating a prompt for lesson discussion.
    1. Should retrieve lesson content from course_repository.
    2. Should call LessonDiscussionPrompt to get responses.
    """
    chat_service.chat_repository.get_chat_messages = MagicMock(return_value=[])
    chat_service.course_repository.get_lesson = MagicMock(return_value=mock_lesson)
    
    mock_prompt_instance = mock_lesson_prompt.return_value
    mock_prompt_instance.get_responses = MagicMock()
    
    chat_service.get_prompt_generator(
        session=MagicMock(id=session_id, prompt_type=PromptType.LESSON.value, resource_id=resource_id),
        input=message
    )
    
    chat_service.course_repository.get_lesson.assert_called_once_with(resource_id)
    mock_prompt_instance.get_responses.assert_called_once()
