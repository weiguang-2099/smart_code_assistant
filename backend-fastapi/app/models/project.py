"""
Project model for organizing code files.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Project(Base):
    """
    Project model representing a code project/workspace.

    Attributes:
        id: Primary key
        name: Project name
        description: Project description (optional)
        owner_id: Foreign key to users table
        created_at: Project creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="projects")
    code_files = relationship("CodeFile", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"
