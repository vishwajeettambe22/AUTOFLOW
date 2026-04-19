import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import structlog

log = structlog.get_logger()

MAX_RESULTS = 5
MAX_CONTENT_CHARS = 3000


async def web_search(query: str) -> str:
    """
    Search the web using DuckDuckGo and return summarized results.
    Returns empty string on failure (Critic will handle it).
    """
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=MAX_RESULTS):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })

        if not results:
            log.warning("web_search_empty", query=query)
            return ""

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"[{i}] {r['title']}\nURL: {r['url']}\n{r['snippet']}\n"
            )

        return "\n".join(formatted)

    except Exception as e:
        log.error("web_search_failed", query=query, error=str(e))
        return ""


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
