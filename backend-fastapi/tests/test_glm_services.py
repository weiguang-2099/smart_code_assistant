"""
Tests for the GLM wrapper services.

We mock the ZhipuAI client and LangChain ChatOpenAI to keep tests offline.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.glm_service import GLMService
from app.services.langchain_glm_service import LangChainGLMService


# ============================================================================
# GLMService
# ============================================================================

class TestGLMServiceInit:
    def test_requires_api_key(self, monkeypatch):
        monkeypatch.setattr("app.services.glm_service.settings", MagicMock(ZHIPUAI_API_KEY=""))
        with pytest.raises(ValueError, match="ZHIPUAI_API_KEY"):
            GLMService()

    def test_explicit_api_key_used(self):
        with patch("app.services.glm_service.ZhipuAI") as Client:
            svc = GLMService(api_key="my-key")
            assert svc.api_key == "my-key"
            Client.assert_called_once_with(api_key="my-key")


class TestGLMServiceChat:
    @pytest.mark.asyncio
    async def test_chat_returns_content_string(self):
        with patch("app.services.glm_service.ZhipuAI") as Client:
            mock_choice = MagicMock()
            mock_choice.message.content = "hello world"
            Client.return_value.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

            svc = GLMService(api_key="k")
            result = await svc.chat("sys", "user")

            assert result == "hello world"
            call = Client.return_value.chat.completions.create.call_args.kwargs
            assert call["model"] == "glm-4"
            assert call["messages"][0]["role"] == "system"
            assert call["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_chat_completion_forwards_messages(self):
        with patch("app.services.glm_service.ZhipuAI") as Client:
            mock_choice = MagicMock()
            mock_choice.message.content = "ok"
            Client.return_value.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

            svc = GLMService(api_key="k")
            msgs = [{"role": "user", "content": "hi"}]
            result = await svc.chat_completion(msgs, temperature=0.1, max_tokens=64)

            assert result == "ok"
            call = Client.return_value.chat.completions.create.call_args.kwargs
            assert call["messages"] == msgs
            assert call["temperature"] == 0.1
            assert call["max_tokens"] == 64


class TestGLMServiceChatOld:
    @pytest.mark.asyncio
    async def test_returns_success_envelope(self):
        with patch("app.services.glm_service.ZhipuAI") as Client:
            response = MagicMock()
            response.choices = [MagicMock(message=MagicMock(content="hi"))]
            response.model = "glm-4"
            response.usage.prompt_tokens = 5
            response.usage.completion_tokens = 2
            response.usage.total_tokens = 7
            Client.return_value.chat.completions.create.return_value = response

            svc = GLMService(api_key="k")
            result = await svc.chat_old([{"role": "user", "content": "hi"}])

            assert result["success"] is True
            assert result["data"]["content"] == "hi"
            assert result["data"]["usage"]["total_tokens"] == 7

    @pytest.mark.asyncio
    async def test_returns_failure_envelope_on_exception(self):
        with patch("app.services.glm_service.ZhipuAI") as Client:
            Client.return_value.chat.completions.create.side_effect = RuntimeError("api down")

            svc = GLMService(api_key="k")
            result = await svc.chat_old([{"role": "user", "content": "hi"}])

            assert result["success"] is False
            assert "api down" in result["error"]


# ============================================================================
# LangChainGLMService
# ============================================================================

class TestLangChainGLMService:
    def test_requires_api_key(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.langchain_glm_service.settings",
            MagicMock(ZHIPUAI_API_KEY=""),
        )
        with pytest.raises(ValueError):
            LangChainGLMService()

    def test_get_llm_returns_inner_llm(self):
        with patch("app.services.langchain_glm_service.ChatOpenAI") as ChatOpenAI:
            ChatOpenAI.return_value = MagicMock(name="llm-instance")
            svc = LangChainGLMService(api_key="k")
            assert svc.get_llm() is svc.llm

    @pytest.mark.asyncio
    async def test_chat_invokes_llm_with_system_and_user_messages(self):
        with patch("app.services.langchain_glm_service.ChatOpenAI") as ChatOpenAI:
            llm = ChatOpenAI.return_value
            llm.ainvoke = AsyncMock(return_value=MagicMock(content="resp"))

            svc = LangChainGLMService(api_key="k")
            out = await svc.chat("sys", "user", temperature=0.2, max_tokens=10)

            assert out == "resp"
            msgs, kwargs = llm.ainvoke.call_args[0][0], llm.ainvoke.call_args.kwargs
            assert len(msgs) == 2
            assert kwargs == {"temperature": 0.2, "max_tokens": 10}

    @pytest.mark.asyncio
    async def test_chat_completion_translates_roles(self):
        with patch("app.services.langchain_glm_service.ChatOpenAI") as ChatOpenAI:
            llm = ChatOpenAI.return_value
            llm.ainvoke = AsyncMock(return_value=MagicMock(content="ok"))

            svc = LangChainGLMService(api_key="k")
            await svc.chat_completion([
                {"role": "system", "content": "s"},
                {"role": "user", "content": "u"},
                {"role": "assistant", "content": "a"},
            ])
            translated = llm.ainvoke.call_args[0][0]
            assert len(translated) == 3
            # role types: SystemMessage, HumanMessage, AIMessage
            assert type(translated[0]).__name__ == "SystemMessage"
            assert type(translated[1]).__name__ == "HumanMessage"
            assert type(translated[2]).__name__ == "AIMessage"

    @pytest.mark.asyncio
    async def test_chat_with_history_appends_current_message(self):
        with patch("app.services.langchain_glm_service.ChatOpenAI") as ChatOpenAI:
            llm = ChatOpenAI.return_value
            llm.ainvoke = AsyncMock(return_value=MagicMock(content="ok"))

            svc = LangChainGLMService(api_key="k")
            await svc.chat_with_history(
                user_message="current",
                history=[{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}],
                system_prompt="sys",
            )
            sent = llm.ainvoke.call_args[0][0]
            # system + 2 history + current = 4
            assert len(sent) == 4
            assert sent[-1].content == "current"

    @pytest.mark.asyncio
    async def test_stream_chat_yields_each_chunk(self):
        with patch("app.services.langchain_glm_service.ChatOpenAI") as ChatOpenAI:
            llm = ChatOpenAI.return_value

            async def fake_astream(*_args, **_kwargs):
                for c in ["a", "b", "c"]:
                    yield MagicMock(content=c)

            llm.astream = fake_astream

            svc = LangChainGLMService(api_key="k")
            chunks = []
            async for c in svc.stream_chat("sys", "user"):
                chunks.append(c)
            assert chunks == ["a", "b", "c"]
