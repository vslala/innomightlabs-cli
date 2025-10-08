from conversation_manager.base_conversation_manager import BaseConversationManager
from common.models import Message

class SlidingWindowConversationManager(BaseConversationManager):
    
    def __init__(self) -> None:
        self.messages = []
           
    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        
    def fetch_conversation(self, window_size: int = 20) -> list[Message]:
        return self.messages[-window_size:]
    
    def persist_conversation(self) -> None:
        pass
    