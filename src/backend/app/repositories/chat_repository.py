import logging
import json
import uuid
from typing import List, Optional

from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from domain.schema.chat import ChatMessage, ChatSession, ChatToolCall
from common.database import engine

logger = logging.getLogger("ChatRepository")

class ChatRepository:
    def create_chat_session(
        self,
        user_id: uuid.UUID,
        prompt_type: str,
        resource_id: Optional[uuid.UUID] = None
    ) -> ChatSession:
        """
        Creates a new chat session

        Args:
            user_id (uuid.UUID): The user that owns the chat session

        Returns:
            ChatSession: The created chat session
        """
        
        with Session(engine) as session:
            chat_session = ChatSession(
                user_id=user_id,
                prompt_type=prompt_type,
                resource_id=resource_id
            )
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            
            return chat_session
    
    def add_chat_message(
        self, 
        session_id: uuid.UUID,
        is_user: bool,
        content: Optional[str]
    ) -> ChatMessage:
        """
        Adds a message to a chat session

        Args:
            user_id (str): The user that owns the chat session
            message_dto (ChatMessageDto): The message to add

        Returns:
            ChatMessage: The added message
        """
        
        with Session(engine) as session:
            chat_message = ChatMessage(
                session_id=session_id,
                is_user=is_user,
                content=content
            )
            session.add(chat_message)
            session.commit()
            session.refresh(chat_message)
            
            return chat_message
        
    def add_tool_message(
        self,
        message_id: uuid.UUID,
        call_id: str,
        tool_name: str,
        arguments: str,
        result: str
    ):
        with Session(engine) as session:
            tool_call = ChatToolCall(
                message_id=message_id,
                tool_call_id=call_id,
                tool_name=tool_name,
                json_arguments=arguments,
                result=result
            )
            session.add(tool_call)
            session.commit()
        
    def get_session(
        self,
        session_id: uuid.UUID
    ) -> Optional[ChatSession]:
        """
        Gets a chat session by ID
        
        Args:
            session_id (uuid.UUID): The ID of the chat session to get
            
        Returns:
            Optional[ChatSession]: The chat session, if found
        """
        
        with Session(engine) as session:
            query = select(ChatSession).where(ChatSession.id == session_id)
            return session.exec(query).unique().first()
        
    def get_chat_messages(
        self,
        session_id: uuid.UUID
    ) -> List[ChatMessage]:
        """
        Gets all messages in a chat session

        Args:
            user_id (uuid.UUID): The user that owns the chat session
            session_id (uuid.UUID): The chat session to get messages for

        Returns:
            List[ChatMessage]: The messages in the chat session
        """
        
        logger.info(f"Getting chat messages for session {session_id}")
        
        with Session(engine) as session:
            query = select(ChatMessage).where(
                ChatMessage.session_id == session_id
            )
            
            query = query.options(joinedload(ChatMessage.tool_calls))
            
            # Order by created_at_utc descending
            query = query.order_by(ChatMessage.created_at_utc.desc())
            query = query.limit(50)
            
            messages = session.exec(query).unique().all()
            messages.reverse()
            
            return messages