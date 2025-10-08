from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Generator

from langchain_aws import ChatBedrockConverse

class BaseAgent(ABC):
    
    @abstractmethod
    def stream(self, prompt: Any) -> AsyncGenerator[str, None]:
        pass
    
    @abstractmethod
    def send_message(self, user_message: Any) -> Generator[str, None]:
        pass