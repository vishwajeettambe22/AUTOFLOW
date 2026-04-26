import httpx
from bs4 import BeautifulSoup
import structlog

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

log = structlog.get_logger()

MAX_RESULTS = 5
MAX_CONTENT_CHARS = 3000


async def web_search(query: str) -> str:
    """
    Search the web using DuckDuckGo and return summarized results.
    Returns formatted string or fallback message on failure.
    """
    try:
        raw_results = []
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=MAX_RESULTS))

        if not raw_results:
            log.warning("web_search_empty", query=query)
            return "No search results found for the query."

        results = []
        for r in raw_results:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })

        formatted_data = "\n".join([
            f"{r['title']} - {r['snippet']}" for r in results if r.get("snippet")
        ])
        
        log.info("web_search_success", num_results=len(results), formatted_len=len(formatted_data))

        return formatted_data

    except Exception as e:
        log.error("web_search_failed", query=query, error=str(e))
        return f"Search failed due to an error: {str(e)}"


async def fetch_page(url: str) -> str:
    """Fetch and extract text from a URL."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            # Remove scripts, styles, nav
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            return text[:MAX_CONTENT_CHARS]
    except Exception as e:
        log.warning("fetch_page_failed", url=url, error=str(e))
        return ""
