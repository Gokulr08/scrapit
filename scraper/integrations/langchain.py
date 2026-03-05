"""
LangChain integration for Scrapit.

Works with LangChain agents, CrewAI, LangGraph, and any framework
that accepts LangChain-compatible tools.

Tools:
    ScrapitTool              — scrape any URL, returns clean text
    ScrapitPageTool          — scrape any URL, returns structured metadata
    ScrapitSelectorTool      — scrape a URL with agent-defined CSS selectors
    ScrapitDirectiveTool     — run a named directive, returns structured JSON

Toolkit:
    ScrapitToolkit           — all tools bundled, plug into any agent

Document Loader:
    ScrapitLoader            — load scraped content as LangChain Documents

Usage:

    from scraper.integrations.langchain import ScrapitToolkit

    tools = ScrapitToolkit().get_tools()
    # → [ScrapitTool, ScrapitPageTool, ScrapitSelectorTool]

    # Or individually:
    from scraper.integrations.langchain import ScrapitTool, ScrapitSelectorTool
"""

from __future__ import annotations

import json
from typing import Any

from scraper.integrations import (
    scrape_url,
    scrape_page,
    scrape_with_selectors,
    scrape_directive,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _dict_to_text(data: dict) -> str:
    """Convert a scraped dict to readable text for LLM consumption."""
    skip = {"url", "timestamp", "_id", "_page", "_source", "_valid", "_errors", "ok"}
    lines = []
    for key, value in data.items():
        if key in skip or value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}: {', '.join(str(v) for v in value)}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


# ── ScrapitTool ───────────────────────────────────────────────────────────────

class ScrapitTool:
    """
    Scrape any URL and return clean text.

    Input: a URL string.
    Output: readable page text with scripts/nav/footer removed.
    """

    name: str = "scrapit_scrape_url"
    description: str = (
        "Fetch a web page and return its clean readable text content. "
        "Use this to read articles, documentation, or any static web page. "
        "Input: a valid URL (http:// or https://). "
        "Output: the page text, cleaned of navigation and scripts."
    )

    def run(self, url: str, **kwargs) -> str:
        try:
            return scrape_url(url.strip())
        except Exception as e:
            return f"Error scraping {url}: {e}"

    def _run(self, url: str, **kwargs) -> str:
        return self.run(url)

    async def _arun(self, url: str, **kwargs) -> str:
        import asyncio
        return await asyncio.to_thread(self.run, url)

    def as_langchain(self):
        from langchain.tools import Tool  # type: ignore
        return Tool(name=self.name, func=self.run, description=self.description)


# ── ScrapitPageTool ───────────────────────────────────────────────────────────

class ScrapitPageTool:
    """
    Scrape any URL and return structured page metadata as JSON.

    Returns title, description, main_content, links, and word_count.
    More useful than ScrapitTool when the agent needs structured context.
    """

    name: str = "scrapit_scrape_page"
    description: str = (
        "Fetch a web page and return structured metadata: "
        "title, meta description, main content text, all outbound links, and word count. "
        "Prefer this over scrapit_scrape_url when you need to know the page title, "
        "find links, or get a quick summary of what the page contains. "
        "Input: a valid URL. Output: JSON with title, description, main_content, links, word_count."
    )

    def run(self, url: str, **kwargs) -> str:
        try:
            page = scrape_page(url.strip())
            # Truncate main_content for agent context window
            page["main_content"] = page["main_content"][:4000]
            page["links"] = page["links"][:30]  # top 30 links
            return json.dumps(page, indent=2, default=str)
        except Exception as e:
            return f"Error fetching page {url}: {e}"

    def _run(self, url: str, **kwargs) -> str:
        return self.run(url)

    async def _arun(self, url: str, **kwargs) -> str:
        import asyncio
        return await asyncio.to_thread(self.run, url)


# ── ScrapitSelectorTool ───────────────────────────────────────────────────────

class ScrapitSelectorTool:
    """
    Scrape specific fields from a URL using CSS selectors — no YAML needed.

    The agent defines exactly what to extract on-the-fly.
    Input: JSON string with {"url": "...", "selectors": {"field": "css-selector"}}.
    """

    name: str = "scrapit_scrape_selectors"
    description: str = (
        "Scrape specific fields from a web page using CSS selectors. "
        "Use this when you know which elements to extract from a page. "
        "Input must be a JSON string with two keys:\n"
        '  "url": the page URL\n'
        '  "selectors": a dict mapping field names to CSS selectors\n'
        "Example input: "
        '{"url": "https://example.com", "selectors": {"title": "h1", "price": ".price"}}\n'
        "Output: JSON with the extracted values."
    )

    def run(self, input_str: str, **kwargs) -> str:
        try:
            data = json.loads(input_str) if isinstance(input_str, str) else input_str
            url = data["url"]
            selectors = data["selectors"]
            result = scrape_with_selectors(url, selectors)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return f"Error: {e}. Input must be JSON: {{\"url\": \"...\", \"selectors\": {{\"field\": \"selector\"}}}}"

    def _run(self, input_str: str, **kwargs) -> str:
        return self.run(input_str)

    async def _arun(self, input_str: str, **kwargs) -> str:
        import asyncio
        return await asyncio.to_thread(self.run, input_str)


