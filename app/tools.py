"""
Platform Tools
==============
"""

from os import getenv

from agno.tools.file_generation import FileGenerationTools
from agno.tools.knowledge_management import KnowledgeManagementTools
from agno.tools.mcp import MCPTools
from agno.tools.openai import OpenAITools
from agno.tools.parallel import ParallelTools
from agno.tools.slack import SlackTools

from app.knowledge import product_knowledge

AGNO_DOCS_MCP_URL = "https://docs.agno.com/mcp"


def get_agno_docs_tools() -> list[MCPTools]:
    return [MCPTools(transport="streamable-http", url=AGNO_DOCS_MCP_URL, name="agno_docs")]


def get_parallel_tools() -> list[ParallelTools | MCPTools]:
    if getenv("PARALLEL_API_KEY"):
        return [ParallelTools()]
    # timeout_seconds: web_fetch page extraction regularly exceeds the 10s MCP default.
    return [
        MCPTools(
            url="https://search.parallel.ai/mcp", transport="streamable-http", name="parallel_tools", timeout_seconds=30
        )
    ]


def get_slack_tools() -> list[SlackTools]:
    """Send-scoped Slack toolkit, only when the Slack interface is configured.

    Deliberately narrower than the SlackTools defaults: a registry any agent
    can draw from gets post + channel listing, never history reads or file transfer.
    """
    if not getenv("SLACK_BOT_TOKEN"):
        return []
    return [
        SlackTools(
            token=getenv("SLACK_BOT_TOKEN"),
            enable_send_message=True,
            enable_send_message_thread=True,
            enable_list_channels=True,
            enable_get_channel_history=False,
            enable_upload_file=False,
            enable_download_file=False,
        )
    ]


def get_media_tools() -> list[OpenAITools]:
    """Image generation and text-to-speech on the platform's existing OpenAI key.

    Generated media come back as run artifacts (bytes on the RunResponse), so they
    persist in Postgres and survive ephemeral container filesystems. Transcription
    stays off: transcribe_audio reads server-local file paths, which agents on this
    platform never have.
    """
    # OpenAITools raises without the key; the registry import must not.
    if not getenv("OPENAI_API_KEY"):
        return []
    return [OpenAITools(enable_transcription=False, image_model="gpt-image-2")]


def get_file_generation_tools() -> list[FileGenerationTools]:
    """Downloadable files (JSON, CSV, TXT, HTML, code) as in-memory run artifacts."""
    return [FileGenerationTools(enable_pdf_generation=False, enable_docx_generation=False)]


DEFAULT_MAX_PAGES = 50
HARD_MAX_PAGES = 500
PARALLEL_BATCH = 8


def _sitemap_urls(root: str, cap: int) -> list[str]:
    """Page URLs from <root>/sitemap.xml, following a sitemap index into its children."""
    pending = [f"{root}/sitemap.xml"]
    pages: list[str] = []
    seen: set[str] = set()
    while pending and len(pages) < cap:
        sitemap = pending.pop(0)
        if sitemap in seen:
            continue
        seen.add(sitemap)
        try:
            response = httpx.get(sitemap, timeout=30, follow_redirects=True)
            response.raise_for_status()
            tree = ElementTree.fromstring(response.text)
        except httpx.HTTPError, ElementTree.ParseError:
            continue
        locs = [e.text.strip() for e in tree.iter() if e.tag.endswith("loc") and e.text]
        if tree.tag.endswith("sitemapindex"):
            pending.extend(locs)
        else:
            pages.extend(locs)
    return pages[:cap]


async def _extract(urls: list[str], host: str) -> tuple[str, list[tuple[str, str, str]], int]:
    """(route, [(url, title, content)], failed) — Parallel Extract with a key, page-by-page WebsiteReader without.

    A page that cannot be read is counted and skipped; one bad page must not abort the ingest.
    """
    pages: list[tuple[str, str, str]] = []
    failed = 0
    if getenv("PARALLEL_API_KEY"):
        from agno.tools.parallel import ParallelTools

        tools = ParallelTools()
        for i in range(0, len(urls), PARALLEL_BATCH):
            batch = urls[i : i + PARALLEL_BATCH]
            try:
                results = json.loads(tools.parallel_extract(urls=batch, full_content=True)).get("results") or []
            except Exception:
                failed += len(batch)
                continue
            for page in results:
                content = page.get("full_content") or "\n".join(page.get("excerpts") or [])
                if page.get("url") and content:
                    title = page.get("title") or urlparse(page["url"]).path.strip("/")
                    pages.append((page["url"], str(title), content))
            failed += len(batch) - len(results)
        return "parallel", pages, failed

    from agno.knowledge.reader.website_reader import WebsiteReader

    # max_depth=1, max_links=1 reads the one page; crawling from the root lands the site as one row.
    reader = WebsiteReader(max_depth=1, max_links=1, allowed_hosts=[host])
    for url in urls:
        try:
            docs = await reader.async_read(url)
        except Exception:
            failed += 1
            continue
        content = "\n\n".join(d.content for d in docs if d.content)
        if content:
            title = docs[0].name if docs and docs[0].name else urlparse(url).path.strip("/")
            pages.append((url, str(title), content))
        else:
            failed += 1
    return "website_reader", pages, failed


def get_knowledge_management_tools() -> KnowledgeManagementTools:
    """The write side of the product knowledge base, mounted on Platform Builder."""
    return KnowledgeManagementTools(knowledge=product_knowledge)
