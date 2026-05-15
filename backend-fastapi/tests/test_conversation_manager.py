"""Tests for conversation manager"""
import pytest
from app.services.conversation_manager import ConversationManager


class TestConversationManager:
    """Test conversation history management"""

    def test_compress_history_returns_unchanged_when_short(self):
        """Short history should not be compressed"""
        manager = ConversationManager()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = manager.compress_history(history)

        assert result == history

    def test_compress_history_adds_summary_when_long(self):
        """Long history should include summary"""
        manager = ConversationManager(max_turns=4)

        # Create 8 messages (4 turns)
        history = []
        for i in range(4):
            history.append({"role": "user", "content": f"Question {i}"})
            history.append({"role": "assistant", "content": f"Answer {i}"})

        result = manager.compress_history(history)

        # Should have summary + recent messages
        assert len(result) <= 6  # summary + 2 turns (4 messages)
        assert any("摘要" in msg.get("content", "") or "summary" in msg.get("content", "").lower() for msg in result if msg.get("role") == "system")

    def test_estimate_tokens_counts_correctly(self):
        """Token estimation should be reasonable"""
        manager = ConversationManager()

        messages = [
            {"role": "user", "content": "Hello world"},  # ~3 tokens
            {"role": "assistant", "content": "Hi there!"},  # ~3 tokens
        ]

        tokens = manager.estimate_tokens(messages)

        # ~6 tokens * 4 chars = ~24 chars / 4 = ~6 tokens
        assert 3 <= tokens <= 10

    def test_truncate_if_needed_removes_old_messages(self):
        """Should remove old messages when over token limit"""
        manager = ConversationManager(max_tokens=50)

        # Create long messages
        history = [
            {"role": "user", "content": "x" * 100},  # 25 tokens
            {"role": "assistant", "content": "y" * 100},  # 25 tokens
            {"role": "user", "content": "z" * 100},  # 25 tokens
            {"role": "assistant", "content": "w" * 100},  # 25 tokens
        ]

        result = manager.truncate_if_needed(history)

        # Should remove messages to get under 50 tokens
        estimated = manager.estimate_tokens(result)
        assert estimated <= 50

    def test_prepare_for_llm_combines_compression_and_truncation(self):
        """Should compress then truncate"""
        manager = ConversationManager(max_turns=3, max_tokens=100)

        # Create history that needs both compression and truncation
        history = []
        for i in range(10):
            history.append({"role": "user", "content": f"Question {i}" * 50})
            history.append({"role": "assistant", "content": f"Answer {i}" * 50})

        result = manager.prepare_for_llm(history)

        # Should be compressed and truncated
        assert manager.estimate_tokens(result) <= 100
