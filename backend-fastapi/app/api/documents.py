"""
Document API routes for managing user documents with version control.
"""
import re
from datetime import datetime
from types import SimpleNamespace
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.deps import get_current_user
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentDetail,
    DocumentListResponse,
    VersionCreate,
    VersionResponse,
    VersionListItem,
    OutlineItem,
    DocumentOutlineResponse,
)
from app.models.user import User
from app.models.document import Document, RawVersion

router = APIRouter()


# ==================== Helper Functions ====================

async def generate_document_number(db: AsyncSession, user_id: int) -> str:
    """Generate a unique document number in format DOC-YYYYMMDD-NNN."""
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"DOC-{today}-"

    # Find the highest number for today
    result = await db.execute(
        select(Document.document_number)
        .where(Document.user_id == user_id, Document.document_number.like(f"{prefix}%"))
        .order_by(Document.document_number.desc())
        .limit(1)
    )
    last_number = result.scalar_one_or_none()

    if last_number:
        try:
            seq = int(last_number.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1

    return f"{prefix}{seq:03d}"


def extract_outline_from_markdown(markdown: str) -> List[OutlineItem]:
    """Extract outline from markdown content."""
    lines = markdown.split("\n")
    headings = []

    for i, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            # Generate anchor from text
            anchor = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text.lower()).strip("-")
            anchor = anchor[:50] or f"heading-{i}"
            headings.append(OutlineItem(
                level=level,
                text=text,
                anchor=anchor,
                line_number=i + 1,
                children=[],
            ))

    # Build tree structure
    return build_outline_tree(headings)


