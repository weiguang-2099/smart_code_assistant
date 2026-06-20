"""extract_files_from_retrieval must handle search_all()'s actual dict shape:
{"functions": [chunk...], "classes": [chunk...]} merged by relevance_score."""
from evals.runner import extract_files_from_retrieval, extract_neighbors_from_graph


def chunk(path, score):
    return {"metadata": {"module_path": path}, "relevance_score": score}


class TestDictShape:
    def test_dict_shape_extracts_and_ranks_by_relevance(self):
        semantic_results = {
            "functions": [chunk("app/a.py", 0.9), chunk("app/c.py", 0.5)],
            "classes": [chunk("app/b.py", 0.7)],
        }
        assert extract_files_from_retrieval(semantic_results) == [
            "app/a.py", "app/b.py", "app/c.py",
        ]

    def test_empty_dict(self):
        assert extract_files_from_retrieval({}) == []

    def test_none_returns_empty(self):
        assert extract_files_from_retrieval(None) == []

    def test_missing_relevance_score_sorts_last(self):
        semantic_results = {
            "functions": [{"metadata": {"module_path": "app/x.py"}}],
            "classes": [chunk("app/y.py", 0.1)],
        }
        assert extract_files_from_retrieval(semantic_results) == ["app/y.py", "app/x.py"]


class TestListShapeStillWorks:
    def test_flat_list_passthrough(self):
        flat = [chunk("app/a.py", 0.9), chunk("backend-fastapi/app/b.py", 0.8)]
        assert extract_files_from_retrieval(flat) == ["app/a.py", "app/b.py"]


class TestNeighborExtractionNewShape:
    def test_extracts_names_not_module_paths(self):
        graph_context = [
            {"name": "do_work", "module_path": "app/a.py", "relation": "callee", "source": "retrieve"},
            {"name": "Neo4jClient", "module_path": None, "relation": "import", "source": "retrieve"},
        ]
        out = extract_neighbors_from_graph(graph_context)
        assert "do_work" in out
        assert "Neo4jClient" in out
        assert "app/a.py" not in out  # module paths are not neighbor names
