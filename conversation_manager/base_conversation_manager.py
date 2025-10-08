from abc import ABC, abstractmethod
from common.models import Message

class BaseConversationManager(ABC):
    @abstractmethod
    def add_message(self, message: Message) -> None:
        pass
    
    @abstractmethod
    def fetch_conversation(self, window_size: int = 20) -> list[Message]:
        pass
    
    @abstractmethod
    def persist_conversation(self) -> None:
        pass