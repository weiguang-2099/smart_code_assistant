from zhipuai import ZhipuAI
from typing import Optional, List, Dict, Any
from app.core.config import settings


class GLMService:
    """智谱AI GLM模型服务封装"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化GLM服务

        Args:
            api_key: 智谱AI API密钥，如果未提供则从配置中读取
        """
        self.api_key = api_key or settings.ZHIPUAI_API_KEY
        if not self.api_key:
            raise ValueError("ZHIPUAI_API_KEY not configured")
        self.client = ZhipuAI(api_key=self.api_key)

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "glm-4",
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Call GLM chat model with system and user prompts.

        Args:
            system_prompt: System message content
            user_prompt: User message content
            model: Model name, default is glm-4
            temperature: Temperature parameter, controls randomness, range 0-1
            top_p: Sampling parameter, controls output diversity
            max_tokens: Maximum generation tokens

        Returns:
            Response content string
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "glm-4",
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Call GLM chat model with message history.

        Args:
            messages: Message list, format: [{"role": "user", "content": "Hello"}]
            model: Model name, default is glm-4
            temperature: Temperature parameter, controls randomness, range 0-1
            top_p: Sampling parameter, controls output diversity
            max_tokens: Maximum generation tokens

        Returns:
            Response content string
        """
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def chat_old(
        self,
        messages: List[Dict[str, str]],
        model: str = "glm-4",
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        调用GLM聊天模型

        Args:
            messages: 消息列表，格式: [{"role": "user", "content": "你好"}]
            model: 模型名称，默认为 glm-4
            temperature: 温度参数，控制随机性，范围0-1
            top_p: 采样参数，控制输出多样性
            max_tokens: 最大生成token数

        Returns:
            包含响应结果的字典
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
            return {
                "success": True,
                "data": {
                    "content": response.choices[0].message.content,
                    "model": response.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                },
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def code_assist(
        self,
        code: str,
        instruction: str,
        language: str = "python",
        model: str = "glm-4",
    ) -> Dict[str, Any]:
        """
        代码辅助功能

        Args:
            code: 用户代码
            instruction: 用户指令（如：解释这段代码、优化代码等）
            language: 编程语言
            model: 模型名称

        Returns:
            包含响应结果的字典
        """
        system_prompt = f"""你是一个专业的编程助手，擅长 {language} 语言编程。
请根据用户的指令提供准确、清晰的回答。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"代码:\n```{language}\n{code}\n```\n\n指令: {instruction}"},
        ]
        
        return await self.chat(messages, model=model)


# 创建全局GLM服务实例
glm_service = GLMService()
