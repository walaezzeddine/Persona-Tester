"""
Website Analyzer - LLM 1 (crawl4ai-powered)
Analyzes a website to understand its structure, features, and target audience.

Pipeline
--------
1. Crawl the homepage + a handful of internal pages with crawl4ai
   (real headless browser → SPA-safe, with pruning + overlay/cookie removal).
2. Stitch the pruned markdown of all pages into a compact "site brief".
3. Ask the LLM to turn the brief into a structured JSON analysis AND a
   persona-generator-friendly markdown context (`llm_context`).

Output: Dict with the legacy JSON schema PLUS:
   - `llm_context`           — compact markdown brief for downstream LLM prompts
   - `pages_crawled`         — list of {url, title, word_count}
   - `crawl_engine`          — "crawl4ai" | "fallback"

If `crawl4ai` is not installed or the crawl fails, falls back to the previous
urllib + HTMLParser + DuckDuckGo path so existing deployments keep working.
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Tuple, Optional
from urllib.parse import urlparse, urljoin
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .web_search_tool import WebSearchTool

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    from crawl4ai.content_filter_strategy import PruningContentFilter
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False


# Per-page markdown budget when building the stitched site brief.
# Keeps the final LLM prompt within a sane token window even for content-heavy pages.
_PER_PAGE_MARKDOWN_CHARS = 2500
_MAX_INTERNAL_PAGES = 4  # homepage + up to 3 internal pages


class WebsiteAnalyzer:
    """
    LLM-powered website analyzer that:
    1. Crawls the website with crawl4ai (real browser, JS-aware, pruned markdown)
    2. Builds a compact, LLM-friendly site brief across the homepage and key internal pages
    3. Synthesizes a rich JSON analysis + a `llm_context` markdown field for the persona generator
    """

    def __init__(
        self,
        provider: str = "openai",
        model: str = None,
        temperature: float = 0.4,
        enable_web_search: bool = False,
        max_internal_pages: int = _MAX_INTERNAL_PAGES,
    ):
        """
        Args:
            provider: LLM provider ('ollama', 'openai', 'github', 'google')
            model: Model name (defaults per provider)
            temperature: LLM temperature for the synthesis step (keep low for factuality)
            enable_web_search: Optional DDG enrichment for sites that block crawling
            max_internal_pages: Cap on pages fetched during the shallow deep crawl
        """
        self.provider = provider
        self.temperature = temperature
        self.llm = self._init_llm(provider, model)
        self.enable_web_search = enable_web_search
        self.web_search = WebSearchTool(max_results=3) if enable_web_search else None
        self.max_internal_pages = max(1, int(max_internal_pages))

    # ──────────────────────────────────────────────────────────────────────
    # LLM initialization
    # ──────────────────────────────────────────────────────────────────────

    def _init_llm(self, provider: str, model: str = None) -> ChatOpenAI:
        if provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            return ChatOpenAI(
                model=model or os.getenv("OLLAMA_MODEL", "qwen3.5:cloud"),
                base_url=base_url,
                api_key="ollama",
                temperature=self.temperature,
                max_tokens=3000,
            )
        if provider == "google":
            google_key = os.getenv("GOOGLE_API_KEY")
            if not google_key:
                raise ValueError("GOOGLE_API_KEY not set in .env")
            return ChatGoogleGenerativeAI(
                model=model or "gemini-1.5-flash",
                google_api_key=google_key,
                temperature=self.temperature,
                max_output_tokens=3000,
            )
        elif provider == "github":
            api_key = os.getenv("GITHUB_TOKEN")
            if not api_key:
                raise ValueError("GITHUB_TOKEN not set in .env")
            return ChatOpenAI(
                model=model or "gpt-4o-mini",
                base_url="https://models.github.ai/inference",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=3000,
            )
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in .env")
            return ChatOpenAI(
                model=model or "gpt-4o-mini",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=3000,
            )

    # ──────────────────────────────────────────────────────────────────────
    # Public entry point
    # ──────────────────────────────────────────────────────────────────────

    def analyze(self, url: str, enable_scraping: bool = True) -> Dict[str, Any]:
        """
        Analyze a website and return a structured description plus an
        LLM-friendly markdown context.
        """
        print(f"🔍 Analyzing website: {url}")
        parsed = urlparse(url)
        domain = parsed.netloc or url

        crawl_engine = "disabled"
        site_brief = ""
        pages_crawled: List[Dict[str, Any]] = []

        if enable_scraping:
            if CRAWL4AI_AVAILABLE:
                try:
                    site_brief, pages_crawled = asyncio.run(self._crawl_with_crawl4ai(url))
                    crawl_engine = "crawl4ai" if site_brief else "crawl4ai-empty"
                except RuntimeError as e:
                    # Happens if we're already inside a running event loop; fall through.
                    print(f"⚠️  crawl4ai run failed ({e}); falling back to legacy scraper")
                    crawl_engine = "fallback"
                except Exception as e:
                    print(f"⚠️  crawl4ai error: {e}; falling back to legacy scraper")
                    crawl_engine = "fallback"
            else:
                print("ℹ️  crawl4ai not installed — using legacy scraper")
                crawl_engine = "fallback"

            if not site_brief:
                legacy_text, legacy_ok = self._legacy_fetch(url)
                if legacy_ok:
                    site_brief = self._format_legacy_brief(url, domain, legacy_text)
                    pages_crawled = [{"url": url, "title": domain, "word_count": len(legacy_text.split())}]
                    if crawl_engine == "disabled":
                        crawl_engine = "fallback"
        else:
            print("ℹ️  Scraping disabled — URL-only analysis")
            crawl_engine = "disabled"

        # Optional DDG enrichment — only really useful when crawling produced nothing.
        web_search_context = ""
        if self.enable_web_search and self.web_search and (not site_brief or crawl_engine == "disabled"):
            try:
                search_info = self.web_search.search_website_info(url)
                web_search_context = search_info.get("combined_context", "")
                print(f"   ✓ DDG enrichment: {search_info.get('num_results', 0)} results")
            except Exception as e:
                print(f"   ⚠️ Web search failed: {e}")

        analysis = self._synthesize(
            url=url,
            domain=domain,
            site_brief=site_brief,
            web_search_context=web_search_context,
        )

        analysis["pages_crawled"] = pages_crawled
        analysis["crawl_engine"] = crawl_engine
        analysis["scraping_enabled"] = enable_scraping
        analysis["scraping_successful"] = bool(site_brief)
        analysis["web_search_enabled"] = self.enable_web_search
        analysis["analysis_type"] = (
            "crawl4ai" if crawl_engine == "crawl4ai"
            else "fallback-scraper" if crawl_engine == "fallback"
            else "url-based"
        )
        return analysis

    # ──────────────────────────────────────────────────────────────────────
    # crawl4ai fetch
    # ──────────────────────────────────────────────────────────────────────

    async def _crawl_with_crawl4ai(self, url: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Crawl the homepage + up to N internal pages, pruning boilerplate and
        returning a single stitched markdown brief.
        """
        browser_config = BrowserConfig(
            headless=True,
            java_script_enabled=True,
            verbose=False,
        )

        md_generator = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.45, threshold_type="fixed")
        )

        run_config = CrawlerRunConfig(
            markdown_generator=md_generator,
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=20,
            excluded_tags=["script", "style", "nav", "footer", "aside", "noscript"],
            remove_overlay_elements=True,
            exclude_external_links=True,
            page_timeout=25000,
        )

        pages: List[Dict[str, Any]] = []

        async with AsyncWebCrawler(config=browser_config) as crawler:
            root_result = await crawler.arun(url=url, config=run_config)
            if not getattr(root_result, "success", False):
                return "", []

            root_md = self._best_markdown(root_result)
            root_title = self._safe_title(root_result, url)
            pages.append({
                "url": url,
                "title": root_title,
                "word_count": len(root_md.split()),
                "markdown": root_md[:_PER_PAGE_MARKDOWN_CHARS],
            })

            internal = self._pick_internal_links(root_result, url, self.max_internal_pages - 1)
            print(f"   ✓ Homepage fetched ({len(root_md)} chars). Following {len(internal)} internal pages…")

            for link in internal:
                try:
                    sub_result = await crawler.arun(url=link, config=run_config)
                    if not getattr(sub_result, "success", False):
                        continue
                    md = self._best_markdown(sub_result)
                    if not md or len(md.split()) < 40:
                        continue
                    pages.append({
                        "url": link,
                        "title": self._safe_title(sub_result, link),
                        "word_count": len(md.split()),
                        "markdown": md[:_PER_PAGE_MARKDOWN_CHARS],
                    })
                except Exception as e:
                    print(f"   ⚠️ Could not crawl {link}: {e}")

        brief = self._build_site_brief(url, pages)
        # Strip the per-page markdown from the returned metadata to keep it DB-friendly.
        meta = [{k: v for k, v in p.items() if k != "markdown"} for p in pages]
        return brief, meta

    @staticmethod
    def _best_markdown(result: Any) -> str:
        """Prefer pruned `fit_markdown`, fall back to `raw_markdown`, then plain string."""
        md_obj = getattr(result, "markdown", None)
        if md_obj is None:
            return ""
        if isinstance(md_obj, str):
            return md_obj
        fit = getattr(md_obj, "fit_markdown", None)
        if fit:
            return fit
        raw = getattr(md_obj, "raw_markdown", None)
        if raw:
            return raw
        return str(md_obj)

    @staticmethod
    def _safe_title(result: Any, fallback: str) -> str:
        meta = getattr(result, "metadata", None) or {}
        title = meta.get("title") if isinstance(meta, dict) else None
        return (title or fallback).strip()[:120]

    def _pick_internal_links(self, result: Any, base_url: str, limit: int) -> List[str]:
        """
        Pick up to `limit` internal links that look useful for understanding
        the site's functionality (login, pricing, products, about, features, etc).
        """
        if limit <= 0:
            return []

        links_obj = getattr(result, "links", None) or {}
        internal_links = links_obj.get("internal", []) if isinstance(links_obj, dict) else []

        parsed_base = urlparse(base_url)
        base_host = parsed_base.netloc.lower()

        # Priority keywords — pages most likely to describe user-facing functionality.
        priority_keywords = [
            "login", "sign-in", "signin", "register", "sign-up", "signup",
            "pricing", "plans", "product", "feature", "service", "shop",
            "cart", "checkout", "account", "dashboard", "docs", "how-it-works",
            "about", "faq", "help", "support",
        ]

        scored: List[Tuple[int, str]] = []
        seen = set()
        for item in internal_links:
            href = item.get("href") if isinstance(item, dict) else str(item)
            if not href:
                continue
            full = urljoin(base_url, href).split("#")[0].rstrip("/")
            if not full or full == base_url.rstrip("/"):
                continue
            if full in seen:
                continue
            parsed = urlparse(full)
            if parsed.netloc and parsed.netloc.lower() != base_host:
                continue
            seen.add(full)

            lower = full.lower()
            score = sum(2 for kw in priority_keywords if kw in lower)
            # Prefer shorter paths (closer to root = usually more informative hubs).
            path_depth = len([p for p in parsed.path.split("/") if p])
            score -= path_depth
            scored.append((score, full))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [url for _, url in scored[:limit]]

    @staticmethod
    def _build_site_brief(root_url: str, pages: List[Dict[str, Any]]) -> str:
        """Stitch per-page markdown into one brief the LLM can reason over."""
        if not pages:
            return ""
        chunks: List[str] = [f"# Site snapshot for {root_url}", ""]
        for i, page in enumerate(pages, 1):
            chunks.append(f"## Page {i}: {page['title']}")
            chunks.append(f"_URL: {page['url']} — ~{page['word_count']} words_")
            chunks.append("")
            chunks.append(page.get("markdown", "").strip())
            chunks.append("")
        return "\n".join(chunks).strip()

    # ──────────────────────────────────────────────────────────────────────
    # Legacy fetch — kept as a safety net
    # ──────────────────────────────────────────────────────────────────────

    def _legacy_fetch(self, url: str, timeout: int = 10) -> Tuple[str, bool]:
        from urllib.request import urlopen, Request
        import ssl

        print(f"📥 Legacy fetch: {url}")
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=timeout, context=context) as response:
                content = response.read(50000)
                return self._html_to_text(content.decode("utf-8", errors="ignore")), True
        except Exception as e:
            print(f"⚠️  urllib failed: {e}")

        try:
            import requests
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                return self._html_to_text(resp.text[:50000]), True
            print(f"⚠️  HTTP {resp.status_code}")
        except ImportError:
            print("⚠️  requests library not available")
        except Exception as e:
            print(f"⚠️  requests failed: {e}")
        return "", False

    @staticmethod
    def _html_to_text(html: str) -> str:
        try:
            from html.parser import HTMLParser

            class Extractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.parts: List[str] = []
                    self.skip = False

                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style"):
                        self.skip = True

                def handle_endtag(self, tag):
                    if tag in ("script", "style"):
                        self.skip = False

                def handle_data(self, data):
                    if not self.skip:
                        cleaned = data.strip()
                        if cleaned:
                            self.parts.append(cleaned)

            ex = Extractor()
            ex.feed(html)
            return "\n".join(ex.parts)[:3000]
        except Exception:
            import re
            text = re.sub(r"<[^>]+>", " ", html)
            return re.sub(r"\s+", " ", text)[:3000]

    @staticmethod
    def _format_legacy_brief(url: str, domain: str, text: str) -> str:
        return (
            f"# Site snapshot for {url}\n\n"
            f"## Page 1: {domain}\n"
            f"_URL: {url} — fallback scraper (no JS rendering)_\n\n"
            f"{text.strip()}"
        )

    # ──────────────────────────────────────────────────────────────────────
    # LLM synthesis
    # ──────────────────────────────────────────────────────────────────────

    def _synthesize(
        self,
        url: str,
        domain: str,
        site_brief: str,
        web_search_context: str,
    ) -> Dict[str, Any]:
        search_section = ""
        if web_search_context:
            search_section = (
                "**External web context (use to fill gaps only):**\n"
                f"{web_search_context[:1500]}\n\n---\n"
            )

        if not site_brief:
            site_brief = f"(No content could be fetched — analyze based on the URL only.)"

        # Truncate defensively to keep the prompt inside the LLM's window.
        site_brief = site_brief[:9000]

        prompt = f"""
You are profiling a website so that another LLM can generate realistic user personas and test scenarios.

**Website URL:** {url}
**Domain:** {domain}

{search_section}**Site snapshot (markdown extracted from a real browser crawl):**
{site_brief}

---

Return ONE JSON object with EXACTLY these keys:

{{
  "domain": "{domain}",
  "url": "{url}",
  "site_type": "e-commerce | banking | social | news | saas | demo | education | blog | travel | other",
  "primary_purpose": "One sentence: what END USERS come here to do.",
  "description": "2-3 sentences describing the site's real-world functionality.",
  "industry": "finance | retail | travel | media | health | education | tech | other",
  "pricing_model": "free | freemium | paid | subscription | marketplace | demo | unknown",
  "target_audience": [
    {{"segment": "name", "characteristics": "who they are", "motivation": "why they visit", "goals": ["goal1", "goal2"]}}
  ],
  "key_features": ["Feature 1 (grounded in the snapshot)", "Feature 2", "..."],
  "user_actions": ["login", "search", "add to cart", "transfer money", ...],
  "user_journey": {{
    "entry_point": "How users arrive",
    "key_steps": ["Step 1", "Step 2", "Step 3"],
    "conversion_goal": "What the site wants the user to accomplish"
  }},
  "forms_and_inputs": ["Login form (username/password)", "Search bar", "..."],
  "navigation_patterns": "Brief description of how users get around (top nav, sidebar, tabs, SPA, etc.)",
  "user_pain_points": ["Plausible frustration 1", "Plausible frustration 2"],
  "competitive_advantages": ["Advantage 1", "Advantage 2"],
  "design_style": "minimalist | modern | corporate | creative | cluttered | other",
  "estimated_audience_size": "large | medium | small",
  "llm_context": "A 300-500 word markdown brief written FOR a persona-generation LLM. Use these sections (keep the headings): ### Site Purpose\\n### Primary User Segments\\n### Key User Flows\\n### Forms & Inputs\\n### Navigation\\n### Likely Pain Points\\n### Test Scenario Hooks. Be concrete and grounded in the snapshot above. This field is the MOST IMPORTANT output — it will be pasted directly into another LLM's prompt."
}}

Rules:
- Ground everything in the snapshot. Do NOT invent features that aren't suggested by the content.
- If a field is genuinely unknowable, use "unknown" (string) or [] (list) — never make things up.
- `llm_context` MUST be valid markdown inside a JSON string (escape newlines as \\n).
- Return ONLY the JSON object, no prose, no code fence.
"""

        messages = [
            SystemMessage(content=(
                "You are a senior web analyst. You profile websites so that a "
                "persona-generation LLM downstream can produce realistic user "
                "personas and test scenarios grounded in the site's actual "
                "functionality. Always respond with a single valid JSON object."
            )),
            HumanMessage(content=prompt),
        ]

        try:
            print("🤖 Synthesizing analysis with LLM…")
            response = self.llm.invoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)
            analysis = self._extract_json(response_text)
            # Belt and suspenders: ensure url/domain are set correctly
            analysis["domain"] = analysis.get("domain") or domain
            analysis["url"] = analysis.get("url") or url
            # Ensure llm_context exists even if model omitted it
            if not analysis.get("llm_context"):
                analysis["llm_context"] = self._synthesize_fallback_context(analysis, site_brief)
            return analysis
        except Exception as e:
            print(f"❌ Synthesis failed: {e}")
            return self._minimal_fallback(url, domain, str(e), site_brief)

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """Robustly pull a JSON object out of an LLM response."""
        import re
        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if fenced:
            return json.loads(fenced.group(1))
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("No JSON object found in LLM response")
        return json.loads(match.group(0))

    @staticmethod
    def _synthesize_fallback_context(analysis: Dict[str, Any], site_brief: str) -> str:
        """Build a passable llm_context from structured fields when the LLM forgets it."""
        feats = analysis.get("key_features") or []
        actions = analysis.get("user_actions") or []
        segments = analysis.get("target_audience") or []
        pains = analysis.get("user_pain_points") or []
        journey = analysis.get("user_journey") or {}
        forms = analysis.get("forms_and_inputs") or []
        parts = [
            "### Site Purpose",
            analysis.get("primary_purpose") or analysis.get("description") or "Unknown.",
            "",
            "### Primary User Segments",
        ]
        for s in segments[:4]:
            if isinstance(s, dict):
                parts.append(f"- **{s.get('segment', 'user')}** — {s.get('characteristics', '')}. Goals: {', '.join(s.get('goals', []) or [])}")
            else:
                parts.append(f"- {s}")
        parts += ["", "### Key User Flows"]
        for step in (journey.get("key_steps") or actions[:5] or ["Browse the site"]):
            parts.append(f"- {step}")
        parts += ["", "### Forms & Inputs"]
        parts += [f"- {f}" for f in forms[:6]] or ["- (none detected)"]
        parts += ["", "### Navigation"]
        parts.append(analysis.get("navigation_patterns") or "Standard top navigation.")
        parts += ["", "### Likely Pain Points"]
        parts += [f"- {p}" for p in pains[:5]] or ["- Slow pages", "- Unclear labels"]
        parts += ["", "### Test Scenario Hooks"]
        parts += [f"- {f}" for f in feats[:5]] or ["- General browsing"]
        return "\n".join(parts)

    @staticmethod
    def _minimal_fallback(url: str, domain: str, err: str, site_brief: str) -> Dict[str, Any]:
        return {
            "domain": domain,
            "url": url,
            "site_type": "other",
            "primary_purpose": f"Website at {domain}",
            "description": f"Could not synthesize a full analysis ({err}).",
            "industry": "unknown",
            "pricing_model": "unknown",
            "target_audience": [
                {"segment": "general visitor", "characteristics": "unknown", "motivation": "unknown", "goals": []}
            ],
            "key_features": [],
            "user_actions": ["browse", "navigate"],
            "user_journey": {"entry_point": "homepage", "key_steps": [], "conversion_goal": "unknown"},
            "forms_and_inputs": [],
            "navigation_patterns": "unknown",
            "user_pain_points": [],
            "competitive_advantages": [],
            "design_style": "unknown",
            "estimated_audience_size": "unknown",
            "llm_context": (
                f"### Site Purpose\nUnknown — analyzer could not synthesize details.\n\n"
                f"### Notes\nError: {err}\n\n"
                f"### Raw snapshot (truncated)\n{site_brief[:1200] if site_brief else '(empty)'}"
            ),
            "error": err,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Utilities
    # ──────────────────────────────────────────────────────────────────────

    def save_analysis(self, analysis: Dict[str, Any], output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"✅ Analysis saved to {output_path}")

    def print_analysis(self, analysis: Dict[str, Any]) -> None:
        print("\n" + "=" * 80)
        print(f"Website Analysis: {analysis.get('domain', 'Unknown')}")
        print("=" * 80)
        for key in [
            "site_type",
            "primary_purpose",
            "pricing_model",
            "key_features",
            "user_actions",
            "target_audience",
            "estimated_audience_size",
            "crawl_engine",
        ]:
            if key in analysis:
                value = analysis[key]
                if isinstance(value, str):
                    print(f"📌 {key.replace('_', ' ').title()}: {value}")
                elif isinstance(value, list):
                    print(f"📌 {key.replace('_', ' ').title()}:")
                    for item in value:
                        print(f"   • {item}")
        print("=" * 80 + "\n")
