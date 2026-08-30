"""
Product Ingestion
=================

Loads a product's website or docs into the product knowledge base, one row per
page with the source URL kept: sitemap discovery (indexes followed), Parallel
Extract when PARALLEL_API_KEY is set, page-by-page WebsiteReader otherwise.
Mounted on Platform Builder so a product agent can be built at runtime; the
create-agent skill calls the same function from the command line.
"""

import json
import time
from os import getenv
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx
import sqlalchemy as sa
from agno.tools import Toolkit

from app.knowledge import product_knowledge
from db.url import build_db_url

DEFAULT_PAGE_CAP = 50
MAX_PAGE_CAP = 200
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


class ProductIngestTools(Toolkit):
    """Load a product's docs into the product knowledge base."""

    def __init__(self) -> None:
        super().__init__(
            name="product_ingest",
            tools=[self.ingest_product_docs, self.list_product_sources],
        )

    async def ingest_product_docs(self, url: str, page_cap: int = DEFAULT_PAGE_CAP) -> str:
        """Ingest a product's website or docs into the product knowledge base, one row per page with its source URL.

        Discovers pages from the site's sitemap.xml (a sitemap index is followed) up to page_cap, in sitemap order.
        A site without a sitemap gets the one page at `url`. Re-running refreshes pages already loaded.

        Args:
            url: Any page of the product's docs or website, e.g. https://docs.example.com. Prefer the docs subdomain.
            page_cap: Maximum pages to ingest (default 50, hard cap 200). Coverage beats selection.

        Returns:
            JSON: ok, route (parallel or website_reader), pages, failed, chars, seconds, and a sample of page names.
        """
        parsed = urlparse(url if "://" in url else f"https://{url}")
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return json.dumps({"ok": False, "error": f"not an http(s) URL: {url}"})
        cap = max(1, min(int(page_cap), MAX_PAGE_CAP))
        root = f"{parsed.scheme}://{parsed.netloc}"
        start = time.monotonic()
        urls = _sitemap_urls(root, cap)
        used_sitemap = bool(urls)
        if not urls:
            urls = [parsed.geturl()]
        route, pages, failed = await _extract(urls, parsed.netloc)
        for page_url, title, content in pages:
            page = urlparse(page_url)
            await product_knowledge.ainsert(
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

    def list_product_sources(self) -> str:
        """List what the product knowledge base holds: hosts, page counts, and the first page names per host.

        Returns:
            JSON: total pages and a per-host breakdown. Empty when nothing has been ingested yet.
        """
        engine = sa.create_engine(build_db_url())
        with engine.connect() as conn:
            rows = conn.execute(
                sa.text("select metadata->>'host', name from ai.product_knowledge_contents order by 1, 2")
            ).fetchall()
        by_host: dict[str, list[str]] = {}
        for host, name in rows:
            by_host.setdefault(host or "unknown", []).append(name)
        return json.dumps(
            {
                "total_pages": len(rows),
                "hosts": [{"host": h, "pages": len(n), "sample": n[:5]} for h, n in by_host.items()],
            }
        )
