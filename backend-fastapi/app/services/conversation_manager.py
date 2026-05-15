"""
Conversation Manager - Handles conversation history compression and token control

Provides utilities to manage conversation history length and token usage
for LLM interactions.
"""
from typing import List, Dict, Optional


class ConversationManager:
    """
    Manages conversation history with compression and token control.

    Features:
    - Sliding window for recent messages
    - Summary generation for old messages
    - Token counting and limiting
    """

    MAX_TURNS = 10
    MAX_TOKENS = 4000
    SUMMARY_THRESHOLD = 6  # Turns before compression kicks in

    def __init__(
        self,
        max_turns: Optional[int] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize conversation manager.

        Args:
            max_turns: Maximum turns to keep (default: 10)
            max_tokens: Maximum tokens allowed (default: 4000)
        """
        self.max_turns = max_turns or self.MAX_TURNS
        self.max_tokens = max_tokens or self.MAX_TOKENS

    def compress_history(self, history: List[Dict]) -> List[Dict]:
        """
        Compress conversation history if too long.

        Args:
            history: List of message dicts with 'role' and 'content'

        Returns:
            Compressed history with summary of old messages
        """
        if len(history) <= self.SUMMARY_THRESHOLD:
            return history

        # Calculate how many turns to keep (half of max_turns for summary room)
        keep_turns = max(1, self.max_turns // 2)
        keep_messages = keep_turns * 2

        # Keep recent messages
        recent = history[-keep_messages:] if keep_messages > 0 else []

        # Create summary of old messages
        old_messages = history[:-keep_messages] if keep_messages > 0 else history

        if old_messages:
            summary = self._create_summary_context(old_messages)
            return [{"role": "system", "content": summary}] + recent

        return recent

    def _create_summary_context(self, messages: List[Dict]) -> str:
        """
        Create summary context from old messages.

        Args:
            messages: List of old message dicts

        Returns:
            Summary string
        """
        conversation_text = self._format_messages(messages)

        # Truncate if too long
        if len(conversation_text) > 500:
            conversation_text = conversation_text[:500] + "..."

        return "[历史对话摘要]" + chr(10) + "之前的讨论主要涉及: " + conversation_text

    def _format_messages(self, messages: List[Dict]) -> str:
        """
        Format messages into readable text.

        Args:
            messages: List of message dicts

        Returns:
            Formatted string
        """
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]  # Truncate long messages
            formatted.append(f"{role}: {content}")
        return chr(10).join(formatted)

    def estimate_tokens(self, messages: List[Dict]) -> int:
        """
        Estimate token count for messages.

        Uses simple heuristic: 1 token = 4 characters

        Args:
            messages: List of message dicts

        Returns:
            Estimated token count
        """
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return total_chars // 4

    def truncate_if_needed(self, messages: List[Dict]) -> List[Dict]:
        """
        Truncate messages if over token limit.

        Removes oldest messages first to stay under limit.

        Args:
            messages: List of message dicts

        Returns:
            Truncated message list
        """
        if self.estimate_tokens(messages) <= self.max_tokens:
            return messages

        result = messages.copy()

        # Remove oldest messages until under limit
        while result and self.estimate_tokens(result) > self.max_tokens:
            # Remove first two messages (one turn)
            if len(result) >= 2:
                result = result[2:]
            else:
                result = []

        return result

    def prepare_for_llm(
        self,
        history: List[Dict],
        max_tokens: Optional[int] = None
    ) -> List[Dict]:
        """
        Prepare history for LLM call (compress + truncate).

        Args:
            history: Raw conversation history
            max_tokens: Optional token limit override

        Returns:
            Prepared history ready for LLM
        """
        # First compress if needed
        compressed = self.compress_history(history)

        # Then truncate if over token limit
        limit = max_tokens or self.max_tokens
        if self.estimate_tokens(compressed) > limit:
            manager = ConversationManager(max_tokens=limit)
            return manager.truncate_if_needed(compressed)

        return compressed


# Global instance for convenience
conversation_manager = ConversationManager()
