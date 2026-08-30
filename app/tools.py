"""
Platform Tools
==============
"""

import json
import time
from os import getenv
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx
import sqlalchemy as sa
from agno.knowledge import Knowledge
from agno.tools import Toolkit
from agno.tools.file_generation import FileGenerationTools
from agno.tools.mcp import MCPTools
from agno.tools.openai import OpenAITools
from agno.tools.parallel import ParallelTools
from agno.tools.slack import SlackTools

from app.knowledge import product_knowledge
from db.url import build_db_url

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


class KnowledgeManagementTools(Toolkit):
    """Load a website or docs site into a knowledge base, one row per page with its source URL."""

    def __init__(self, knowledge: Knowledge, *, max_pages: int = DEFAULT_MAX_PAGES) -> None:
        self.knowledge = knowledge
        self.max_pages = max_pages
        super().__init__(
            name="knowledge_management",
            tools=[self.ingest_url, self.list_content],
        )

    async def ingest_url(self, url: str, max_pages: int | None = None) -> str:
        """Ingest a website or docs site into the knowledge base, one row per page with its source URL.

        Discovers pages from the site's sitemap.xml (a sitemap index is followed) up to page_cap, in sitemap order.
        A site without a sitemap gets the one page at `url`. Re-running refreshes pages already loaded.

        Args:
            url: Any page of the product's docs or website, e.g. https://docs.example.com. Prefer the docs subdomain.
            max_pages: Maximum pages to ingest (default 50, hard cap 500). Coverage beats selection.

        Returns:
            JSON: ok, route (parallel or website_reader), pages, failed, chars, seconds, and a sample of page names.
        """
        parsed = urlparse(url if "://" in url else f"https://{url}")
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return json.dumps({"ok": False, "error": f"not an http(s) URL: {url}"})
        cap = max(1, min(int(max_pages if max_pages is not None else self.max_pages), HARD_MAX_PAGES))
        root = f"{parsed.scheme}://{parsed.netloc}"
        start = time.monotonic()
        urls = _sitemap_urls(root, cap)
        used_sitemap = bool(urls)
        if not urls:
            urls = [parsed.geturl()]
        route, pages, failed = await _extract(urls, parsed.netloc)
        for page_url, title, content in pages:
            page = urlparse(page_url)
            await self.knowledge.ainsert(
                name=f"{page.netloc}/{page.path.strip('/') or 'index'}",
                text_content=f"# {title}\nSource: {page_url}\n\n{content}",
                metadata={"url": page_url, "title": title, "source": "product-site", "host": parsed.netloc},
            )
        return json.dumps(
            {
                "ok": True,
                "route": route,
                "sitemap": used_sitemap,
                "pages": len(pages),
                "failed": failed,
                "chars": sum(len(c) for _, _, c in pages),
                "seconds": round(time.monotonic() - start, 1),
                "sample": [f"{urlparse(u).netloc}/{urlparse(u).path.strip('/') or 'index'}" for u, _, _ in pages[:5]],
            }
        )

    def list_content(self, host: str | None = None, limit: int = 50) -> str:
        """List what the knowledge base holds, grouped by site.

        Args:
            host: Only list this host's pages, e.g. docs.example.com.
            limit: Maximum page names listed per site.

        Returns:
            JSON: sites, each with name, pages, and a sample of page names. Empty when nothing is ingested yet.
        """
        table = getattr(self.knowledge.vector_db, "table_name", "product_knowledge")
        engine = sa.create_engine(build_db_url())
        with engine.connect() as conn:
            rows = conn.execute(
                sa.text(f"select metadata->>'host', name from ai.{table}_contents order by 1, 2")
            ).fetchall()
        by_host: dict[str, list[str]] = {}
        for row_host, name in rows:
            by_host.setdefault(row_host or "unknown", []).append(name)
        if host is not None:
            by_host = {h: n for h, n in by_host.items() if h == host}
        return json.dumps(
            {
                "sites": [{"name": h, "pages": len(n), "sample": n[: max(1, int(limit))]} for h, n in by_host.items()],
                "other": [],
            }
        )


def get_knowledge_management_tools() -> KnowledgeManagementTools:
    return KnowledgeManagementTools(knowledge=product_knowledge)
