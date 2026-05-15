"""
AI Agent API Routes - LangChain Agent 端点

提供基于 LangChain 的智能 Agent 服务，支持代码生成、审查、分析等功能
"""
import asyncio
import hashlib
import re
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.core.cache import global_cache_manager
from app.models.user import User
from app.services.langchain_glm_service import langchain_glm_service
from app.services.code_tools import (
    langchain_tools_dict,
    get_tool,
    CodeToolName,
    tool_descriptions,
)
from app.services.conversation_manager import conversation_manager
from app.schemas.agent import (
    AgentAnalyzeRequest,
    AgentAnalyzeResponse,
    AgentGenerateRequest,
    AgentGenerateResponse,
    AgentReviewRequest,
    AgentReviewResponse,
    AgentChatRequest,
    AgentChatResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

TOOL_TIMEOUT_SECONDS = 5.0
TOOL_CACHE_TTL = 300


# ============================================================================
# Agent 辅助函数
# ============================================================================

async def run_tool_analysis(code: str, language: str) -> Dict[str, str]:
    """
    并行运行所有分析工具，带超时控制和缓存。

    Args:
        code: 要分析的代码
        language: 编程语言

    Returns:
        工具名称 -> 分析结果的字典
    """
    cache_key = f"tool_analysis:{hashlib.sha256(f'{code}:{language}'.encode()).hexdigest()[:32]}"

    cached_result = await global_cache_manager.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Tool analysis cache hit for {cache_key[:16]}")
        return cached_result

    tool_names = [
        CodeToolName.ANALYZE_STRUCTURE,
        CodeToolName.DETECT_SMELLS,
        CodeToolName.CALCULATE_COMPLEXITY,
        CodeToolName.CHECK_SECURITY,
    ]

    tools = []
    for name in tool_names:
        tool = get_tool(name)
        if tool:
            tools.append(tool)

    async def run_tool_with_timeout(tool) -> tuple:
        """Run a single tool with timeout control."""
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(tool.invoke, {"code": code, "language": language}),
                timeout=TOOL_TIMEOUT_SECONDS
            )
            return tool.name, result
        except asyncio.TimeoutError:
            logger.warning(f"Tool {tool.name} timed out after {TOOL_TIMEOUT_SECONDS}s")
            return tool.name, f"分析超时（>{TOOL_TIMEOUT_SECONDS}s）"
        except Exception as e:
            logger.error(f"Tool {tool.name} failed: {e}")
            return tool.name, f"分析失败: {str(e)}"

    tasks = [run_tool_with_timeout(tool) for tool in tools]
    results_list = await asyncio.gather(*tasks)

    results = {name: result for name, result in results_list}

    await global_cache_manager.set(cache_key, results, ttl=TOOL_CACHE_TTL)
    logger.debug(f"Tool analysis cached for {cache_key[:16]}")

    return results


