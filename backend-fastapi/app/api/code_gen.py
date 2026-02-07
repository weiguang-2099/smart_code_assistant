"""
Code generation API routes using LangChain + GLM AI model.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.schemas.code_gen import (
    CodeGenRequest,
    CodeGenResponse,
    CodeReviewRequest,
    CodeReviewResponse,
    ChatRequest,
    ChatResponse,
)
from app.models.user import User
# 使用 LangChain GLM 服务替代原生 SDK
from app.services.langchain_glm_service import langchain_glm_service

router = APIRouter()


@router.post("/generate", response_model=CodeGenResponse)
async def generate_code(
    request: CodeGenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate code using AI based on user prompt.

    Args:
        request: Code generation request
        current_user: Current authenticated user
        db: Database session

    Returns:
        CodeGenResponse: Generated code with explanation
    """
    try:
        # Build the prompt for AI
        system_prompt = f"""You are an expert programmer and code assistant.
Generate clean, well-commented, and efficient {request.language} code.
Focus on best practices, readability, and maintainability."""

        user_prompt = f"Generate {request.language} code for: {request.prompt}"

        if request.context:
            user_prompt += f"\n\nContext:\n{request.context}"

        # Call LangChain GLM service
        response = await langchain_glm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=request.max_tokens,
        )

        # Parse the response
        # The AI response may contain both code and explanation
        code = response
        explanation = None

        # Try to separate code from explanation
        if "```" in response:
            # Extract code from markdown code blocks
            parts = response.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 1:  # Code block
                    lines = part.split("\n", 1)
                    if len(lines) > 1:
                        code = lines[1]
                        if "```" in code:
                            code = code.split("```")[0]
                elif i % 2 == 0 and i > 0:  # Explanation after code
                    explanation = part.strip()
                    break
        else:
            # No markdown blocks, use entire response as code
            code = response

        return CodeGenResponse(
            code=code.strip(),
            language=request.language,
            explanation=explanation,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code generation failed: {str(e)}"
        )


@router.post("/review", response_model=CodeReviewResponse)
async def review_code(
    request: CodeReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Review code using AI and provide suggestions.

    Args:
        request: Code review request
        current_user: Current authenticated user
        db: Database session

    Returns:
        CodeReviewResponse: Code review with score, issues, and suggestions
    """
    try:
        # Build the review prompt
        focus_str = ""
        if request.focus_areas:
            focus_str = f" Focus on: {', '.join(request.focus_areas)}."

        system_prompt = f"""You are an expert code reviewer specializing in {request.language}.
Analyze the code for bugs, security issues, performance problems, and best practices.{focus_str}
Provide a score from 0-100, list specific issues, and suggest improvements."""

        user_prompt = f"Review this {request.language} code:\n\n```{request.language}\n{request.code}\n```"

        # Call LangChain GLM service
        response = await langchain_glm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2000,
        )

        # Parse the response to extract structured review
        # This is a simplified parser - in production you'd want more robust parsing
        lines = response.split("\n")

        score = 75  # Default score
        issues = []
        suggestions = []

        for line in lines:
            line_lower = line.lower()
            if "score" in line_lower or "rating" in line_lower:
                try:
                    score_str = line.split(":")[-1].strip()
                    score = int("".join(filter(str.isdigit, score_str)))
                    score = max(0, min(100, score))
                except:
                    pass
            elif any(word in line_lower for word in ["issue", "problem", "bug", "error", "vulnerability"]):
                if line.strip():
                    issues.append(line.strip())
            elif any(word in line_lower for word in ["suggest", "improve", "better", "consider", "recommend"]):
                if line.strip():
                    suggestions.append(line.strip())

        # If no structured response, add the full response as suggestions
        if not issues and not suggestions:
            suggestions.append(response)

        return CodeReviewResponse(
            overall_score=score,
            issues=issues[:10],  # Limit to top 10 issues
            suggestions=suggestions[:10],  # Limit to top 10 suggestions
            improved_code=None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code review failed: {str(e)}"
        )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with AI assistant for code-related questions.

    Args:
        request: Chat request with conversation history
        current_user: Current authenticated user
        db: Database session

    Returns:
        ChatResponse: Assistant's response
    """
    try:
        # Build conversation from history
        conversation = []
        for msg in request.messages:
            if msg.role == "user":
                conversation.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                conversation.append({"role": "assistant", "content": msg.content})

        # System prompt
        system_prompt = f"""You are a helpful coding assistant specializing in {request.language}.
Provide clear, accurate, and concise answers.
When showing code, use markdown code blocks with the appropriate language tag."""

        # Get the last user message
        last_user_msg = request.messages[-1].content if request.messages else ""

        # Call LangChain GLM service
        response = await langchain_glm_service.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                *conversation
            ],
            max_tokens=1500,
        )

        # Extract code from response if present
        code = None
        language = None

        if "```" in response:
            for block in response.split("```")[1::2]:
                lines = block.split("\n")
                if len(lines) > 1:
                    # First line might be the language
                    potential_lang = lines[0].strip()
                    if potential_lang and potential_lang.isalpha():
                        language = potential_lang
                    code = "\n".join(lines[1:])
                    break

        return ChatResponse(
            message=response,
            code=code,
            language=language or request.language,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )
