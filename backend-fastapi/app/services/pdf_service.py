"""
PDF parsing service using Datalab Marker API.

This service converts PDF documents to Markdown format by calling the
Datalab Marker API (https://www.datalab.to/api/v1/marker).

API flow:
1. Submit PDF file via POST -> receive request_id and check_url
2. Poll the check_url until status is "complete" or "failed"
3. Return the markdown content and extracted images

Docs: https://documentation.datalab.to/docs/recipes/marker/conversion-api-overview
"""
import asyncio
import base64
import os
import tempfile
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MODE = "balanced"  # "fast" | "balanced" | "accurate"
DEFAULT_OUTPUT_FORMAT = "markdown"
POLL_INTERVAL_SECONDS = 2
MAX_POLL_ATTEMPTS = 300  # 300 * 2s = 10 minutes max wait


class PDFParseService:
    """
    PDF parsing service powered by Datalab Marker API.

    Features:
    - PDF text extraction to Markdown / HTML / JSON
    - Image extraction from PDF (base64 encoded)
    - Table recognition and conversion
    - Preserves document structure (headings, lists, etc.)
    """

    def __init__(self):
        """Initialize PDF parsing service."""
        self.temp_dir = tempfile.gettempdir()
        self.api_url = settings.DATALAB_API_URL
        self.api_key = settings.DATALAB_API_KEY
        if self.api_key:
            logger.info("PDFParseService initialized (Datalab Marker API)")
        else:
            logger.warning(
                "PDFParseService: DATALAB_API_KEY is not set. "
                "PDF parsing will fail until a valid key is configured."
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for Datalab API requests."""
        return {"X-API-Key": self.api_key}

    async def _submit_file(
        self,
        file_path: str,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        mode: str = DEFAULT_MODE,
        extract_images: bool = True,
        max_pages: Optional[int] = None,
        page_range: Optional[str] = None,
        paginate: bool = False,
    ) -> dict:
        """
        Submit a PDF file to the Datalab Marker API.

        Returns the JSON response containing ``request_id`` and
        ``request_check_url``.
        """
        if not self.api_key:
            raise RuntimeError(
                "DATALAB_API_KEY is not configured. "
                "Set the DATALAB_API_KEY environment variable or add it to .env"
            )

        data: Dict[str, str] = {
            "output_format": output_format,
            "mode": mode,
            "disable_image_extraction": str(not extract_images).lower(),
            "paginate": str(paginate).lower(),
        }
        if max_pages is not None:
            data["max_pages"] = str(max_pages)
        if page_range is not None:
            data["page_range"] = page_range

        filename = Path(file_path).name
        headers = self._build_headers()
        
        # Debug logging (mask the API key for security)
        masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "***"
        logger.info(
            "Submitting to Datalab API: url=%s, api_key=%s, file=%s",
            self.api_url,
            masked_key,
            filename,
        )
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(file_path, "rb") as f:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    files={"file": (filename, f, "application/pdf")},
                    data=data,
                )

        # Enhanced error handling with response details
        if response.status_code != 200:
            error_details = f"Status: {response.status_code}, Response: {response.text[:500]}"
            logger.error("Datalab API error: %s", error_details)
            raise RuntimeError(
                f"Datalab API returned {response.status_code}: {response.text[:200]}"
            )

        result = response.json()

        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error from Datalab API")
            raise RuntimeError(f"Datalab submission failed: {error_msg}")

        logger.info(
            "Submitted PDF to Datalab: request_id=%s", result.get("request_id")
        )
        return result

    async def _poll_result(self, check_url: str) -> dict:
        """
        Poll the Datalab result endpoint until the job is complete or fails.

        Returns the full result dictionary.
        """
        headers = self._build_headers()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
                response = await client.get(check_url, headers=headers)
                response.raise_for_status()
                result = response.json()

                status = result.get("status", "")
                if status == "complete":
                    logger.info(
                        "Datalab conversion complete (attempt %d/%d)",
                        attempt,
                        MAX_POLL_ATTEMPTS,
                    )
                    return result
                elif status == "failed":
                    error_msg = result.get("error", "Unknown error")
                    raise RuntimeError(
                        f"Datalab conversion failed: {error_msg}"
                    )

                # Still processing -- wait and retry
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

        raise TimeoutError(
            f"Datalab conversion timed out after "
            f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def parse_pdf(
        self,
        file_path: str,
        extract_images: bool = True,
        mode: str = DEFAULT_MODE,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        max_pages: Optional[int] = None,
        page_range: Optional[str] = None,
        paginate: bool = False,
    ) -> Tuple[str, List[dict]]:
        """
        Parse a PDF file and return its content as Markdown (or other format).

        Args:
            file_path: Path to the PDF file.
            extract_images: Whether to extract images from the PDF.
            mode: Processing mode -- "fast", "balanced", or "accurate".
            output_format: Output format -- "markdown", "html", "json", "chunks".
            max_pages: Maximum number of pages to process.
            page_range: Specific pages, e.g. "0-5,10".
            paginate: Whether to add page delimiters.

        Returns:
            Tuple of (content_string, images_list).
            ``images_list`` contains dicts with keys:
                - filename (str)
                - data (bytes) -- raw image bytes
                - base64 (str) -- base64-encoded string
        """
        # Step 1: Submit
        submit_result = await self._submit_file(
            file_path=file_path,
            output_format=output_format,
            mode=mode,
            extract_images=extract_images,
            max_pages=max_pages,
            page_range=page_range,
            paginate=paginate,
        )

        check_url = submit_result["request_check_url"]

        # Step 2: Poll
        result = await self._poll_result(check_url)

        # Step 3: Extract content
        content = result.get(output_format, result.get("markdown", ""))

        # Step 4: Extract images
        images: List[dict] = []
        raw_images: Dict[str, str] = result.get("images", {})
        if raw_images and extract_images:
            for img_filename, img_b64 in raw_images.items():
                try:
                    img_bytes = base64.b64decode(img_b64)
                    images.append(
                        {
                            "filename": img_filename,
                            "data": img_bytes,
                            "base64": img_b64,
                            "size": len(img_bytes),
                        }
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to decode image %s: %s", img_filename, exc
                    )

        # Log summary
        page_count = result.get("page_count", "?")
        quality = result.get("parse_quality_score", "?")
        logger.info(
            "Parsed PDF: %s -> %d chars, %d images, %s pages, quality=%s",
            file_path,
            len(content),
            len(images),
            page_count,
            quality,
        )

        return content, images

    async def parse_pdf_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        extract_images: bool = True,
        mode: str = DEFAULT_MODE,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        max_pages: Optional[int] = None,
        page_range: Optional[str] = None,
        paginate: bool = False,
    ) -> Tuple[str, List[dict]]:
        """
        Parse PDF from raw bytes.

        Saves to a temporary file, calls :meth:`parse_pdf`, then cleans up.

        Args:
            file_bytes: PDF content as bytes.
            filename: Original filename.
            extract_images: Whether to extract images.
            mode: Processing mode.
            output_format: Output format.
            max_pages: Maximum pages to process.
            page_range: Specific pages.
            paginate: Add page delimiters.

        Returns:
            Tuple of (content_string, images_list).
        """
        temp_path = os.path.join(self.temp_dir, filename)
        try:
            with open(temp_path, "wb") as f:
                f.write(file_bytes)

            return await self.parse_pdf(
                file_path=temp_path,
                extract_images=extract_images,
                mode=mode,
                output_format=output_format,
                max_pages=max_pages,
                page_range=page_range,
                paginate=paginate,
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def get_pdf_metadata(self, file_path: str) -> dict:
        """
        Get metadata from a PDF by running a fast conversion.

        Returns a dictionary with page_count, parse_quality_score, etc.
        """
        submit_result = await self._submit_file(
            file_path=file_path,
            output_format="markdown",
            mode="fast",
            extract_images=False,
            max_pages=1,
        )
        result = await self._poll_result(submit_result["request_check_url"])

        return {
            "title": Path(file_path).stem,
            "page_count": result.get("page_count"),
            "parse_quality_score": result.get("parse_quality_score"),
            "metadata": result.get("metadata", {}),
            "cost_breakdown": result.get("cost_breakdown", {}),
        }


# Singleton instance
pdf_service = PDFParseService()
