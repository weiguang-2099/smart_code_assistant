"""
Code generation schemas for request and response validation.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


# Schema for code generation request
class CodeGenRequest(BaseModel):
    """Schema for code generation request."""
    prompt: str = Field(..., min_length=1, description="User prompt describing what code to generate")
    language: str = Field("python", description="Programming language for the generated code")
    context: Optional[str] = Field(None, description="Additional context or existing code")
    max_tokens: Optional[int] = Field(2000, description="Maximum tokens to generate")


# Schema for code generation response
class CodeGenResponse(BaseModel):
    """Schema for code generation response."""
    code: str = Field(..., description="Generated code")
    language: str = Field(..., description="Programming language of the generated code")
    explanation: Optional[str] = Field(None, description="Explanation of the generated code")


# Schema for code review request
class CodeReviewRequest(BaseModel):
    """Schema for code review request."""
    code: str = Field(..., min_length=1, description="Code to review")
    language: str = Field(..., description="Programming language")
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas to focus on (e.g., 'security', 'performance')")


# Schema for code review response
class CodeReviewResponse(BaseModel):
    """Schema for code review response."""
    overall_score: int = Field(..., ge=0, le=100, description="Overall code quality score")
    issues: List[str] = Field(default_factory=list, description="List of issues found")
    suggestions: List[str] = Field(default_factory=list, description="List of suggestions")
    improved_code: Optional[str] = Field(None, description="Suggested improved version of the code")


# Schema for chat message
class ChatMessage(BaseModel):
    """Schema for chat message in code generation."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


# Schema for chat request
class ChatRequest(BaseModel):
    """Schema for chat request with conversation history."""
    messages: List[ChatMessage] = Field(..., min_items=1, description="Conversation history")
    language: Optional[str] = Field("python", description="Target programming language")


# Schema for chat response
class ChatResponse(BaseModel):
    """Schema for chat response."""
    message: str = Field(..., description="Assistant's response")
    code: Optional[str] = Field(None, description="Generated code if any")
    language: Optional[str] = Field(None, description="Language of the generated code")
