from dependency_injector import containers, providers

from conversation_manager.sliding_window_conversation_manager import (
    SlidingWindowConversationManager,
)
from text_embedding.ollama_text_embedder import OllamaTextEmbedder


class KrishnaAgentContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    persistent_conversation_manager = providers.Singleton(
        SlidingWindowConversationManager,
        persist_to_file=True,
        conversation_file=config.conversation_file.optional(),
    )

    in_memory_conversation_manager = providers.Factory(
        SlidingWindowConversationManager,
        persist_to_file=False,
    )

    conversation_manager = providers.Selector(
        config.mode.from_value("persistent"),  # type: ignore[func-returns-value]
        persistent=persistent_conversation_manager,
        memory=in_memory_conversation_manager,
    )

    text_embedder = providers.Singleton(OllamaTextEmbedder)

container = KrishnaAgentContainer()
