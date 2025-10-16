class BaseTextEmbedder:
    """Base class for text embedders."""

    def embed_text(self, text: str) -> list[float]:
        """Embed a single piece of text.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        raise NotImplementedError(
            "embed_text method must be implemented by subclasses."
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple pieces of text.

        Args:
            texts: A list of texts to embed.

        Returns:
            A list of lists of floats, where each inner list represents the embedding vector for a text.
        """
        raise NotImplementedError(
            "embed_text method must be implemented by subclasses."
        )
