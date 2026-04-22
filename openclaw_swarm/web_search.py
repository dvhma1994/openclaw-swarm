"""
OpenClaw Swarm - Web Search & Fetch
Supports DuckDuckGo (free) and Firecrawl (optional)
"""

import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SearchResult:
    """Web search result"""

    title: str
    url: str
    snippet: str
    source: str


class WebSearch:
    """Web search using DuckDuckGo (free) or Firecrawl (paid)"""

    def __init__(self, firecrawl_key: Optional[str] = None):
        self.firecrawl_key = firecrawl_key

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Search the web using DuckDuckGo (free)

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of search results
        """
        # Use DuckDuckGo HTML version (free, no API key)
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"

        results = []
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response = urllib.request.urlopen(req, timeout=10)
            html = response.read().decode("utf-8")

            # Parse results from HTML
            results = self._parse_ddg_html(html, max_results)

        except Exception as e:
            print(f"Search error: {e}")

        return results

    def _parse_ddg_html(self, html: str, max_results: int) -> List[SearchResult]:
        """Parse DuckDuckGo HTML results"""
        results = []

        # Simple regex-based parsing
        import re

        # Find result patterns
        pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        for url, title in matches[:max_results]:
            # Clean URL (DuckDuckGo redirects)
            if "uddg=" in url:
                url = urllib.parse.unquote(url.split("uddg=")[1].split("&")[0])

            results.append(
                SearchResult(
                    title=title.strip(),
                    url=url,
                    snippet="",  # Would need more parsing
                    source="duckduckgo",
                )
            )

        return results

    def fetch(self, url: str) -> str:
        """
        Fetch and convert webpage to markdown

        Args:
            url: URL to fetch

        Returns:
            Markdown content
        """
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response = urllib.request.urlopen(req, timeout=30)
            html = response.read().decode("utf-8")

            # Convert HTML to markdown (simple)
            return self._html_to_markdown(html)

        except Exception as e:
            return f"Fetch error: {e}"

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to simple markdown"""
        import re

        # Remove scripts and styles
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)

        # Convert common elements
        html = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", html)
        html = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", html)
        html = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", html)
        html = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", html, flags=re.DOTALL)
        html = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", html)
        html = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", html)
        html = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", html)
        html = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", html)
        html = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", html)
        html = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", html)
        html = re.sub(
            r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", html, flags=re.DOTALL
        )
        html = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", html)

        # Remove remaining tags
        html = re.sub(r"<[^>]+>", "", html)

        # Clean up whitespace
        html = re.sub(r"\n\s*\n\s*\n", "\n\n", html)
        html = re.sub(r"  +", " ", html)

        return html.strip()

    def search_and_summarize(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search and return structured summary

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            Structured search results
        """
        results = self.search(query, max_results)

        return {
            "query": query,
            "results_count": len(results),
            "results": [
                {"title": r.title, "url": r.url, "snippet": r.snippet} for r in results
            ],
        }
