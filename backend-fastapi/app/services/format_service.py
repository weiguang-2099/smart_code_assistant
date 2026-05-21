"""
Format conversion service for Markdown ↔ TipTap JSON transformation.

This service handles bidirectional conversion between Markdown text and
TipTap editor JSON format, enabling seamless integration with the frontend
rich text editor.
"""
import re
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FormatConvertService:
    """
    Format conversion service for Markdown ↔ TipTap.

    The TipTap format is based on ProseMirror schema, which represents
    documents as a tree of nodes with marks for text styling.
    """

    def __init__(self):
        """Initialize format conversion service."""
        logger.info("FormatConvertService initialized")

    def md_to_tiptap(self, markdown: str) -> Dict[str, Any]:
        """
        Convert Markdown text to TipTap JSON format.

        Args:
            markdown: Markdown text content

        Returns:
            TipTap JSON document structure

        Example:
            Input:  "# Hello\\n\\nThis is **bold** text."
            Output: {"type": "doc", "content": [...]}
        """
        if not markdown:
            return self._empty_document()

        content_nodes = []
        lines = markdown.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()

            # Handle code blocks
            if stripped.startswith("```"):
                code_block, end_index = self._parse_code_block(lines, i)
                content_nodes.append(code_block)
                i = end_index
                continue

            # Handle headings
            if stripped.startswith("#"):
                heading = self._parse_heading(stripped)
                content_nodes.append(heading)
                i += 1
                continue

            # Handle horizontal rules
            if re.match(r"^[-*_]{3,}\s*$", stripped):
                content_nodes.append({"type": "horizontalRule"})
                i += 1
                continue

            # Handle blockquotes
            if stripped.startswith(">"):
                blockquote, end_index = self._parse_blockquote(lines, i)
                content_nodes.append(blockquote)
                i = end_index
                continue

            # Handle lists
            if stripped.startswith(("- ", "* ", "+ ")) or re.match(r"^\d+\.\s", stripped):
                list_node, end_index = self._parse_list(lines, i)
                content_nodes.append(list_node)
                i = end_index
                continue

            # Handle regular paragraphs
            if stripped:
                paragraph = self._parse_paragraph(line)
                content_nodes.append(paragraph)
            elif content_nodes and content_nodes[-1]["type"] != "paragraph":
                # Empty line - add hard break if previous content exists
                content_nodes.append({"type": "paragraph"})
            i += 1

        # Remove trailing empty paragraphs
        while content_nodes and content_nodes[-1] == {"type": "paragraph"}:
            content_nodes.pop()

        return {"type": "doc", "content": content_nodes}

    def tiptap_to_md(self, tiptap_json: Dict[str, Any]) -> str:
        """
        Convert TipTap JSON format to Markdown text.

        Args:
            tiptap_json: TipTap JSON document structure

        Returns:
            Markdown text content
        """
        if not tiptap_json or tiptap_json.get("type") != "doc":
            return ""

        content = tiptap_json.get("content", [])
        if not content:
            return ""

        lines = []
        for node in content:
            lines.append(self._node_to_markdown(node, 0))

        return "\n".join(lines)

    def _empty_document(self) -> Dict[str, Any]:
        """Return an empty TipTap document."""
        return {"type": "doc", "content": []}

    # ==================== Markdown → TipTap Parsers ====================

    def _parse_code_block(self, lines: List[str], start_index: int) -> tuple:
        """Parse a fenced code block."""
        first_line = lines[start_index].lstrip()
        # Extract language info if present
        lang_match = re.match(r"^```(\w+)?", first_line)
        language = lang_match.group(1) or ""

        # Find closing ```
        content_lines = []
        i = start_index + 1
        while i < len(lines):
            if lines[i].lstrip().startswith("```"):
                break
            content_lines.append(lines[i])
            i += 1

        return {
            "type": "codeBlock",
            "attrs": {"language": language},
            "content": [{"type": "text", "text": "\n".join(content_lines)}] if content_lines else [],
        }, i + 1

    def _parse_heading(self, line: str) -> Dict[str, Any]:
        """Parse a heading line."""
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            level = len(match.group(1))
            text = match.group(2)
            return {
                "type": "heading",
                "attrs": {"level": level},
                "content": [{"type": "text", "text": text}] if text else [],
            }
        return {"type": "paragraph", "content": []}

    def _parse_blockquote(self, lines: List[str], start_index: int) -> tuple:
        """Parse a blockquote block."""
        content_lines = []
        i = start_index
        while i < len(lines):
            stripped = lines[i].lstrip()
            if not stripped.startswith(">"):
                break
            # Remove the > prefix
            content_lines.append(stripped[1:].lstrip())
            i += 1

        # Parse inner content as paragraphs
        paragraphs = []
        for line in content_lines:
            if line:
                paragraphs.append(self._parse_inline_text(line))

        return {
            "type": "blockquote",
            "content": paragraphs,
        }, i

    def _parse_list(self, lines: List[str], start_index: int) -> tuple:
        """Parse an ordered or unordered list."""
        # Determine list type
        first_line = lines[start_index].lstrip()
        is_ordered = bool(re.match(r"^\d+\.\s", first_line))

        list_items = []
        i = start_index

        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()

            # Check if still a list item
            if is_ordered:
                if not re.match(r"^\d+\.\s", stripped):
                    break
            else:
                if not stripped.startswith(("- ", "* ", "+ ")):
                    break

            # Extract content
            if is_ordered:
                content = re.sub(r"^\d+\.\s", "", stripped)
            else:
                content = re.sub(r"^[-*+]\s", "", stripped)

            list_items.append({
                "type": "listItem",
                "content": [{"type": "paragraph", "content": self._parse_inline_text(content)}],
            })
            i += 1

        return {
            "type": "bulletList" if not is_ordered else "orderedList",
            "content": list_items,
        }, i

    def _parse_paragraph(self, line: str) -> Dict[str, Any]:
        """Parse a regular paragraph line."""
        return {
            "type": "paragraph",
            "content": self._parse_inline_text(line),
        }

    def _parse_inline_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse inline formatting (bold, italic, code, links, etc.)."""
        if not text:
            return []

        nodes = []
        remaining = text

        # Pattern for inline formatting
        patterns = [
            (r"\*\*\*(.+?)\*\*\*", "bold_italic"),
            (r"___(.+?)___", "bold_italic"),
            (r"\*\*(.+?)\*\*", "bold"),
            (r"__(.+?)__", "bold"),
            (r"\*(.+?)\*", "italic"),
            (r"_(.+?)_", "italic"),
            (r"`(.+?)`", "code"),
            (r"\[(.+?)\]\((.+?)\)", "link"),
        ]

        while remaining:
            # Find the earliest match
            earliest_match = None
            earliest_pos = len(remaining)
            matched_pattern = None

            for pattern, format_type in patterns:
                match = re.search(pattern, remaining)
                if match:
                    if match.start() < earliest_pos:
                        earliest_pos = match.start()
                        earliest_match = match
                        matched_pattern = (pattern, format_type)

            if earliest_match:
                # Add text before the match
                if earliest_pos > 0:
                    nodes.append({"type": "text", "text": remaining[:earliest_pos]})

                # Add the formatted text
                pattern, format_type = matched_pattern
                if format_type == "link":
                    nodes.append({
                        "type": "text",
                        "marks": [{"type": "link", "attrs": {"href": earliest_match.group(2)}}],
                        "text": earliest_match.group(1),
                    })
                elif format_type == "code":
                    nodes.append({
                        "type": "code",
                        "text": earliest_match.group(1),
                    })
                elif format_type == "bold":
                    nodes.append({
                        "type": "text",
                        "marks": [{"type": "bold"}],
                        "text": earliest_match.group(1),
                    })
                elif format_type == "italic":
                    nodes.append({
                        "type": "text",
                        "marks": [{"type": "italic"}],
                        "text": earliest_match.group(1),
                    })
                elif format_type == "bold_italic":
                    nodes.append({
                        "type": "text",
                        "marks": [{"type": "bold"}, {"type": "italic"}],
                        "text": earliest_match.group(1),
                    })

                remaining = remaining[earliest_match.end():]
            else:
                # No more matches, add remaining text
                nodes.append({"type": "text", "text": remaining})
                break

        return nodes if nodes else [{"type": "text", "text": text}]

    # ==================== TipTap → Markdown ====================

    def _node_to_markdown(self, node: Dict[str, Any], indent_level: int) -> str:
        """Convert a TipTap node to Markdown."""
        node_type = node.get("type", "")
        content = node.get("content", [])
        indent = "  " * indent_level

        if node_type == "paragraph":
            text = self._content_to_text(content)
            return f"{indent}{text}" if text.strip() else ""

        elif node_type == "heading":
            level = node.get("attrs", {}).get("level", 1)
            text = self._content_to_text(content)
            return f"{indent}{'#' * level} {text}"

        elif node_type == "codeBlock":
            language = node.get("attrs", {}).get("language", "")
            lang_attr = language if language else ""
            text = self._content_to_text(content, preserve_newlines=True)
            return f"{indent}```{lang_attr}\n{indent}{text}\n{indent}```"

        elif node_type == "blockquote":
            inner = "\n".join(
                f"{indent}> {self._content_to_text([child])}"
                for child in content
            )
            return inner

        elif node_type == "bulletList":
            items = []
            for child in content:
                if child.get("type") == "listItem":
                    items.append(f"{indent}- {self._render_list_item(child)}")
            return "\n".join(items)

        elif node_type == "orderedList":
            items = []
            for idx, child in enumerate(content, 1):
                if child.get("type") == "listItem":
                    items.append(f"{indent}{idx}. {self._render_list_item(child)}")
            return "\n".join(items)

        elif node_type == "horizontalRule":
            return f"{indent}---"

        elif node_type == "hardBreak":
            return f"{indent}\n"

        else:
            # Default: treat as text
            return self._content_to_text(content)

    def _render_list_item(self, list_item: Dict[str, Any]) -> str:
        """
        Unwrap a listItem's inner content. md_to_tiptap wraps each item in a
        paragraph, so we recurse one level rather than treating the paragraph
        as opaque text.
        """
        parts = []
        for nested in list_item.get("content", []):
            if nested.get("type") == "paragraph":
                parts.append(self._content_to_text(nested.get("content", [])))
            else:
                parts.append(self._content_to_text([nested]))
        return " ".join(p for p in parts if p)

    def _content_to_text(self, content: List[Dict[str, Any]], preserve_newlines: bool = False) -> str:
        """Convert content nodes to plain text with inline formatting."""
        if not content:
            return ""

        parts = []
        for node in content:
            if node.get("type") == "text":
                text = node.get("text", "")
                marks = node.get("marks", [])

                # Apply marks in reverse order (nesting)
                for mark in reversed(marks):
                    mark_type = mark.get("type", "")
                    if mark_type == "bold":
                        text = f"**{text}**"
                    elif mark_type == "italic":
                        text = f"*{text}*"
                    elif mark_type == "code":
                        text = f"`{text}`"
                    elif mark_type == "link":
                        href = mark.get("attrs", {}).get("href", "")
                        text = f"[{text}]({href})"

                parts.append(text)

            elif node.get("type") == "hardBreak":
                parts.append("\n")

            elif node.get("type") == "code":
                parts.append(f"`{node.get('text', '')}`")

        result = "".join(parts)
        if preserve_newlines:
            return result
        return result.replace("\n", " ")


# Singleton instance
format_service = FormatConvertService()
