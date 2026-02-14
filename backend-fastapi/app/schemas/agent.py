"""
Agent schemas for request and response validation.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class AgentStatus(str, Enum):
    """Agent status enum."""
    draft = "draft"
    active = "active"
    inactive = "inactive"
    training = "training"


class TrainingStatus(str, Enum):
    """Training task status enum."""
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


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
