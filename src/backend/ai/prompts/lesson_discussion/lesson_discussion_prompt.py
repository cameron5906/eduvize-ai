from typing import Generator, List
from ai.prompts.base_prompt import BasePrompt
from ai.common import BaseChatResponse, BaseChatMessage, ChatRole
from domain.dto.ai.completion_chunk import CompletionChunk

class LessonDiscussionPrompt(BasePrompt):
    def setup(self) -> None:
        self.set_system_prompt("""
You are a helpful assistant who answers questions and helps students comprehend the lesson.
You will not go off topic and will only discuss the lesson content.
""".strip())
    
    def get_responses(
        self,
        history: List[BaseChatMessage],
        lesson_content: str,
        message: str
    ) -> Generator[CompletionChunk, None, List[BaseChatResponse]]:
        from ai.models.gpt_4o import GPT4o
        model = GPT4o()
        
        self.add_user_message(f"""
Lesson content:
{lesson_content}
""".strip())
        
        for message in history:
            if message.role == ChatRole.USER:
                self.add_user_message(message.message)
            elif message.role == ChatRole.AGENT:
                self.add_agent_message(
                    message=message.message,
                    tool_calls=message.tool_calls
                )
                
        self.add_user_message(message)
        
        response_generator = model.get_streaming_response(self)
        
        while True:
            try:
                yield next(response_generator)
            except StopIteration as e:
                return e.value