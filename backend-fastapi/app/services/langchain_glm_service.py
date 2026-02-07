"""
LangChain GLM Service - 智谱 AI LangChain 集成

使用 OpenAI 兼容接口连接智谱 AI，支持 LangChain Agent 和 Tool Calling
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import List, Dict, Any, Optional
from app.core.config import settings

# 智谱 AI OpenAI 兼容接口配置
ZHIPUAI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
ZHIPUAI_MODEL = "glm-4"
ZHIPUAI_MODEL_PLUS = "glm-4-plus"
ZHIPUAI_MODEL_AIR = "glm-4-air"
ZHIPUAI_MODEL_FLASH = "glm-4-flash"


class LangChainGLMService:
    """
    基于 LangChain 的智谱 AI 服务

    使用 ChatOpenAI 通过智谱 AI 的 OpenAI 兼容接口调用 GLM 模型
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = ZHIPUAI_BASE_URL,
        model: str = ZHIPUAI_MODEL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ):
        """
        初始化 LangChain GLM 服务

        Args:
            api_key: 智谱 API 密钥，默认从配置读取
            base_url: API 基础 URL，默认使用智谱兼容接口
            model: 模型名称
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成 token 数
        """
        self.api_key = api_key or settings.ZHIPUAI_API_KEY
        if not self.api_key:
            raise ValueError("ZHIPUAI_API_KEY not configured")

        self.model = model
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        简单对话 - 系统提示 + 用户提示

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            temperature: 温度参数（覆盖初始化值）
            max_tokens: 最大 token 数（覆盖初始化值）

        Returns:
            AI 响应内容
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # 动态设置参数
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
        多轮对话 - 支持对话历史

        Args:
            messages: 消息列表，格式: [{"role": "user", "content": "Hello"}]
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            AI 响应内容
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

        # 动态设置参数
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
        带历史记录的对话

        Args:
            user_message: 当前用户消息
            history: 对话历史
            system_prompt: 系统提示词（可选）

        Returns:
            AI 响应内容
        """
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        # 添加历史消息
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        # 添加当前用户消息
        messages.append(HumanMessage(content=user_message))

        response = await self.llm.ainvoke(messages)
        return response.content

    async def stream_chat(
        self,
        system_prompt: str,
        user_prompt: str,
    ):
        """
        流式对话（生成器）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入

        Yields:
            流式响应内容块
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        async for chunk in self.llm.astream(messages):
            yield chunk.content

    def get_llm(self):
        """
        获取 LangChain LLM 实例，用于创建 Agent

        Returns:
            ChatOpenAI 实例
        """
        return self.llm


# 创建全局单例实例
langchain_glm_service = LangChainGLMService()


# 创建不同模型的专用实例
glm_service_flash = LangChainGLMService(model=ZHIPUAI_MODEL_FLASH)  # 快速响应
glm_service_plus = LangChainGLMService(model=ZHIPUAI_MODEL_PLUS)    # 高质量
glm_service_air = LangChainGLMService(model=ZHIPUAI_MODEL_AIR)      # 轻量级
