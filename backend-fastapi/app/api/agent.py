"""
AI Agent API Routes - LangChain Agent 端点

提供基于 LangChain 的智能 Agent 服务，支持代码生成、审查、分析等功能
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.langchain_glm_service import langchain_glm_service
from app.services.code_tools import langchain_tools

router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class AgentAnalyzeRequest(BaseModel):
    """Agent 代码分析请求"""
    code: str = Field(..., description="要分析的代码")
    language: str = Field(default="python", description="编程语言")
    focus_areas: Optional[List[str]] = Field(
        default=None,
        description="关注领域: structure, smells, complexity, security, all"
    )


class AgentAnalyzeResponse(BaseModel):
    """Agent 代码分析响应"""
    analysis: str = Field(..., description="分析结果")
    structure: Optional[str] = Field(None, description="代码结构")
    smells: Optional[str] = Field(None, description="代码坏味道")
    complexity: Optional[str] = Field(None, description="复杂度分析")
    security: Optional[str] = Field(None, description="安全问题")
    recommendations: List[str] = Field(default_factory=list, description="改进建议")


class AgentGenerateRequest(BaseModel):
    """Agent 代码生成请求"""
    prompt: str = Field(..., description="需求描述")
    language: str = Field(default="python", description="目标编程语言")
    context: Optional[str] = Field(None, description="上下文信息")
    use_tools: bool = Field(default=False, description="是否使用工具分析")


class AgentGenerateResponse(BaseModel):
    """Agent 代码生成响应"""
    code: str = Field(..., description="生成的代码")
    explanation: str = Field(..., description="代码说明")
    analysis: Optional[str] = Field(None, description="代码分析（如果使用工具）")


class AgentReviewRequest(BaseModel):
    """Agent 代码审查请求"""
    code: str = Field(..., description="要审查的代码")
    language: str = Field(default="python", description="编程语言")
    deep_analysis: bool = Field(default=True, description="是否进行深度分析")


class AgentReviewResponse(BaseModel):
    """Agent 代码审查响应"""
    overall_score: int = Field(..., description="总体评分 (0-100)")
    summary: str = Field(..., description="审查摘要")
    structure: Optional[str] = Field(None, description="结构分析")
    issues: List[str] = Field(default_factory=list, description="发现的问题")
    suggestions: List[str] = Field(default_factory=list, description="改进建议")
    security_issues: List[str] = Field(default_factory=list, description="安全问题")
    improved_code: Optional[str] = Field(None, description="改进后的代码")


class AgentChatRequest(BaseModel):
    """Agent 聊天请求"""
    message: str = Field(..., description="用户消息")
    history: Optional[List[Dict[str, str]]] = Field(
        default_factory=list,
        description="对话历史"
    )
    language: str = Field(default="python", description="编程语言")


class AgentChatResponse(BaseModel):
    """Agent 聊天响应"""
    response: str = Field(..., description="Agent 响应")
    code_blocks: List[Dict[str, str]] = Field(
        default_factory=list,
        description="提取的代码块"
    )


# ============================================================================
# Agent 辅助函数
# ============================================================================

async def run_tool_analysis(code: str, language: str) -> Dict[str, str]:
    """
    运行所有工具进行分析

    Args:
        code: 要分析的代码
        language: 编程语言

    Returns:
        各工具的分析结果
    """
    results = {}

    for tool in langchain_tools:
        try:
            if tool.name == "search_code_pattern":
                continue  # 跳过搜索工具
            result = tool.invoke({"code": code, "language": language})
            results[tool.name] = result
        except Exception as e:
            results[tool.name] = f"分析失败: {str(e)}"

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
        # 确定要使用的工具
        focus_areas = request.focus_areas or ["structure", "smells", "complexity", "security"]

        results = {}
        code = request.code
        language = request.language

        # 运行请求的工具
        if "all" in focus_areas or "structure" in focus_areas:
            try:
                results["structure"] = langchain_tools[0].invoke({"code": code, "language": language})
            except Exception as e:
                results["structure"] = f"结构分析失败: {str(e)}"

        if "all" in focus_areas or "smells" in focus_areas:
            try:
                results["smells"] = langchain_tools[1].invoke({"code": code, "language": language})
            except Exception as e:
                results["smells"] = f"坏味道检测失败: {str(e)}"

        if "all" in focus_areas or "complexity" in focus_areas:
            try:
                results["complexity"] = langchain_tools[2].invoke({"code": code, "language": language})
            except Exception as e:
                results["complexity"] = f"复杂度分析失败: {str(e)}"

        if "all" in focus_areas or "security" in focus_areas:
            try:
                results["security"] = langchain_tools[3].invoke({"code": code, "language": language})
            except Exception as e:
                results["security"] = f"安全检测失败: {str(e)}"

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

    支持多轮对话，自动提取代码块
    """
    try:
        # 构建对话历史
        conversation = []
        for msg in request.history:
            conversation.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # 系统提示词
        system_prompt = f"""你是一个专业的编程助手，精通 {request.language} 语言。
提供清晰、准确的答案。
显示代码时使用 markdown 代码块。"""

        # 调用 AI
        response = await langchain_glm_service.chat_with_history(
            user_message=request.message,
            history=conversation,
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
    from app.services.code_tools import tool_descriptions

    return {
        "tools": [
            {
                "name": name,
                "description": tool_descriptions.get(name, ""),
            }
            for name in tool_descriptions.keys()
        ]
    }
