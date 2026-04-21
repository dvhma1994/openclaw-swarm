"""
Example: Web Search
====================

This example shows how to use Web Search functionality.
"""

from openclaw_swarm import WebSearch


def main():
    print("=" * 60)
    print("OpenClaw Swarm - Web Search Example")
    print("=" * 60)
    
    # Create web search instance
    web = WebSearch()
    
    # 1. Search the web
    print("\n1. Basic Search")
    print("-" * 40)
    
    results = web.search("Python async programming", max_results=3)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.title}")
        print(f"   URL: {result.url}")
        if result.snippet:
            print(f"   Snippet: {result.snippet[:50]}...")
        print()
    
    # 2. Fetch a webpage
    print("\n2. Fetch Webpage")
    print("-" * 40)
    
    content = web.fetch("https://example.com")
    print(content[:500] + "..." if len(content) > 500 else content)
    
    # 3. Search and summarize
    print("\n3. Search and Summarize")
    print("-" * 40)
    
    summary = web.search_and_summarize("OpenAI GPT-4", max_results=3)
    
    print(f"Query: {summary['query']}")
    print(f"Results: {summary['results_count']}")
    
    for result in summary['results']:
        print(f"\n- {result['title']}")
        print(f"  {result['url']}")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()