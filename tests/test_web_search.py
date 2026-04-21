"""
Tests for Web Search functionality
"""

import pytest
from openclaw_swarm.web_search import WebSearch, SearchResult


class TestWebSearch:
    """Test WebSearch class"""

    def test_search_initialization(self):
        """Test WebSearch initialization"""
        search = WebSearch()
        assert search.firecrawl_key is None

        search_with_key = WebSearch(firecrawl_key="test_key")
        assert search_with_key.firecrawl_key == "test_key"

    def test_search_result_dataclass(self):
        """Test SearchResult dataclass"""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test snippet",
            source="duckduckgo",
        )

        assert result.title == "Test"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.source == "duckduckgo"

    def test_search_returns_list(self):
        """Test that search returns a list"""
        search = WebSearch()
        results = search.search("test query", max_results=3)

        assert isinstance(results, list)
        assert len(results) <= 3

    def test_html_to_markdown(self):
        """Test HTML to markdown conversion"""
        search = WebSearch()

        html = "<h1>Title</h1><p>Paragraph</p>"
        markdown = search._html_to_markdown(html)

        assert "# Title" in markdown
        assert "Paragraph" in markdown

    def test_html_to_markdown_links(self):
        """Test link conversion"""
        search = WebSearch()

        html = '<a href="https://example.com">Link</a>'
        markdown = search._html_to_markdown(html)

        assert "[Link](https://example.com)" in markdown

    def test_html_to_markdown_code(self):
        """Test code conversion"""
        search = WebSearch()

        html = "<code>inline code</code>"
        markdown = search._html_to_markdown(html)

        assert "`inline code`" in markdown

    def test_html_to_markdown_pre(self):
        """Test pre block conversion"""
        search = WebSearch()

        html = "<pre>code block</pre>"
        markdown = search._html_to_markdown(html)

        assert "```" in markdown
        assert "code block" in markdown

    def test_fetch_returns_string(self):
        """Test that fetch returns a string"""
        search = WebSearch()

        # Test with a simple URL (might fail without network)
        result = search.fetch("https://example.com")

        assert isinstance(result, str)

    def test_search_and_summarize_structure(self):
        """Test search_and_summarize returns correct structure"""
        search = WebSearch()
        result = search.search_and_summarize("test", max_results=2)

        assert "query" in result
        assert "results_count" in result
        assert "results" in result
        assert result["query"] == "test"

    def test_parse_ddg_html_empty(self):
        """Test parsing empty HTML"""
        search = WebSearch()
        results = search._parse_ddg_html("", 5)

        assert results == []

    def test_parse_ddg_html_with_results(self):
        """Test parsing HTML with results"""
        search = WebSearch()

        html = """
        <a rel="nofollow" class="result__a" href="https://example.com">Example</a>
        <a rel="nofollow" class="result__a" href="https://test.com">Test</a>
        """

        results = search._parse_ddg_html(html, 2)

        assert len(results) <= 2
        for r in results:
            assert isinstance(r, SearchResult)


class TestSearchResult:
    """Test SearchResult class"""

    def test_result_creation(self):
        """Test creating a result"""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            source="test",
        )

        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.source == "test"