# ── ScrapitDirectiveTool ──────────────────────────────────────────────────────

class ScrapitDirectiveTool:
    """
    Run a pre-configured Scrapit directive by name.

    Returns structured JSON — useful when the agent needs specific fields
    from a site that already has a YAML directive configured.
    """

    name: str = "scrapit_directive"
    description: str = (
        "Run a Scrapit directive to scrape a website with a predefined configuration. "
        "Returns structured JSON with the scraped fields. "
        "Input: directive name (e.g. 'wikipedia') or path to a YAML file."
    )

    def __init__(self, directive: str | None = None):
        self.default_directive = directive
        if directive:
            self.name = f"scrapit_{directive}"
            self.description = (
                f"Scrape data using the '{directive}' directive. "
                "Returns structured JSON with the pre-configured scraped fields."
            )

    def run(self, directive: str | None = None, **kwargs) -> str:
        target = directive or self.default_directive
        if not target:
            return "Error: no directive specified."
        try:
            result = scrape_directive(target.strip())
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return f"Error running directive '{target}': {e}"

    def _run(self, directive: str | None = None, **kwargs) -> str:
        return self.run(directive)

    async def _arun(self, directive: str | None = None, **kwargs) -> str:
        import asyncio
        return await asyncio.to_thread(self.run, directive)


# ── ScrapitToolkit ────────────────────────────────────────────────────────────

class ScrapitToolkit:
    """
    All Scrapit tools bundled — plug directly into any LangChain agent.

    Usage:

        from scraper.integrations.langchain import ScrapitToolkit
        from langchain.agents import initialize_agent, AgentType
        from langchain_openai import ChatOpenAI

        tools = ScrapitToolkit().get_tools()

        agent = initialize_agent(
            tools=tools,
            llm=ChatOpenAI(model="gpt-4o"),
            agent=AgentType.OPENAI_FUNCTIONS,
        )
        agent.run("What are the top stories on Hacker News right now?")

    With CrewAI:

        from crewai import Agent
        tools = ScrapitToolkit().get_tools()
        researcher = Agent(role="Researcher", tools=tools, ...)
    """

    def __init__(self, directives: list[str] | None = None):
        """
        Args:
            directives: Optional list of directive names to include as extra tools.
        """
        self.directives = directives or []

    def get_tools(self) -> list:
        """Return all Scrapit tools as a list."""
        tools = [
            ScrapitTool(),
            ScrapitPageTool(),
            ScrapitSelectorTool(),
        ]
        for d in self.directives:
            tools.append(ScrapitDirectiveTool(directive=d))
        return tools

    def get_langchain_tools(self) -> list:
        """Return native langchain Tool objects (requires langchain installed)."""
        from langchain.tools import Tool  # type: ignore
        result = []
        for t in self.get_tools():
            result.append(Tool(name=t.name, func=t.run, description=t.description))
        return result


# ── ScrapitLoader ─────────────────────────────────────────────────────────────

class ScrapitLoader:
    """
    LangChain Document Loader — load scraped content as Document objects.

    Supports URL mode and directive mode.
    Compatible with LangChain's ingestion pipeline and text splitters.

    Usage (RAG pipeline):

        from scraper.integrations.langchain import ScrapitLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        loader = ScrapitLoader("https://example.com")
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
        chunks = splitter.split_documents(docs)
    """

    def __init__(self, source: str, mode: str = "auto"):
        """
        Args:
            source: A URL or directive name/path.
            mode: 'url', 'directive', or 'auto' (default: inferred from source).
        """
        self.source = source
        self.mode = mode

    def load(self) -> list:
        Document = _import_document()
        mode = self._detect_mode()

        if mode == "url":
            page = scrape_page(self.source)
            content = page["main_content"]
            metadata = {
                "source": self.source,
                "title": page.get("title", ""),
                "description": page.get("description", ""),
                "word_count": page.get("word_count", 0),
            }
            return [Document(page_content=content, metadata=metadata)]

        result = scrape_directive(self.source)
        results = result if isinstance(result, list) else [result]
        docs = []
        for item in results:
            content = _dict_to_text(item)
            metadata = {
                "source": item.get("url", self.source),
                "timestamp": str(item.get("timestamp", "")),
                "directive": self.source,
            }
            docs.append(Document(page_content=content, metadata=metadata))
        return docs

    def lazy_load(self):
        yield from self.load()

    def _detect_mode(self) -> str:
        if self.mode != "auto":
            return self.mode
        return "url" if self.source.startswith(("http://", "https://")) else "directive"


def _import_document():
    try:
        from langchain_core.documents import Document  # type: ignore
        return Document
    except ImportError:
        try:
            from langchain.schema import Document  # type: ignore
            return Document
        except ImportError:
            raise ImportError(
                "langchain or langchain-core is required. "
                "Install with: pip install langchain-core"
            )