def format_agent_analysis(tool_results: Dict[str, str]) -> str:
    """
    格式化工具分析结果

    Args:
        tool_results: 工具分析结果字典

    Returns:
        格式化的分析报告
    """
    sections = []

    for tool_name, result in tool_results.items():
        if result and "分析失败" not in result:
            sections.append(f"\n{result}")

    return "\n".join(sections)


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/analyze", response_model=AgentAnalyzeResponse)
async def agent_analyze(
    request: AgentAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    使用 Agent 分析代码

    运行所有分析工具并返回综合报告
    """
    try:
        # 确定要使用的工具（focus_area -> tool_name 映射）
        focus_to_tool = {
            "structure": CodeToolName.ANALYZE_STRUCTURE,
            "smells": CodeToolName.DETECT_SMELLS,
            "complexity": CodeToolName.CALCULATE_COMPLEXITY,
            "security": CodeToolName.CHECK_SECURITY,
        }

        focus_areas = request.focus_areas or list(focus_to_tool.keys())
        code = request.code
        language = request.language

        results = {}

        # 使用字典访问工具，避免硬编码索引
        for area in focus_areas:
            if area == "all":
                # 并行执行所有工具
                results = await run_tool_analysis(code, language)
                break

            tool_name = focus_to_tool.get(area)
            if tool_name:
                tool = get_tool(tool_name)
                if tool:
                    try:
                        results[area] = tool.invoke({"code": code, "language": language})
                    except Exception as e:
                        results[area] = f"{area}分析失败: {str(e)}"
                        logger.error(f"Tool {tool_name} failed: {e}")

        # 使用 AI 生成综合分析
        analysis_text = format_agent_analysis(results)

        # 生成改进建议
        system_prompt = f"""你是一个专业的代码审查专家，擅长 {language} 语言。
根据以下工具分析结果，提供简洁的改进建议（最多5条）。
每条建议应该具体、可操作。"""

        user_prompt = f"""请根据以下分析结果，提供改进建议：

{analysis_text}

请提供 3-5 条具体的改进建议，每条一行，格式：
• [优先级] 建议内容"""

        ai_response = await langchain_glm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=500,
        )

        # 提取建议
        recommendations = []
        for line in ai_response.split('\n'):
            line = line.strip()
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                recommendations.append(line.lstrip('•-*').strip())

        return AgentAnalyzeResponse(
            analysis=analysis_text,
            structure=results.get("structure"),
            smells=results.get("smells"),
            complexity=results.get("complexity"),
            security=results.get("security"),
            recommendations=recommendations[:5],
        )

    except Exception as e:
        logger.error(f"Agent analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent analysis failed: {str(e)}"
        )


@router.post("/generate", response_model=AgentGenerateResponse)
async def agent_generate(
    request: AgentGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    使用 Agent 生成代码

    可以选择使用工具对生成的代码进行分析
    """
    try:
        # 构建提示词
        system_prompt = f"""你是一个专业的 {request.language} 程序员和代码生成专家。
请生成干净、注释完整、高效的 {request.language} 代码。
遵循最佳实践，注重可读性和可维护性。"""

        user_prompt = f"生成 {request.language} 代码: {request.prompt}"

        if request.context:
            user_prompt += f"\n\n上下文:\n{request.context}"

        # 生成代码
        response = await langchain_glm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2000,
        )

        # 提取代码块
        code = response
        explanation = ""

        if "```" in response:
            parts = response.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 1:  # 代码块
                    lines = part.split("\n", 1)
                    if len(lines) > 1:
                        code = lines[1]
                        if "```" in code:
                            code = code.split("```")[0]
                        break
                elif i % 2 == 0 and i > 0:
                    explanation = part.strip()

        # 如果使用工具分析
        analysis = None
        if request.use_tools:
            tool_results = await run_tool_analysis(code, request.language)
            analysis = format_agent_analysis(tool_results)

        return AgentGenerateResponse(
            code=code.strip(),
            explanation=explanation or "代码生成完成",
            analysis=analysis,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent generation failed: {str(e)}"
        )


