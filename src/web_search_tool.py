"""
Web Search Tool - DuckDuckGo Integration
Searches the web for information about websites.

Input: Search query (typically website URL or domain)
Output: List of search results with titles, snippets, URLs
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ddgs import DDGS


@dataclass
class SearchResult:
    """Represents a single search result."""
    title: str
    snippet: str
    url: str


class WebSearchTool:
    """
    DuckDuckGo-based web search tool.
    No API key required - free and unlimited (within reason).
    """

    def __init__(self, max_results: int = 5):
        """
        Initialize the Web Search Tool.

        Args:
            max_results: Maximum number of search results to return per query
        """
        self.max_results = max_results

    def search(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """
        Search the web for information.

        Args:
            query: Search query string
            max_results: Override default max_results if provided

        Returns:
            List of SearchResult objects
        """
        num_results = max_results or self.max_results

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query,
                    max_results=num_results,
                    safesearch="moderate"
                ))

            search_results = []
            for r in results:
                search_results.append(SearchResult(
                    title=r.get("title", ""),
                    snippet=r.get("body", ""),
                    url=r.get("href", "")
                ))

            return search_results

        except Exception as e:
            print(f"⚠️ Search error: {e}")
            return []

    def search_website_info(self, url: str) -> Dict[str, Any]:
        """
        Search for comprehensive information about a website.
        Performs multiple targeted searches to gather context.

        Args:
            url: Website URL to research

        Returns:
            Dict with categorized search results
        """
        # Extract domain from URL
        domain = self._extract_domain(url)
        site_name = self._get_site_name(domain)

        # Multiple search queries for comprehensive understanding
        # Focus on FUNCTIONALITY and USER ACTIONS, not meta-information
        queries = {
            "general": f'"{site_name}" website',
            "functionality": f"{site_name} how to use features tutorial",
            "user_actions": f"{site_name} login account transfer payment",
            "user_guide": f"{site_name} user guide getting started",
        }

        results = {}
        all_snippets = []

        for category, query in queries.items():
            print(f"🔍 Searching: {query}")
            search_results = self.search(query, max_results=3)
            results[category] = [
                {"title": r.title, "snippet": r.snippet, "url": r.url}
                for r in search_results
            ]
            all_snippets.extend([r.snippet for r in search_results])

        return {
            "domain": domain,
            "url": url,
            "search_results": results,
            "combined_context": "\n\n".join(all_snippets),
            "num_results": sum(len(v) for v in results.values())
        }

    def _get_site_name(self, domain: str) -> str:
        """Extract readable site name from domain."""
        # Remove TLD (.com, .org, etc.)
        parts = domain.split(".")
        if len(parts) >= 2:
            # Handle subdomains like parabank.parasoft.com
            if len(parts) > 2:
                return parts[0]  # Return subdomain as site name
            return parts[0]  # Return main name
        return domain

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL."""
        # Remove protocol
        domain = url.replace("https://", "").replace("http://", "")
        # Remove path
        domain = domain.split("/")[0]
        # Remove www
        domain = domain.replace("www.", "")
        return domain


# Convenience function for quick searches
def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Quick web search function.

    Args:
        query: Search query
        max_results: Number of results

    Returns:
        List of dicts with title, snippet, url
    """
    tool = WebSearchTool(max_results=max_results)
    results = tool.search(query)
    return [{"title": r.title, "snippet": r.snippet, "url": r.url} for r in results]


if __name__ == "__main__":
    # Test the search tool
    tool = WebSearchTool()

    print("=" * 60)
    print("Testing Web Search Tool")
    print("=" * 60)

    # Test basic search
    results = tool.search("parabank demo website")
    print(f"\n🔍 Search: 'parabank demo website'")
    for r in results:
        print(f"  • {r.title}")
        print(f"    {r.snippet[:100]}...")
        print()

    # Test website info search
    print("\n" + "=" * 60)
    info = tool.search_website_info("https://parabank.parasoft.com")
    print(f"\n📊 Website Info for: {info['domain']}")
    print(f"   Total results: {info['num_results']}")
    print(f"   Context length: {len(info['combined_context'])} chars")
