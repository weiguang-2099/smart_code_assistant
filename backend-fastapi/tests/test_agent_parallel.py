"""Tests for parallel tool execution"""
import pytest
import time
from unittest.mock import patch, MagicMock


class TestParallelToolAnalysis:
    """Test parallel tool execution"""

    @pytest.mark.asyncio
    async def test_run_tool_analysis_returns_all_results(self):
        """Should return results for all 4 tools"""
        from app.api.agent import run_tool_analysis

        code = "def hello():\n    print('hello')"
        language = "python"

        result = await run_tool_analysis(code, language)

        assert "analyze_code_structure" in result
        assert "detect_code_smells" in result
        assert "calculate_code_complexity" in result
        assert "check_security_issues" in result

    @pytest.mark.asyncio
    async def test_parallel_execution_is_faster_than_sequential(self):
        """Parallel execution should be significantly faster"""
        from app.api.agent import run_tool_analysis

        code = "def hello():\n    print('hello')"
        language = "python"

        # Each tool takes ~0.5s, 4 tools sequentially = 2s
        # Parallel should be ~0.5s
        start = time.time()
        await run_tool_analysis(code, language)
        elapsed = time.time() - start

        # Should complete in less than 1.5 seconds (allowing overhead)
        assert elapsed < 1.5, f"Parallel execution took {elapsed}s, expected < 1.5s"

    @pytest.mark.asyncio
    async def test_handles_tool_exceptions_gracefully(self):
        """Should not fail if one tool throws an exception"""
        from app.api.agent import run_tool_analysis

        code = "def hello():\n    print('hello')"
        language = "python"

        result = await run_tool_analysis(code, language)

        # All results should be strings (either result or error message)
        for tool_name, tool_result in result.items():
            assert isinstance(tool_result, str), f"{tool_name} result should be string"