@router.post("/review", response_model=AgentReviewResponse)
async def agent_review(
    request: AgentReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    使用 Agent 进行深度代码审查

    结合工具分析和 AI 推理，提供全面的代码审查
    """
    try:
        code = request.code
        language = request.language

        # 运行所有工具
        tool_results = await run_tool_analysis(code, language)

        # 构建审查提示词
        system_prompt = f"""你是一个专业的 {language} 代码审查专家。
请根据工具分析结果，提供全面的代码审查报告。
包括：总体评分（0-100）、摘要、关键问题、改进建议。

评分标准：
• 90-100: 优秀
• 70-89: 良好
• 50-69: 一般
• 30-49: 较差
• 0-29: 很差"""

        analysis_text = format_agent_analysis(tool_results)

        user_prompt = f"""请审查以下 {language} 代码：

```{language}
{code[:1000]}  # 限制长度
```

工具分析结果：
{analysis_text}

请提供：
1. 总体评分 (0-100)
2. 审查摘要
3. 关键问题列表
4. 改进建议"""

        # 使用 AI 进行审查
        ai_response = await langchain_glm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2000,
        )

        # 解析响应
        score = 75
        summary = ai_response
        issues = []
        suggestions = []

        lines = ai_response.split('\n')
        current_section = None

        for line in lines:
            line_lower = line.lower()

            if '评分' in line_lower or 'score' in line_lower:
                try:
                    score_str = line.split(':')[-1].strip()
                    score = int(''.join(filter(str.isdigit, score_str)))
                    score = max(0, min(100, score))
                except:
                    pass

            # 简化解析，实际项目中可以使用更复杂的解析
            if any(word in line_lower for word in ['问题', 'issue', 'bug', 'error']):
                if line.strip() and not line.startswith('#'):
                    issues.append(line.strip())

            if any(word in line_lower for word in ['建议', 'suggest', 'improve', 'recommend']):
                if line.strip() and not line.startswith('#'):
                    suggestions.append(line.strip())

        # 提取安全问题
        security_issues = []
        if "security" in tool_results:
            security_text = tool_results["security"]
            if "🔴" in security_text or "🟠" in security_text:
                for line in security_text.split('\n'):
                    if line.strip().startswith('🔴') or line.strip().startswith('🟠'):
                        security_issues.append(line.strip())

        return AgentReviewResponse(
            overall_score=score,
            summary=summary[:500],  # 限制长度
            structure=tool_results.get("structure"),
            issues=issues[:10],
            suggestions=suggestions[:10],
            security_issues=security_issues[:5],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent review failed: {str(e)}"
        )


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: AgentChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    与 Agent 进行对话

    支持多轮对话，自动提取代码块，智能调用分析工具
    """
    try:
        # Build and compress conversation history
        conversation = []
        for msg in request.history:
            conversation.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Compress and truncate history to control tokens
        compressed_history = conversation_manager.prepare_for_llm(
            conversation,
            max_tokens=3000  # Leave room for response
        )

        # 检测用户消息中的代码块
        code_blocks_in_message = []
        code_pattern = r'```(\w*)\n([\s\S]*?)```'
        for match in re.finditer(code_pattern, request.message):
            lang = match.group(1) or request.language
            code = match.group(2)
            code_blocks_in_message.append({"language": lang, "code": code})

        # 工具调用结果
        tool_results = []
        message_lower = request.message.lower()

        # 如果消息中有代码，自动进行基础分析
        for code_block in code_blocks_in_message[:2]:  # 最多分析2个代码块
            code = code_block["code"]
            lang = code_block["language"]

            # 检测用户意图，决定调用哪些工具（使用字典访问工具）
            # 安全检查关键词
            if any(kw in message_lower for kw in ["安全", "漏洞", "security", "vulnerability", "风险"]):
                tool = get_tool(CodeToolName.CHECK_SECURITY)
                if tool:
                    try:
                        result = tool.invoke({"code": code, "language": lang})
                        tool_results.append(f"🔒 安全分析:\n{result}")
                    except Exception as e:
                        logger.warning(f"Security check failed: {e}")

            # 代码坏味道检测
            elif any(kw in message_lower for kw in ["坏味道", "重构", "smell", "refactor", "优化"]):
                tool = get_tool(CodeToolName.DETECT_SMELLS)
                if tool:
                    try:
                        result = tool.invoke({"code": code, "language": lang})
                        tool_results.append(f"🔍 代码质量:\n{result}")
                    except Exception as e:
                        logger.warning(f"Smell detection failed: {e}")

            # 结构分析（默认对较长代码执行）
            elif len(code.split('\n')) > 10:
                tool = get_tool(CodeToolName.ANALYZE_STRUCTURE)
                if tool:
                    try:
                        result = tool.invoke({"code": code, "language": lang})
                        tool_results.append(f"📊 结构分析:\n{result}")
                    except Exception as e:
                        logger.warning(f"Structure analysis failed: {e}")

        # 语义搜索关键词
        search_keywords = ["搜索", "查找", "找", "search", "find", "查询", "query"]
        if any(kw in message_lower for kw in search_keywords) and not code_blocks_in_message:
            # 提取搜索查询
            search_query = request.message
            for kw in search_keywords:
                search_query = search_query.replace(kw, "").strip()
            if len(search_query) > 3:
                tool = get_tool(CodeToolName.SEARCH_SEMANTIC)
                if tool:
                    try:
                        result = tool.invoke({
                            "query": search_query,
                            "project_id": 1,
                            "top_k": 5
                        })
                        tool_results.append(f"🔎 语义搜索:\n{result}")
                    except Exception as e:
                        logger.warning(f"Semantic search failed: {e}")

        # 构建系统提示词
        system_prompt = f"""你是一个专业的编程助手，精通 {request.language} 语言。
提供清晰、准确的答案。
显示代码时使用 markdown 代码块。

如果提供了工具分析结果，请基于这些结果给出建议。"""

        # 如果有工具结果，添加到用户消息
        enhanced_message = request.message
        if tool_results:
            enhanced_message += "\n\n---\n📊 自动分析结果:\n" + "\n\n".join(tool_results)

        # 调用 AI
        response = await langchain_glm_service.chat_with_history(
            user_message=enhanced_message,
            history=compressed_history,  # Use compressed history
            system_prompt=system_prompt,
        )

        # 提取代码块
        code_blocks = []
        if "```" in response:
            parts = response.split("```")
            for i, part in enumerate(parts[1::2]):
                lines = part.split('\n')
                if len(lines) > 1:
                    lang = lines[0].strip()
                    code = '\n'.join(lines[1:])
                    code_blocks.append({
                        "language": lang,
                        "code": code
                    })

        return AgentChatResponse(
            response=response,
            code_blocks=code_blocks,
        )

    except Exception as e:
        logger.error(f"Agent chat failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent chat failed: {str(e)}"
        )


@router.get("/tools")
async def list_tools(
    current_user: User = Depends(get_current_user),
):
    """
    列出所有可用的 Agent 工具
    """
    return {
        "tools": [
            {
                "name": name,
                "description": desc,
            }
            for name, desc in tool_descriptions.items()
        ]
    }
