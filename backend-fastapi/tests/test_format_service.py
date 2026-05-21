"""
Tests for Markdown <-> TipTap format conversion.

The service is pure logic; we exercise each block type and roundtrip a sample
document end to end.
"""
import pytest

from app.services.format_service import FormatConvertService, format_service


@pytest.fixture
def svc():
    return FormatConvertService()


def _node_types(doc):
    return [n.get("type") for n in doc.get("content", [])]


# ----- md -> tiptap -----

class TestMarkdownToTipTap:
    def test_empty_input_returns_empty_doc(self, svc):
        doc = svc.md_to_tiptap("")
        assert doc == {"type": "doc", "content": []}

    def test_singleton_instance_exists(self):
        assert isinstance(format_service, FormatConvertService)

    def test_heading_levels(self, svc):
        doc = svc.md_to_tiptap("# H1\n## H2\n### H3")
        types = _node_types(doc)
        assert types == ["heading", "heading", "heading"]
        levels = [n["attrs"]["level"] for n in doc["content"]]
        assert levels == [1, 2, 3]

    def test_paragraph_extracted(self, svc):
        doc = svc.md_to_tiptap("just some text")
        assert _node_types(doc) == ["paragraph"]

    def test_bold_and_italic_marks(self, svc):
        doc = svc.md_to_tiptap("This is **bold** and *italic*.")
        paragraph = doc["content"][0]
        marks = [m.get("type") for child in paragraph["content"] for m in child.get("marks", [])]
        assert "bold" in marks
        assert "italic" in marks

    def test_inline_code_recognised(self, svc):
        doc = svc.md_to_tiptap("Run `pytest` now.")
        para = doc["content"][0]
        # contains a code node
        assert any(c.get("type") == "code" for c in para["content"])

    def test_link_extracted(self, svc):
        doc = svc.md_to_tiptap("see [docs](https://example.com)")
        para = doc["content"][0]
        link_node = next(c for c in para["content"] if c.get("marks"))
        assert link_node["marks"][0]["type"] == "link"
        assert link_node["marks"][0]["attrs"]["href"] == "https://example.com"

    def test_fenced_code_block_preserves_language(self, svc):
        md = "```python\nprint('hi')\n```"
        doc = svc.md_to_tiptap(md)
        code = doc["content"][0]
        assert code["type"] == "codeBlock"
        assert code["attrs"]["language"] == "python"
        assert "print('hi')" in code["content"][0]["text"]

    def test_horizontal_rule(self, svc):
        doc = svc.md_to_tiptap("hello\n\n---\n\nworld")
        types = _node_types(doc)
        assert "horizontalRule" in types

    def test_blockquote(self, svc):
        doc = svc.md_to_tiptap("> quoted line\n> more quoted")
        first = doc["content"][0]
        assert first["type"] == "blockquote"

    def test_unordered_list(self, svc):
        doc = svc.md_to_tiptap("- one\n- two\n- three")
        first = doc["content"][0]
        assert first["type"] == "bulletList"
        assert len(first["content"]) == 3

    def test_ordered_list(self, svc):
        doc = svc.md_to_tiptap("1. one\n2. two")
        first = doc["content"][0]
        assert first["type"] == "orderedList"
        assert len(first["content"]) == 2


# ----- tiptap -> md -----

class TestTipTapToMarkdown:
    def test_empty_doc_returns_empty_string(self, svc):
        assert svc.tiptap_to_md({}) == ""
        assert svc.tiptap_to_md({"type": "doc", "content": []}) == ""

    def test_non_doc_root_returns_empty(self, svc):
        assert svc.tiptap_to_md({"type": "paragraph", "content": []}) == ""

    def test_heading_emits_hashes(self, svc):
        doc = {"type": "doc", "content": [
            {"type": "heading", "attrs": {"level": 2}, "content": [
                {"type": "text", "text": "Title"}
            ]}
        ]}
        assert svc.tiptap_to_md(doc) == "## Title"

    def test_paragraph_with_bold_marks(self, svc):
        doc = {"type": "doc", "content": [
            {"type": "paragraph", "content": [
                {"type": "text", "text": "Hello "},
                {"type": "text", "text": "World", "marks": [{"type": "bold"}]},
            ]}
        ]}
        assert "**World**" in svc.tiptap_to_md(doc)

    def test_link_emits_inline_md(self, svc):
        doc = {"type": "doc", "content": [
            {"type": "paragraph", "content": [
                {"type": "text", "text": "click",
                 "marks": [{"type": "link", "attrs": {"href": "https://x.com"}}]}
            ]}
        ]}
        out = svc.tiptap_to_md(doc)
        assert "[click](https://x.com)" in out

    def test_code_block_round_trips_language(self, svc):
        doc = {"type": "doc", "content": [
            {"type": "codeBlock", "attrs": {"language": "rust"},
             "content": [{"type": "text", "text": "fn main(){}"}]}
        ]}
        out = svc.tiptap_to_md(doc)
        assert "```rust" in out
        assert "fn main(){}" in out

    def test_bullet_list_emits_dashes(self, svc):
        doc = {"type": "doc", "content": [
            {"type": "bulletList", "content": [
                {"type": "listItem", "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "a"}]}
                ]},
                {"type": "listItem", "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "b"}]}
                ]},
            ]}
        ]}
        out = svc.tiptap_to_md(doc)
        assert "- a" in out and "- b" in out

    def test_ordered_list_emits_numbers(self, svc):
        doc = {"type": "doc", "content": [
            {"type": "orderedList", "content": [
                {"type": "listItem", "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "x"}]}
                ]},
                {"type": "listItem", "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "y"}]}
                ]},
            ]}
        ]}
        out = svc.tiptap_to_md(doc)
        assert "1. x" in out and "2. y" in out

    def test_horizontal_rule(self, svc):
        doc = {"type": "doc", "content": [{"type": "horizontalRule"}]}
        assert "---" in svc.tiptap_to_md(doc)


# ----- light roundtrip -----

class TestRoundtripIsStable:
    def test_simple_heading_paragraph_roundtrip(self, svc):
        md = "# Title\n\nbody text"
        doc = svc.md_to_tiptap(md)
        out = svc.tiptap_to_md(doc)
        assert "# Title" in out
        assert "body text" in out
