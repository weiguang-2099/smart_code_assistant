"""Unit tests for document outline extraction (app.api.documents)."""
from app.api.documents import extract_outline_from_markdown


def test_extract_outline_builds_nested_tree():
    md = "# Title\n\n## Section A\n\ntext\n\n### Sub\n\n## Section B"
    outline = extract_outline_from_markdown(md)

    assert len(outline) == 1
    assert outline[0].level == 1
    assert outline[0].text == "Title"

    # H1 has two H2 children
    children = outline[0].children
    assert [c.text for c in children] == ["Section A", "Section B"]

    # Section A nests the H3
    assert [c.text for c in children[0].children] == ["Sub"]


def test_extract_outline_empty_returns_empty_list():
    assert extract_outline_from_markdown("just a paragraph, no headings") == []
