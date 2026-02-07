"""
Code file API routes for managing code files within projects.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.deps import get_current_user
from app.schemas.code_file import (
    CodeFileCreate,
    CodeFileUpdate,
    CodeFileResponse,
    CodeFileDetail,
)
from app.models.user import User
from app.models.project import Project
from app.models.code_file import CodeFile

router = APIRouter()


async def verify_project_access(project_id: int, user_id: int, db: AsyncSession) -> Project:
    """Verify user has access to the project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if project.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return project


@router.post("", response_model=CodeFileResponse, status_code=status.HTTP_201_CREATED)
async def create_code_file(
    file_data: CodeFileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new code file in a project.

    Args:
        file_data: Code file creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        CodeFileResponse: Created code file
    """
    # Verify project access
    await verify_project_access(file_data.project_id, current_user.id, db)

    # Create new code file
    new_file = CodeFile(
        filename=file_data.filename,
        path=file_data.path,
        language=file_data.language,
        content=file_data.content,
        project_id=file_data.project_id,
    )

    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)

    return CodeFileResponse.model_validate(new_file)


@router.get("", response_model=List[CodeFileResponse])
async def list_code_files(
    project_id: int = Query(..., description="Project ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all code files in a project.

    Args:
        project_id: Project ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        List[CodeFileResponse]: List of code files
    """
    # Verify project access
    await verify_project_access(project_id, current_user.id, db)

    # Get files
    result = await db.execute(
        select(CodeFile)
        .where(CodeFile.project_id == project_id)
        .order_by(CodeFile.path, CodeFile.filename)
    )
    files = result.scalars().all()

    return [CodeFileResponse.model_validate(f) for f in files]


@router.get("/{file_id}", response_model=CodeFileDetail)
async def get_code_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific code file by ID.

    Args:
        file_id: Code file ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        CodeFileDetail: Code file details
    """
    # Get file with project
    result = await db.execute(
        select(CodeFile)
        .options(selectinload(CodeFile.project))
        .where(CodeFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code file not found"
        )

    # Check project ownership
    if file.project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return CodeFileDetail(
        id=file.id,
        filename=file.filename,
        path=file.path,
        language=file.language,
        content=file.content,
        project_id=file.project_id,
        created_at=file.created_at,
        updated_at=file.updated_at,
        full_path=file.full_path,
        owner_id=file.project.owner_id,
        project_name=file.project.name,
    )


@router.put("/{file_id}", response_model=CodeFileResponse)
async def update_code_file(
    file_id: int,
    file_update: CodeFileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a code file.

    Args:
        file_id: Code file ID
        file_update: Code file update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        CodeFileResponse: Updated code file
    """
    # Get file with project
    result = await db.execute(
        select(CodeFile)
        .options(selectinload(CodeFile.project))
        .where(CodeFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code file not found"
        )

    # Check project ownership
    if file.project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update fields
    if file_update.filename is not None:
        file.filename = file_update.filename
    if file_update.path is not None:
        file.path = file_update.path
    if file_update.language is not None:
        file.language = file_update.language
    if file_update.content is not None:
        file.content = file_update.content

    await db.commit()
    await db.refresh(file)

    return CodeFileResponse.model_validate(file)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_code_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a code file.

    Args:
        file_id: Code file ID
        current_user: Current authenticated user
        db: Database session
    """
    # Get file with project
    result = await db.execute(
        select(CodeFile)
        .options(selectinload(CodeFile.project))
        .where(CodeFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code file not found"
        )

    # Check project ownership
    if file.project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Delete file
    await db.execute(delete(CodeFile).where(CodeFile.id == file_id))
    await db.commit()
