"""
Database models for Smart Code Assistant.
"""
from app.models.user import User
from app.models.project import Project
from app.models.code_file import CodeFile
from app.models.document import Document, RawVersion, Attachment
from app.models.user_profile import UserProfile, UserPreference
from app.models.agent import Agent, Conversation, Message, TrainingTask, AgentStatus, TrainingStatus

__all__ = [
    "User",
    "Project",
    "CodeFile",
    "Document",
    "RawVersion",
    "Attachment",
    "UserProfile",
    "UserPreference",
    "Agent",
    "Conversation",
    "Message",
    "TrainingTask",
    "AgentStatus",
    "TrainingStatus",
]
