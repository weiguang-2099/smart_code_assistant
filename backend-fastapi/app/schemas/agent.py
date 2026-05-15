"""
Agent schemas for request and response validation.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

# Import enums from models to ensure consistency
from app.models.agent import AgentStatus, TrainingStatus


# ==================== Agent Schemas ====================

class AgentBase(BaseModel):
    """Base agent schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    domain: Optional[str] = Field(None, max_length=100, description="Agent domain/specialty")
    description: Optional[str] = Field(None, description="Agent description")


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""
    system_prompt: Optional[str] = Field(None, description="System prompt for the agent")
    config: Optional[Dict[str, Any]] = Field(None, description="Additional configuration")


class AgentUpdate(BaseModel):
    """Schema for updating agent."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Agent name")
    domain: Optional[str] = Field(None, max_length=100, description="Agent domain")
    description: Optional[str] = Field(None, description="Agent description")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar URL")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    config: Optional[Dict[str, Any]] = Field(None, description="Configuration")
    status: Optional[AgentStatus] = Field(None, description="Agent status")


class AgentStatusUpdate(BaseModel):
    """Schema for updating agent status."""
    status: AgentStatus = Field(..., description="New status")


class AgentResponse(AgentBase):
    """Schema for agent response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    avatar_url: Optional[str] = None
    status: str
    conversation_count: int = 0
    created_at: datetime
    updated_at: datetime


class AgentDetail(AgentResponse):
    """Schema for detailed agent information."""
    system_prompt: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class AgentListResponse(BaseModel):
    """Schema for paginated agent list."""
    items: List[AgentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Message Schemas ====================

class MessageBase(BaseModel):
    """Base message schema."""
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    pass


class MessageResponse(MessageBase):
    """Schema for message response."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    conversation_id: int
    tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="meta_data")
    created_at: datetime


# ==================== Conversation Schemas ====================

class ConversationBase(BaseModel):
    """Base conversation schema."""
    title: Optional[str] = Field(None, max_length=255, description="Conversation title")
    summary: Optional[str] = Field(None, description="Conversation summary")


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation."""
    agent_id: int = Field(..., description="Agent ID")


class ConversationUpdate(BaseModel):
    """Schema for updating conversation."""
    title: Optional[str] = Field(None, max_length=255, description="Conversation title")
    summary: Optional[str] = Field(None, description="Conversation summary")


class ConversationResponse(ConversationBase):
    """Schema for conversation response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    user_id: int
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationResponse):
    """Schema for detailed conversation with messages."""
    messages: List[MessageResponse] = []


class ConversationListResponse(BaseModel):
    """Schema for paginated conversation list."""
    items: List[ConversationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Training Task Schemas ====================

class TrainingTaskBase(BaseModel):
    """Base training task schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Task name")
    description: Optional[str] = Field(None, description="Task description")


class TrainingTaskCreate(TrainingTaskBase):
    """Schema for creating a new training task."""
    agent_id: int = Field(..., description="Agent ID")
    training_data: Optional[Dict[str, Any]] = Field(None, description="Training data reference")
    config: Optional[Dict[str, Any]] = Field(None, description="Training configuration")


class TrainingTaskResponse(TrainingTaskBase):
    """Schema for training task response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    user_id: int
    status: str
    progress: int
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class TrainingTaskListResponse(BaseModel):
    """Schema for paginated training task list."""
    items: List[TrainingTaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Chat Request Schemas ====================

class ChatRequest(BaseModel):
    """Schema for chat request."""
    message: str = Field(..., description="User message")
    conversation_id: Optional[int] = Field(None, description="Existing conversation ID (creates new if None)")


class ChatResponse(BaseModel):
    """Schema for chat response."""
    conversation_id: int
    message: MessageResponse


# ==================== Agent Name Suggestion Schemas ====================

class AgentNameSuggestionRequest(BaseModel):
    """Schema for agent name suggestion request."""
    domain: str = Field(..., description="Agent domain/specialty (e.g., 'code', 'writing')")
    description: Optional[str] = Field(None, description="Optional description to help generate better names")


class AgentNameSuggestionResponse(BaseModel):
    """Schema for agent name suggestion response."""
    names: List[str] = Field(..., description="List of suggested agent names")
    domain: str = Field(..., description="The domain used for generation")


# ==================== Agent Workflow Schemas ====================
# 以下 Schema 用于 Agent 代码分析、生成、审查和聊天功能

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


class StreamChatRequest(BaseModel):
    """Streaming chat request"""
    message: str = Field(..., description="User message")
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    language: str = Field(default="python")
