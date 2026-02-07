"""
Version API routes for document version management.
"""
import difflib
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.deps import get_current_user
from app.schemas.document import (
    VersionResponse,
    VersionListItem,
    VersionCompareResponse,
    VersionRollbackRequest,
    VersionRollbackResponse,
)
from app.models.user import User
from app.models.document import Document, RawVersion

router = APIRouter()


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router is working."""
    return {"message": "Versions router is working"}


# ==================== Version List ====================

@router.get("/documents/{document_id}/versions", response_model=List[VersionListItem])
async def list_versions(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all versions of a document.

    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        List[VersionListItem]: List of versions

    Raises:
        HTTPException: If document not found or access denied
    """
    # Verify document exists and user has access
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get all versions
    versions_result = await db.execute(
        select(RawVersion)
        .where(RawVersion.document_id == document_id)
        .order_by(RawVersion.version_number.desc())
    )
    versions = versions_result.scalars().all()

    # Build version list with creator usernames
    version_list = []
    for version in versions:
        creator_result = await db.execute(
            select(User).where(User.id == version.created_by)
        )
        creator = creator_result.scalar_one_or_none()

        version_list.append(
            VersionListItem(
                id=version.id,
                document_id=version.document_id,
                version_number=version.version_number,
                change_summary=version.change_summary,
                source_type=version.source_type,
                created_by=version.created_by,
                created_by_username=creator.username if creator else None,
                created_at=version.created_at,
            )
        )

    return version_list


# ==================== Get Specific Version ====================

@router.get("/documents/{document_id}/versions/{version_id}", response_model=VersionResponse)
async def get_version(
    document_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific version of a document.

    Args:
        document_id: Document ID
        version_id: Version ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        VersionResponse: Version details

    Raises:
        HTTPException: If document/version not found or access denied
    """
    # Verify document exists and user has access
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get version
    version_result = await db.execute(
        select(RawVersion).where(
            RawVersion.id == version_id,
            RawVersion.document_id == document_id
        )
    )
    version = version_result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    return VersionResponse(
        id=version.id,
        document_id=version.document_id,
        version_number=version.version_number,
        markdown_content=version.markdown_content,
        tiptap_content=version.tiptap_content,
        change_summary=version.change_summary,
        source_type=version.source_type,
        created_by=version.created_by,
        created_at=version.created_at,
    )


# ==================== Version Compare ====================

@router.get("/documents/{document_id}/versions/compare", response_model=VersionCompareResponse)
async def compare_versions(
    document_id: int,
    from_version: int = Query(..., description="From version ID"),
    to_version: int = Query(..., description="To version ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare two versions of a document.

    Args:
        document_id: Document ID
        from_version: Source version ID
        to_version: Target version ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        VersionCompareResponse: Version comparison with diff

    Raises:
        HTTPException: If document/version not found or access denied
    """
    # Verify document exists and user has access
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get both versions
    versions_result = await db.execute(
        select(RawVersion).where(
            RawVersion.id.in_([from_version, to_version]),
            RawVersion.document_id == document_id
        )
    )
    versions = versions_result.scalars().all()

    if len(versions) != 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both versions not found"
        )

    # Create version map
    version_map = {v.id: v for v in versions}

    from_ver = version_map[from_version]
    to_ver = version_map[to_version]

    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        from_ver.markdown_content.splitlines(keepends=True),
        to_ver.markdown_content.splitlines(keepends=True),
        fromfile=f"Version {from_ver.version_number}",
        tofile=f"Version {to_ver.version_number}",
        lineterm=""
    ))
    diff = "".join(diff_lines)

    return VersionCompareResponse(
        from_version=VersionResponse(
            id=from_ver.id,
            document_id=from_ver.document_id,
            version_number=from_ver.version_number,
            markdown_content=from_ver.markdown_content,
            tiptap_content=from_ver.tiptap_content,
            change_summary=from_ver.change_summary,
            source_type=from_ver.source_type,
            created_by=from_ver.created_by,
            created_at=from_ver.created_at,
        ),
        to_version=VersionResponse(
            id=to_ver.id,
            document_id=to_ver.document_id,
            version_number=to_ver.version_number,
            markdown_content=to_ver.markdown_content,
            tiptap_content=to_ver.tiptap_content,
            change_summary=to_ver.change_summary,
            source_type=to_ver.source_type,
            created_by=to_ver.created_by,
            created_at=to_ver.created_at,
        ),
        diff=diff,
    )


# ==================== Version Rollback ====================

@router.post("/documents/{document_id}/rollback", response_model=VersionRollbackResponse)
async def rollback_to_version(
    document_id: int,
    rollback_data: VersionRollbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Rollback a document to a specific version by creating a new version with that content.

    Args:
        document_id: Document ID
        rollback_data: Rollback request data
        current_user: Current authenticated user
        db: Database session

    Returns:
        VersionRollbackResponse: Newly created version after rollback

    Raises:
        HTTPException: If document/version not found or access denied
    """
    # Get document
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.current_version))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get target version
    target_version_result = await db.execute(
        select(RawVersion).where(
            RawVersion.id == rollback_data.version_id,
            RawVersion.document_id == document_id
        )
    )
    target_version = target_version_result.scalar_one_or_none()

    if not target_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target version not found"
        )

    # Get next version number
    count_query = select(func.count()).select_from(RawVersion).where(
        RawVersion.document_id == document_id
    )
    count_result = await db.execute(count_query)
    next_version_number = (count_result.scalar() or 0) + 1

    # Create new version with content from target version
    new_version = RawVersion(
        document_id=document.id,
        version_number=next_version_number,
        markdown_content=target_version.markdown_content,
        tiptap_content=target_version.tiptap_content,
        source_type="manual",
        change_summary=rollback_data.change_summary or f"Rollback to version {target_version.version_number}",
        created_by=current_user.id,
    )

    db.add(new_version)
    await db.flush()

    # Update document's current version
    document.current_version_id = new_version.id

    await db.commit()
    await db.refresh(new_version)

    return VersionRollbackResponse(
        new_version_id=new_version.id,
        version_number=new_version.version_number,
        message=f"Successfully rolled back to version {target_version.version_number}",
    )
