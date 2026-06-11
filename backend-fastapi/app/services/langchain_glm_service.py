"""
LLM Service - provider-agnostic LangChain integration.

Both ZhipuAI and OpenAI are reached through the OpenAI-compatible chat
protocol via ChatOpenAI; provider/model/base_url resolve from env config
(see app/core/llm_config.py). Default provider remains ZhipuAI GLM.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.llm_config import resolve_llm_config

# Backward-compat constants (existing imports elsewhere keep working)
ZHIPUAI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
ZHIPUAI_MODEL = "glm-4"
ZHIPUAI_MODEL_PLUS = "glm-4-plus"
ZHIPUAI_MODEL_AIR = "glm-4-air"
ZHIPUAI_MODEL_FLASH = "glm-4-flash"


class LLMService:
    """Provider-agnostic chat service. LLM construction is deferred to first
    use so the app (and the eval harness) can import this module without any
    API key configured."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tier: str = "default",
    ):
        self._config = resolve_llm_config(
            settings, tier, model=model, base_url=base_url, api_key=api_key
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm: Optional[ChatOpenAI] = None

    @property
    def model(self) -> str:
        return self._config.model

    @property
    def api_key(self) -> str:
        return self._config.api_key

    @property
    def llm(self) -> ChatOpenAI:
        if self._llm is None:
            if not self._config.api_key:
                raise ValueError(
                    "No LLM API key configured. Set LLM_API_KEY "
                    "(or ZHIPUAI_API_KEY for the zhipuai provider)."
                )
            self._llm = ChatOpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                model=self._config.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        return self._llm

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Simple conversation - system prompt + user prompt.

        Args:
            system_prompt: System prompt
            user_prompt: User input
            temperature: Temperature parameter (overrides init value)
            max_tokens: Max token count (overrides init value)

        Returns:
            AI response content
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        kwargs = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = await self.llm.ainvoke(messages, **kwargs)
        return response.content

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Multi-turn conversation - supports conversation history.

        Args:
            messages: Message list, format: [{"role": "user", "content": "Hello"}]
            temperature: Temperature parameter
            max_tokens: Max token count

        Returns:
            AI response content
        """
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))

        kwargs = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = await self.llm.ainvoke(lc_messages, **kwargs)
        return response.content

    async def chat_with_history(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Conversation with history.

        Args:
            user_message: Current user message
            history: Conversation history
            system_prompt: System prompt (optional)

        Returns:
            AI response content
        """
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_message))

        response = await self.llm.ainvoke(messages)
        return response.content

    async def stream_chat(
        self,
        system_prompt: str,
        user_prompt: str,
    ):
        """
        Streaming conversation (generator).

        Args:
            system_prompt: System prompt
            user_prompt: User input

        Yields:
            Streaming response content chunks
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        async for chunk in self.llm.astream(messages):
            yield chunk.content

    def get_llm(self):
        """
        Get LangChain LLM instance for creating Agents.

        Returns:
            ChatOpenAI instance
        """
        return self.llm


# Global singletons (names preserved; tier mapping per spec section 5.3).
# Their _config is resolved once at import; .llm stays lazy, so importing
# this module without an API key is safe but later settings changes do not
# affect already-constructed instances.
langchain_glm_service = LLMService(tier="default")

glm_service_flash = LLMService(tier="fast")     # fast responses
glm_service_plus = LLMService(tier="quality")   # high quality
glm_service_air = LLMService(tier="light")      # lightweight

# Backward-compat alias
LangChainGLMService = LLMService
