from text_embedding.base_text_embedder import BaseTextEmbedder
import requests
import ollama


class OllamaTextEmbedder(BaseTextEmbedder):
    def embed_text(self, text: str) -> list[float]:
        """Embed a single piece of text using Ollama.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        import subprocess
        import json

        try:
            response = ollama.embed(model="nomic-embed-text", input=text)
            return list(response.embeddings[0])
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Error executing Ollama command: {e.stderr.strip() if e.stderr else str(e)}"
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Error parsing Ollama output: {str(e)}")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple pieces of text using Ollama.

        Args:
            texts: A list of texts to embed.

        Returns:
            A list of lists of floats, where each inner list represents the embedding vector for a text.
        """
        response = ollama.embed(model="nomic-embed-text", input=texts)
        return [list(embedding) for embedding in response.embeddings]
