"""
Project API routes for managing code projects.
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import (
    ProjectNotFoundException,
    ForbiddenException,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetail,
    ProjectListResponse,
)
from app.models.user import User
from app.models.project import Project
from app.models.code_file import CodeFile

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new project for the current user.

    Args:
        project_data: Project creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        ProjectResponse: Created project
    """
    # Create new project
    new_project = Project(
        name=project_data.name,
        description=project_data.description,
        owner_id=current_user.id,
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    return ProjectResponse(
        id=new_project.id,
        name=new_project.name,
        description=new_project.description,
        owner_id=new_project.owner_id,
        created_at=new_project.created_at,
        updated_at=new_project.updated_at,
        file_count=0,
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all projects for the current user with pagination.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        current_user: Current authenticated user
        db: Database session

    Returns:
        ProjectListResponse: Paginated list of projects
    """
    # Get total count
    count_query = select(func.count()).select_from(Project).where(
        Project.owner_id == current_user.id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get projects
    offset = (page - 1) * page_size
    projects_query = (
        select(Project)
        .where(Project.owner_id == current_user.id)
        .order_by(Project.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(projects_query)
    projects = result.scalars().all()

    # Build response with file counts
    project_responses = []
    for project in projects:
        # Get file count for each project
        file_count_query = select(func.count()).select_from(CodeFile).where(
            CodeFile.project_id == project.id
        )
        file_count_result = await db.execute(file_count_query)
        file_count = file_count_result.scalar() or 0

        project_responses.append(
            ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                owner_id=project.owner_id,
                created_at=project.created_at,
                updated_at=project.updated_at,
                file_count=file_count,
            )
        )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return ProjectListResponse(
        projects=project_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific project by ID.

    Args:
        project_id: Project ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        ProjectDetail: Project details

    Raises:
        ProjectNotFoundException: If project not found
        ForbiddenException: If access denied
    """
    # Get project with owner and files
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.owner))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise ProjectNotFoundException(project_id=project_id)

    # Check ownership
    if project.owner_id != current_user.id:
        raise ForbiddenException(message="You don't have access to this project")

    # Get files for the project
    files_result = await db.execute(
        select(CodeFile)
        .where(CodeFile.project_id == project_id)
        .order_by(CodeFile.path, CodeFile.filename)
    )
    files = files_result.scalars().all()

    return ProjectDetail(
        id=project.id,
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
        owner_username=project.owner.username if project.owner else None,
        created_at=project.created_at,
        updated_at=project.updated_at,
        file_count=len(files),
        files=[
            {
                "id": f.id,
                "filename": f.filename,
                "path": f.path,
                "language": f.language,
                "full_path": f.full_path if hasattr(f, 'full_path') else f"{f.path}/{f.filename}" if f.path else f.filename,
                "created_at": f.created_at.isoformat(),
                "updated_at": f.updated_at.isoformat(),
            }
            for f in files
        ],
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a project.

    Args:
        project_id: Project ID
        project_update: Project update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        ProjectResponse: Updated project

    Raises:
        ProjectNotFoundException: If project not found
        ForbiddenException: If access denied
    """
    # Get project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise ProjectNotFoundException(project_id=project_id)

    # Check ownership
    if project.owner_id != current_user.id:
        raise ForbiddenException(message="You don't have access to this project")

    # Update fields
    if project_update.name is not None:
        project.name = project_update.name
    if project_update.description is not None:
        project.description = project_update.description

    await db.commit()
    await db.refresh(project)

    # Get file count
    file_count_query = select(func.count()).select_from(CodeFile).where(
        CodeFile.project_id == project.id
    )
    file_count_result = await db.execute(file_count_query)
    file_count = file_count_result.scalar() or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        file_count=file_count,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a project and all its files.

    Args:
        project_id: Project ID
        current_user: Current authenticated user
        db: Database session

    Raises:
        ProjectNotFoundException: If project not found
        ForbiddenException: If access denied
    """
    # Get project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise ProjectNotFoundException(project_id=project_id)

    # Check ownership
    if project.owner_id != current_user.id:
        raise ForbiddenException(message="You don't have access to this project")

    # Delete project (cascade will delete files)
    await db.execute(delete(Project).where(Project.id == project_id))
    await db.commit()
