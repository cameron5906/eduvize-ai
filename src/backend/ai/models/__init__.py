import logging
from typing import Generator, List, Tuple
from ai.prompts import BasePrompt
from ai.common import BaseChatMessage, BaseChatResponse, BaseTool
from domain.dto.ai import CompletionChunk

class BaseModel:
    def get_responses(self, prompt: BasePrompt) -> List[BaseChatResponse]:
        """
        Performs a streaming request to the AI model and returns the final response synchronously

        Args:
            prompt (BasePrompt): The prompt to send to the AI model

        Returns:
            List[BaseChatResponse]: The final response from the AI model
        """
        generator = self.get_streaming_response(prompt)

        while True:
            try:
                next(generator)
            except StopIteration as e:
                return e.value
    
    def get_streaming_response(self, prompt: BasePrompt) -> Generator[CompletionChunk, None, List[BaseChatResponse]]:
        """
        Performs a streaming request to the AI model and returns the response as a generator

        Args:
            prompt (BasePrompt): The prompt to send to the AI model

        Yields:
            Generator[CompletionChunk, None, List[BaseChatResponse]]: Metadata about the completion chunk
            
        Returns:
            List[BaseChatResponse]: The final response from the AI model
        """
        raise NotImplementedError("Method not implemented")
    
    def get_message(self, message: BaseChatMessage) -> dict:
        raise NotImplementedError("Method not implemented")

    def get_tool(self, tool: BaseTool) -> dict:
        raise NotImplementedError("Method not implemented")