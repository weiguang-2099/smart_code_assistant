"""
CodeFile model for storing code snippets and files.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class CodeFile(Base):
    """
    CodeFile model representing individual code files within a project.

    Attributes:
        id: Primary key
        filename: File name with extension
        path: File path within project (e.g., 'src/utils/helpers.js')
        language: Programming language (javascript, python, etc.)
        content: File content/code
        project_id: Foreign key to projects table
        created_at: File creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "code_files"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False, default="")
    language = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False, default="")
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="code_files")

    def __repr__(self) -> str:
        return f"<CodeFile(id={self.id}, filename='{self.filename}', path='{self.path}')>"

    @property
    def full_path(self) -> str:
        """Get the full path including filename."""
        if self.path:
            return f"{self.path}/{self.filename}" if not self.path.endswith('/') else f"{self.path}{self.filename}"
        return self.filename