def build_outline_tree(headings: List[OutlineItem]) -> List[OutlineItem]:
    """Build a tree structure from flat heading list."""
    if not headings:
        return []

    # Sentinel root: a plain holder, not an OutlineItem (whose schema requires
    # level >= 1). Only its `.level` and `.children` are used by the algorithm.
    root = SimpleNamespace(level=0, children=[])
    stack = [root]

    for heading in headings:
        # Find parent (last heading with lower level)
        while stack[-1].level >= heading.level:
            stack.pop()

        stack[-1].children.append(heading)
        stack.append(heading)

    return root.children


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router is working."""
    return {"message": "Documents router is working"}


# ==================== Document CRUD ====================

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new document for the current user.

    Args:
        document_data: Document creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        DocumentResponse: Created document
    """
    # Generate document number
    document_number = await generate_document_number(db, current_user.id)

    # Create new document
    new_document = Document(
        user_id=current_user.id,
        title=document_data.title,
        document_number=document_number,
        description=document_data.description,
        category=document_data.category,
        project_id=document_data.project_id,
    )

    db.add(new_document)
    await db.commit()
    await db.refresh(new_document)

    return DocumentResponse(
        id=new_document.id,
        user_id=new_document.user_id,
        document_number=new_document.document_number,
        title=new_document.title,
        description=new_document.description,
        category=new_document.category,
        project_id=new_document.project_id,
        current_version_id=new_document.current_version_id,
        is_published=new_document.is_published,
        version_count=0,
        created_at=new_document.created_at,
        updated_at=new_document.updated_at,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    sort_by: str = Query("updated_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all documents for the current user with pagination and filtering.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        category: Filter by category
        project_id: Filter by project ID
        search: Search in title and description
        sort_by: Sort field
        sort_order: Sort order (asc/desc)
        current_user: Current authenticated user
        db: Database session

    Returns:
        DocumentListResponse: Paginated list of documents
    """
    # Build base query
    base_filters = [Document.user_id == current_user.id]

    if category:
        base_filters.append(Document.category == category)
    if project_id is not None:
        base_filters.append(Document.project_id == project_id)
    if search:
        base_filters.append(
            or_(
                Document.title.ilike(f"%{search}%"),
                Document.description.ilike(f"%{search}%"),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(Document).where(*base_filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Build sort order
    sort_column = getattr(Document, sort_by, Document.updated_at)
    if sort_order == "asc":
        order_by = sort_column.asc()
    else:
        order_by = sort_column.desc()

    # Get documents
    offset = (page - 1) * page_size
    documents_query = (
        select(Document)
        .where(*base_filters)
        .order_by(order_by)
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(documents_query)
    documents = result.scalars().all()

    # Build response with version counts
    document_responses = []
    for doc in documents:
        # Count versions
        version_count_query = select(func.count()).select_from(RawVersion).where(
            RawVersion.document_id == doc.id
        )
        version_count_result = await db.execute(version_count_query)
        version_count = version_count_result.scalar() or 0

        document_responses.append(
            DocumentResponse(
                id=doc.id,
                user_id=doc.user_id,
                document_number=doc.document_number,
                title=doc.title,
                description=doc.description,
                category=doc.category,
                project_id=doc.project_id,
                current_version_id=doc.current_version_id,
                is_published=doc.is_published,
                version_count=version_count,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
        )

    total_pages = (total + page_size - 1) // page_size

    return DocumentListResponse(
        items=document_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific document by ID with its current version and version history.

    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        DocumentDetail: Document details with versions

    Raises:
        HTTPException: If document not found or access denied
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

    # Check ownership
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

    # Build version list
    version_list = []
    current_version_response = None

    for version in versions:
        # Get creator username
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

        # Get current version details
        if document.current_version_id == version.id:
            current_version_response = VersionResponse(
                id=version.id,
                document_id=version.document_id,
                version_number=version.version_number,
                markdown_content=version.markdown_content,
                tiptap_content=version.tiptap_content or {},
                change_summary=version.change_summary,
                source_type=version.source_type,
                created_by=version.created_by,
                created_at=version.created_at,
            )

    return DocumentDetail(
        id=document.id,
        user_id=document.user_id,
        document_number=document.document_number,
        title=document.title,
        description=document.description,
        category=document.category,
        project_id=document.project_id,
        current_version_id=document.current_version_id,
        is_published=document.is_published,
        version_count=len(versions),
        created_at=document.created_at,
        updated_at=document.updated_at,
        current_version=current_version_response,
        versions=version_list,
    )


@router.patch("/{document_id}/metadata", response_model=DocumentResponse)
async def update_document_metadata(
    document_id: int,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update document metadata (title, description, category).

    Args:
        document_id: Document ID
        document_update: Document update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        DocumentResponse: Updated document

    Raises:
        HTTPException: If document not found or access denied
    """
    # Get document
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check ownership
    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update fields
    if document_update.title is not None:
        document.title = document_update.title
    if document_update.description is not None:
        document.description = document_update.description
    if document_update.category is not None:
        document.category = document_update.category

    await db.commit()
    await db.refresh(document)

    # Count versions
    version_count_query = select(func.count()).select_from(RawVersion).where(
        RawVersion.document_id == document.id
    )
    version_count_result = await db.execute(version_count_query)
    version_count = version_count_result.scalar() or 0

    return DocumentResponse(
        id=document.id,
        user_id=document.user_id,
        document_number=document.document_number,
        title=document.title,
        description=document.description,
        category=document.category,
        project_id=document.project_id,
        current_version_id=document.current_version_id,
        is_published=document.is_published,
        version_count=version_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.put("/{document_id}", response_model=VersionResponse)
async def update_document_content(
    document_id: int,
    version_data: VersionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update document content by creating a new version.

    Args:
        document_id: Document ID
        version_data: New version data
        current_user: Current authenticated user
        db: Database session

    Returns:
        VersionResponse: Newly created version

    Raises:
        HTTPException: If document not found or access denied
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

    # Check ownership
    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get next version number
    count_query = select(func.count()).select_from(RawVersion).where(
        RawVersion.document_id == document_id
    )
    count_result = await db.execute(count_query)
    next_version_number = (count_result.scalar() or 0) + 1

    # Create new version
    new_version = RawVersion(
        document_id=document.id,
        version_number=next_version_number,
        markdown_content=version_data.markdown_content,
        tiptap_content=version_data.tiptap_content or {},
        source_type=version_data.source_type,
        change_summary=version_data.change_summary,
        created_by=current_user.id,
    )

    db.add(new_version)
    await db.flush()  # Get the new version ID

    # Update document's current version
    document.current_version_id = new_version.id

    await db.commit()
    await db.refresh(new_version)

    return VersionResponse(
        id=new_version.id,
        document_id=new_version.document_id,
        version_number=new_version.version_number,
        markdown_content=new_version.markdown_content,
        tiptap_content=new_version.tiptap_content,
        change_summary=new_version.change_summary,
        source_type=new_version.source_type,
        created_by=new_version.created_by,
        created_at=new_version.created_at,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a document and all its versions.

    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If document not found or access denied
    """
    # Get document
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check ownership
    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Delete document (cascade will delete versions)
    await db.execute(delete(Document).where(Document.id == document_id))
    await db.commit()


# ==================== Document Outline ====================

@router.get("/{document_id}/outline", response_model=DocumentOutlineResponse)
async def get_document_outline(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract and return the outline (table of contents) from a document's current version.

    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        DocumentOutlineResponse: Document outline with nested headings

    Raises:
        HTTPException: If document not found, access denied, or no content
    """
    # Get document with current version
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

    if not document.current_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document has no content"
        )

    # Extract outline from markdown content
    outline = extract_outline_from_markdown(document.current_version.markdown_content)

    return DocumentOutlineResponse(
        document_id=document_id,
        outline=outline,
    )
