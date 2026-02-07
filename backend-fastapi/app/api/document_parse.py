"""
Document parsing API routes for PDF processing and format conversion.

This module handles:
- PDF upload and parsing to Markdown
- Markdown to TipTap JSON conversion
- TipTap JSON to Markdown conversion
- Document creation from parsed content
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user
from app.schemas.document import (
    PDFUploadRequest,
    PDFUploadResponse,
)
from app.models.user import User
from app.services.pdf_service import pdf_service
from app.services.format_service import format_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router is working."""
    return {"message": "Document parse router is working"}


# ==================== PDF Parsing ====================

@router.post("/parse-pdf", response_model=PDFUploadResponse)
async def parse_pdf(
    file: UploadFile = File(...),
    title: str = None,
    description: str = None,
    category: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Parse PDF file and convert to Markdown with TipTap JSON.

    This endpoint accepts a PDF file, parses it using the PDF service,
    and returns both Markdown and TipTap JSON formats.

    TODO: Implement third-party PDF API integration for actual parsing.

    Args:
        file: PDF file to parse
        title: Optional document title (defaults to filename)
        description: Optional document description
        category: Optional document category
        current_user: Current authenticated user
        db: Database session

    Returns:
        PDFUploadResponse: Parsed content in both formats

    Raises:
        HTTPException: If file is invalid or parsing fails
    """
    # Validate file type
    if not file.content_type == "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )

    # Read file content
    try:
        file_bytes = await file.read()
        logger.info(f"Received PDF file: {file.filename}, size: {len(file_bytes)} bytes")
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file"
        )

    # Parse PDF to Markdown
    try:
        markdown_content, images = await pdf_service.parse_pdf_from_bytes(
            file_bytes=file_bytes,
            filename=file.filename,
            extract_images=True,
        )
        logger.info(f"Parsed PDF to Markdown: {len(markdown_content)} chars, {len(images)} images")
    except Exception as e:
        logger.error(f"Failed to parse PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse PDF: {str(e)}"
        )

    # Convert Markdown to TipTap JSON
    try:
        tiptap_content = format_service.md_to_tiptap(markdown_content)
        logger.info(f"Converted Markdown to TipTap JSON")
    except Exception as e:
        logger.error(f"Failed to convert to TipTap: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert content: {str(e)}"
        )

    # Use provided title or fallback to filename
    document_title = title or file.filename.replace(".pdf", "")

    # Note: This endpoint only parses and returns content.
    # To create an actual document, use the returned content with
    # POST /api/v1/documents endpoint.

    return PDFUploadResponse(
        # Placeholder document_id (not actually created)
        document_id=0,
        version_id=0,
        markdown_content=markdown_content,
        tiptap_content=tiptap_content,
    )


@router.post("/convert-to-tiptap")
async def convert_to_tiptap(
    markdown: str,
    current_user: User = Depends(get_current_user),
):
    """
    Convert Markdown text to TipTap JSON format.

    Args:
        markdown: Markdown text content
        current_user: Current authenticated user

    Returns:
        TipTap JSON representation
    """
    try:
        tiptap_json = format_service.md_to_tiptap(markdown)
        return {
            "success": True,
            "tiptap": tiptap_json,
        }
    except Exception as e:
        logger.error(f"Failed to convert to TipTap: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversion failed: {str(e)}"
        )


@router.post("/convert-to-markdown")
async def convert_to_markdown(
    tiptap_json: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """
    Convert TipTap JSON format to Markdown text.

    Args:
        tiptap_json: TipTap JSON document structure
        current_user: Current authenticated user

    Returns:
        Markdown text content
    """
    try:
        markdown = format_service.tiptap_to_md(tiptap_json)
        return {
            "success": True,
            "markdown": markdown,
        }
    except Exception as e:
        logger.error(f"Failed to convert to Markdown: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversion failed: {str(e)}"
        )


# ==================== PDF Service Status ====================

@router.get("/parse-status")
async def get_parse_status(
    current_user: User = Depends(get_current_user),
):
    """
    Get the current status of the PDF parsing service.

    Returns information about the PDF parsing capabilities,
    including whether third-party API integration is complete.
    """
    return {
        "service": "PDFParseService",
        "status": "placeholder",
        "message": "PDF parsing is currently in placeholder mode",
        "capabilities": {
            "pdf_to_markdown": "placeholder",
            "image_extraction": "not_implemented",
            "table_recognition": "not_implemented",
            "metadata_extraction": "not_implemented",
        },
        "todo": [
            "Integrate third-party PDF parsing API",
            "Recommended options:",
            "  - Adobe PDF Services API",
            "  - Cloudmersive PDF API",
            "  - PyMuPDF (local library)",
            "  - pdfplumber (local library)",
        ],
    }
