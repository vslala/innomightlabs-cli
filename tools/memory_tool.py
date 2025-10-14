from datetime import datetime
from typing import List, Optional, Dict, Any, Union
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

from common.decorators import Tool
from text_embedding.base_text_embedder import BaseTextEmbedder
from common.models import BaseTool
from common.containers import container
from dependency_injector.wiring import Provide


@dataclass
class MemoryEntry:
    """Structured memory entry with metadata and embedding"""

    id: int  # Line number in the file
    content: str
    timestamp: str
    tags: List[str]
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def create(
        cls,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_service: Optional[BaseTextEmbedder] = None,
    ) -> "MemoryEntry":
        """Create a new memory entry with auto-generated fields"""
        entry = cls(
            id=0,  # Will be set when adding to file
            content=content,
            timestamp=datetime.now().isoformat(),
            tags=tags or [],
            metadata=metadata or {},
        )

        # Generate embedding if service provided
        if embedding_service:
            entry.embedding = embedding_service.embed_text(content)

        return entry

    def to_ndjson_line(self) -> str:
        """Convert to NDJSON line format"""
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_ndjson_line(cls, line: str) -> "MemoryEntry":
        """Create from NDJSON line"""
        data = json.loads(line.strip())
        return cls(**data)


class MemoryTool:
    """Tool for managing persistent memory with embeddings"""

    def __init__(self, embedding_service: Optional[BaseTextEmbedder] = None):
        self.embedding_service = embedding_service
        self.memory_dir = Path(".krishna")
        self.memory_file = self.memory_dir / "memories.ndjson"
        self._ensure_memory_structure()

    def _ensure_memory_structure(self) -> None:
        """Ensure .krishna directory and memory file exist"""
        self.memory_dir.mkdir(exist_ok=True)
        if not self.memory_file.exists():
            self.memory_file.touch()

    def _get_next_id(self) -> int:
        """Get the next available ID (line number)"""
        if not self.memory_file.exists() or self.memory_file.stat().st_size == 0:
            return 1

        with open(self.memory_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return len(lines) + 1

    def _load_all_memories(self) -> List[MemoryEntry]:
        """Load all memory entries from file"""
        memories: List[MemoryEntry] = []
        if not self.memory_file.exists():
            return memories

        with open(self.memory_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        memory = MemoryEntry.from_ndjson_line(line)
                        memory.id = line_num  # Ensure ID matches line number
                        memories.append(memory)
                    except json.JSONDecodeError:
                        continue  # Skip malformed lines
        return memories

    def append_memory(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        position: str = "end",
        line_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Append memory to file with various positioning options"""
        try:
            # Create memory entry
            memory = MemoryEntry.create(
                content=content,
                tags=tags,
                metadata=metadata,
                embedding_service=self.embedding_service,
            )

            if position == "end":
                memory.id = self._get_next_id()
                with open(self.memory_file, "a", encoding="utf-8") as f:
                    f.write(memory.to_ndjson_line() + "\n")
                return {
                    "success": True,
                    "memory_id": memory.id,
                    "message": f"Memory added at line {memory.id}",
                }

            elif position == "beginning":
                memories = self._load_all_memories()
                memory.id = 1

                # Rewrite file with new memory at beginning
                with open(self.memory_file, "w", encoding="utf-8") as f:
                    f.write(memory.to_ndjson_line() + "\n")
                    for mem in memories:
                        mem.id += 1  # Shift existing IDs
                        f.write(mem.to_ndjson_line() + "\n")

                return {
                    "success": True,
                    "memory_id": memory.id,
                    "message": "Memory added at beginning",
                }

            elif position == "line" and line_number:
                memories = self._load_all_memories()

                if line_number < 1 or line_number > len(memories) + 1:
                    return {
                        "success": False,
                        "error": f"Invalid line number {line_number}",
                    }

                memory.id = line_number

                # Insert at specific position
                with open(self.memory_file, "w", encoding="utf-8") as f:
                    for i, mem in enumerate(memories):
                        if i + 1 == line_number:
                            f.write(memory.to_ndjson_line() + "\n")
                            mem.id += 1
                        elif i + 1 >= line_number:
                            mem.id += 1
                        f.write(mem.to_ndjson_line() + "\n")

                    # If inserting at the very end
                    if line_number == len(memories) + 1:
                        f.write(memory.to_ndjson_line() + "\n")

                return {
                    "success": True,
                    "memory_id": memory.id,
                    "message": f"Memory inserted at line {line_number}",
                }

            else:
                return {
                    "success": False,
                    "error": "Invalid position or missing line_number",
                }

        except Exception as e:
            return {"success": False, "error": f"Failed to append memory: {str(e)}"}

    def scan_memories(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """Scan through memories with pagination"""
        try:
            memories = self._load_all_memories()
            total_memories = len(memories)
            total_pages = (total_memories + page_size - 1) // page_size

            if page < 1 or page > total_pages:
                return {
                    "success": False,
                    "error": f"Invalid page {page}. Total pages: {total_pages}",
                }

            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_memories)
            page_memories = memories[start_idx:end_idx]

            return {
                "success": True,
                "memories": [
                    {
                        "id": mem.id,
                        "content": mem.content,
                        "timestamp": mem.timestamp,
                        "tags": mem.tags,
                        "metadata": mem.metadata,
                    }
                    for mem in page_memories
                ],
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "page_size": page_size,
                    "total_memories": total_memories,
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to scan memories: {str(e)}"}

    def search_memories(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> Dict[str, Any]:
        """Search memories by keyword with pagination"""
        try:
            memories = self._load_all_memories()
            query_lower = query.lower()

            # Filter memories containing the query
            matching_memories = []
            for mem in memories:
                if (
                    query_lower in mem.content.lower()
                    or any(query_lower in tag.lower() for tag in mem.tags)
                    or (mem.metadata and query_lower in str(mem.metadata).lower())
                ):
                    matching_memories.append(mem)

            total_matches = len(matching_memories)
            total_pages = (
                (total_matches + page_size - 1) // page_size if total_matches > 0 else 1
            )

            if page < 1 or page > total_pages:
                return {
                    "success": False,
                    "error": f"Invalid page {page}. Total pages: {total_pages}",
                }

            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_matches)
            page_memories = matching_memories[start_idx:end_idx]

            return {
                "success": True,
                "query": query,
                "memories": [
                    {
                        "id": mem.id,
                        "content": mem.content,
                        "timestamp": mem.timestamp,
                        "tags": mem.tags,
                        "metadata": mem.metadata,
                    }
                    for mem in page_memories
                ],
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "page_size": page_size,
                    "total_matches": total_matches,
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to search memories: {str(e)}"}

    def modify_memory(
        self,
        memory_id: int,
        new_content: str,
        new_tags: Optional[List[str]] = None,
        new_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Modify existing memory by ID"""
        try:
            memories = self._load_all_memories()

            # Find memory to modify
            target_memory = None
            for mem in memories:
                if mem.id == memory_id:
                    target_memory = mem
                    break

            if not target_memory:
                return {
                    "success": False,
                    "error": f"Memory with ID {memory_id} not found",
                }

            # Update memory fields
            target_memory.content = new_content
            target_memory.timestamp = datetime.now().isoformat()  # Update timestamp
            if new_tags is not None:
                target_memory.tags = new_tags
            if new_metadata is not None:
                target_memory.metadata = new_metadata

            # Regenerate embedding for new content
            if self.embedding_service:
                target_memory.embedding = self.embedding_service.embed_text(new_content)

            # Rewrite file with updated memory
            with open(self.memory_file, "w", encoding="utf-8") as f:
                for mem in memories:
                    f.write(mem.to_ndjson_line() + "\n")

            return {
                "success": True,
                "memory_id": memory_id,
                "message": f"Memory {memory_id} updated successfully",
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to modify memory: {str(e)}"}

    def delete_memory(
        self, memory_id: Optional[int] = None, content_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete memory by ID or content text"""
        try:
            memories = self._load_all_memories()
            original_count = len(memories)

            if memory_id:
                memories = [mem for mem in memories if mem.id != memory_id]
                identifier = f"ID {memory_id}"
            elif content_text:
                memories = [mem for mem in memories if content_text not in mem.content]
                identifier = f"content containing '{content_text}'"
            else:
                return {
                    "success": False,
                    "error": "Must provide either memory_id or content_text",
                }

            deleted_count = original_count - len(memories)

            if deleted_count == 0:
                return {
                    "success": False,
                    "error": f"No memories found matching {identifier}",
                }

            # Reassign IDs to maintain line number consistency
            for i, mem in enumerate(memories, 1):
                mem.id = i

            # Rewrite file
            with open(self.memory_file, "w", encoding="utf-8") as f:
                for mem in memories:
                    f.write(mem.to_ndjson_line() + "\n")

            return {
                "success": True,
                "message": f"Deleted {deleted_count} memory(ies) matching {identifier}",
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to delete memory: {str(e)}"}


@Tool
def memory_append(
    content: str,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    position: str = "end",
    line_number: Optional[int] = None,
) -> str:
    """Append memory to file with various positioning options

    Args:
        content: Memory content to store
        tags: Optional list of tags for categorization
        metadata: Optional metadata dictionary
        position: Where to place memory - "end", "beginning", or "line"
        line_number: Specific line number when position is "line"

    Returns:
        Success/error message with memory ID
    """
    try:
        from dependency_injector.wiring import Provide, inject
        from common.containers import container

        @inject
        def _append_with_service(
            embedding_service: BaseTextEmbedder = Provide[container.text_embedder],
        ) -> str:
            tool = MemoryTool(embedding_service)
            result = tool.append_memory(content, tags, metadata, position, line_number)

            if result["success"]:
                return str(result["message"])
            else:
                return f"Error: {result['error']}"

        return _append_with_service()

    except Exception as e:
        return f"Failed to append memory: {str(e)}"


@Tool
def memory_scan(page: int = 1, page_size: int = 10) -> str:
    """Scan through memories with pagination

    Args:
        page: Page number to retrieve (1-based)
        page_size: Number of memories per page

    Returns:
        Formatted list of memories with pagination info
    """
    try:
        from dependency_injector.wiring import Provide, inject
        from common.containers import container

        @inject
        def _scan_with_service(
            embedding_service: BaseTextEmbedder = Provide[container.text_embedder],
        ) -> str:
            tool = MemoryTool(embedding_service)
            result = tool.scan_memories(page, page_size)

            if result["success"]:
                memories_text = []
                for mem in result["memories"]:
                    tags_str = ", ".join(mem["tags"]) if mem["tags"] else "No tags"
                    memories_text.append(
                        f"ID {mem['id']}: {mem['content']} | Tags: {tags_str} | {mem['timestamp']}"
                    )

                pagination = result["pagination"]
                footer = f"\nPage {pagination['current_page']}/{pagination['total_pages']} | Total: {pagination['total_memories']} memories"

                return "\n".join(memories_text) + footer
            else:
                return f"Error: {result['error']}"

        return _scan_with_service()

    except Exception as e:
        return f"Failed to scan memories: {str(e)}"


@Tool
def memory_search(query: str, page: int = 1, page_size: int = 10) -> str:
    """Search memories by keyword with pagination

    Args:
        query: Search query to match against content, tags, and metadata
        page: Page number to retrieve (1-based)
        page_size: Number of results per page

    Returns:
        Formatted list of matching memories with pagination info
    """
    try:
        from dependency_injector.wiring import Provide, inject
        from common.containers import container

        @inject
        def _search_with_service(
            embedding_service: BaseTextEmbedder = Provide[container.text_embedder],
        ) -> str:
            tool = MemoryTool(embedding_service)
            result = tool.search_memories(query, page, page_size)

            if result["success"]:
                memories_text = []
                for mem in result["memories"]:
                    tags_str = ", ".join(mem["tags"]) if mem["tags"] else "No tags"
                    memories_text.append(
                        f"ID {mem['id']}: {mem['content']} | Tags: {tags_str} | {mem['timestamp']}"
                    )

                pagination = result["pagination"]
                header = f"Search results for '{result['query']}'"
                footer = f"\nPage {pagination['current_page']}/{pagination['total_pages']} | Found: {pagination['total_matches']} matches"

                return header + "\n" + "\n".join(memories_text) + footer
            else:
                return f"Error: {result['error']}"

        return _search_with_service()

    except Exception as e:
        return f"Failed to search memories: {str(e)}"


@Tool
def memory_modify(
    memory_id: int,
    new_content: str,
    new_tags: Optional[List[str]] = None,
    new_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Modify existing memory by ID

    Args:
        memory_id: ID of memory to modify
        new_content: New content for the memory
        new_tags: Optional new tags list
        new_metadata: Optional new metadata dictionary

    Returns:
        Success/error message
    """
    try:
        from dependency_injector.wiring import Provide, inject
        from common.containers import container

        @inject
        def _modify_with_service(
            embedding_service: BaseTextEmbedder = Provide[container.text_embedder],
        ) -> str:
            tool = MemoryTool(embedding_service)
            result = tool.modify_memory(memory_id, new_content, new_tags, new_metadata)

            if result["success"]:
                return str(result["message"])
            else:
                return f"Error: {result['error']}"

        return _modify_with_service()

    except Exception as e:
        return f"Failed to modify memory: {str(e)}"


@Tool
def memory_delete(
    memory_id: Optional[int] = None, content_text: Optional[str] = None
) -> str:
    """Delete memory by ID or content text

    Args:
        memory_id: ID of memory to delete
        content_text: Text content to match for deletion

    Returns:
        Success/error message with deletion count
    """
    try:
        from dependency_injector.wiring import Provide, inject
        from common.containers import container

        @inject
        def _delete_with_service(
            embedding_service: BaseTextEmbedder = Provide[container.text_embedder],
        ) -> str:
            tool = MemoryTool(embedding_service)
            result = tool.delete_memory(memory_id, content_text)

            if result["success"]:
                return str(result["message"])
            else:
                return f"Error: {result['error']}"

        return _delete_with_service()

    except Exception as e:
        return f"Failed to delete memory: {str(e)}"
