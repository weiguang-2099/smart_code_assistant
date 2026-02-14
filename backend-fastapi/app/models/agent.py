"""
Agent (Digital Human) models for AI assistant management.
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base


class AgentStatus(str, Enum):
    """Agent status enum."""
    draft = "draft"          # 草稿
    active = "active"        # 活跃
    inactive = "inactive"    # 停用
    training = "training"    # 训练中


class TrainingStatus(str, Enum):
    """Training task status enum."""
    pending = "pending"      # 等待中
    running = "running"      # 运行中
    completed = "completed"  # 已完成
    failed = "failed"        # 失败


class Agent(Base):
    """
    Agent (Digital Human) model for AI assistant.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table (owner)
        name: Agent name
        description: Agent description
        domain: Agent domain/specialty (code, writing, analysis, etc.)
        avatar_url: URL to agent avatar image
        status: Agent status (draft/active/inactive/training)
        system_prompt: System prompt for the agent
        config: Additional configuration parameters (JSON)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 基础信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    domain = Column(String(100), nullable=True)  # 领域: code, writing, analysis, etc.
    avatar_url = Column(String(500), nullable=True)

    # 状态
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.draft, nullable=False)

    # 配置
    system_prompt = Column(Text, nullable=True)  # 系统提示词
    config = Column(JSON, nullable=True)  # 其他配置参数

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="agents")
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")
    training_tasks = relationship("TrainingTask", back_populates="agent", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', status='{self.status}')>"


class Conversation(Base):
    """
    Conversation model for chat history.

    Attributes:
        id: Primary key
        agent_id: Foreign key to agents table
        user_id: Foreign key to users table
        title: Conversation title
        summary: Conversation summary
        message_count: Total number of messages in conversation
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)

    # 消息数量统计
    message_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, agent_id={self.agent_id}, title='{self.title}')>"


class Message(Base):
    """
    Message model for individual chat messages.

    Attributes:
        id: Primary key
        conversation_id: Foreign key to conversations table
        role: Message role (user/assistant/system)
        content: Message content
        tokens: Token count for the message
        meta_data: Additional metadata (JSON)
        created_at: Creation timestamp
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)

    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # 元数据
    tokens = Column(Integer, nullable=True)  # token 数量
    meta_data = Column(JSON, nullable=True)  # 其他元数据

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role='{self.role}', conversation_id={self.conversation_id})>"


class TrainingTask(Base):
    """
    Training task model for agent fine-tuning.

    Attributes:
        id: Primary key
        agent_id: Foreign key to agents table
        user_id: Foreign key to users table
        name: Training task name
        description: Training task description
        status: Training status (pending/running/completed/failed)
        progress: Training progress (0-100)
        training_data: Reference to training data (JSON)
        config: Training configuration (JSON)
        result: Training result (JSON)
        error_message: Error message if training failed
        started_at: Training start timestamp
        completed_at: Training completion timestamp
        created_at: Creation timestamp
    """

    __tablename__ = "training_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # 训练状态
    status = Column(SQLEnum(TrainingStatus), default=TrainingStatus.pending, nullable=False)
    progress = Column(Integer, default=0, nullable=False)  # 0-100

    # 训练配置
    training_data = Column(JSON, nullable=True)  # 训练数据引用
    config = Column(JSON, nullable=True)  # 训练配置

    # 结果
    result = Column(JSON, nullable=True)  # 训练结果
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="training_tasks")
    user = relationship("User", back_populates="training_tasks")

    def __repr__(self) -> str:
        return f"<TrainingTask(id={self.id}, name='{self.name}', status='{self.status}')>"
