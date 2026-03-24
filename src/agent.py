

import os
import time
import asyncio
import json
import base64
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .prompt_builder import build_system_prompt
from .parser import parse_response
from .config_loader import Config

# Optional MCP dependencies — imported lazily so the existing pipeline keeps
# working even when langchain-mcp-adapters is not installed.
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# BROWSER USE INTEGRATION — START
try:
    from browser_use import Browser
    from browser_use.browser.config import BrowserConfig
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    # Fallback for newer browser-use versions where BrowserConfig moved.
    try:
        from browser_use import Browser, BrowserProfile as BrowserConfig
        BROWSER_USE_AVAILABLE = True
    except ImportError:
        pass
# BROWSER USE INTEGRATION — END

# GEMINI VISION — START
# To use Google Gemini vision: pip install langchain-google-genai
# Then set GOOGLE_API_KEY=AIza... in .env
# Get free API key at: https://aistudio.google.com/app/apikey
# GEMINI VISION — END


class PersonaAgent:

    def __init__(self, user: dict, scenario: dict = None, config: Config = None,
                 use_mcp: bool = False):
        """
        Parameters
        ----------
        user       : persona dict loaded from personas/*.json
        scenario   : scenario dict loaded from scenarios/*.yaml
        config     : global Config; defaults to Config() if omitted
        use_mcp    : when True, ``run_with_mcp()`` is available to drive the
                     browser autonomously via the Playwright MCP server instead
                     of the manual ReAct loop in main.py.
        """
        self.user = user
        self.scenario = scenario
        self.config = config or Config()
        self.use_mcp = use_mcp

        # Build system prompt with persona and scenario
        self.system_prompt = build_system_prompt(user, scenario)
        self.history: List = []

        # History limit: 2 derniers échanges (keep within token budget)
        self.max_history_length = 2

        # Initialize the LLM based on config
        self.llm = self._init_llm()
        self.vision_llm = self._init_vision_llm()

        # BROWSER USE INTEGRATION — START
        self._last_screenshot: Optional[str] = None
        # GEMINI VISION — START
        # Determine which API key to check based on vision provider
        _vision_provider = self.config.vision_provider
        if _vision_provider == "google":
            _vision_key_available = bool(os.getenv("GOOGLE_API_KEY"))
            _vision_key_name = "GOOGLE_API_KEY"
            _vision_model_display = f"gemini ({self.config.vision_model})"
        elif _vision_provider == "openai":
            _vision_key_available = bool(os.getenv("OPENAI_API_KEY"))
            _vision_key_name = "OPENAI_API_KEY"
            _vision_model_display = f"gpt-4o-mini"
        elif _vision_provider == "github":
            _vision_key_available = bool(os.getenv("GITHUB_TOKEN"))
            _vision_key_name = "GITHUB_TOKEN"
            _vision_model_display = self.config.vision_model
        elif _vision_provider == "groq":
            _vision_key_available = bool(os.getenv("GROQ_API_KEY"))
            _vision_key_name = "GROQ_API_KEY"
            _vision_model_display = self.config.vision_model
        elif _vision_provider == "ollama":
            _vision_key_available = True
            _vision_key_name = "OLLAMA_LOCAL"
            _vision_model_display = self.config.vision_model
        else:
            _vision_key_available = False
            _vision_key_name = "API_KEY"
            _vision_model_display = self.config.vision_model

        self._attach_observation_images = bool(
            self.config.vision_enabled
            and self.config.sandbox
            and _vision_key_available
        )
        
        if self.config.vision_enabled and not _vision_key_available:
            print(f"ℹ Vision disabled: {_vision_key_name} not set in .env")
        elif self.config.vision_enabled and _vision_key_available:
            print(f"✅ Vision enabled: screenshots → {_vision_model_display}")
        # GEMINI VISION — END
        # BROWSER USE INTEGRATION — END
    
    def _init_llm(self) -> ChatOpenAI:
        
        provider = self.config.llm_provider
        
        if provider == "github":
            # GitHub Models - new endpoint
            api_key = os.getenv("GITHUB_TOKEN")
            base_url = "https://models.github.ai/inference"
        elif provider == "openai":
            # Direct OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = None
        elif provider == "groq":
            # Groq — OpenAI-compatible API
            api_key = os.getenv("GROQ_API_KEY")
            base_url = "https://api.groq.com/openai/v1"
        elif provider == "ollama":
            # Local Ollama
            api_key = "ollama"  # Ollama doesn't need a real key
            base_url = "http://localhost:11434/v1"
        # GEMINI MAIN LLM — START
        elif provider == "google":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                google_key = os.getenv("GOOGLE_API_KEY")
                if not google_key:
                    print("⚠ GOOGLE_API_KEY not set — falling back to GitHub")
                    api_key = os.getenv("GITHUB_TOKEN")
                    base_url = "https://models.github.ai/inference"
                    return ChatOpenAI(
                        model="openai/gpt-4o-mini",
                        base_url=base_url,
                        api_key=api_key,
                        temperature=self.config.llm_temperature,
                        max_tokens=self.config.llm_max_tokens,
                    )
                return ChatGoogleGenerativeAI(
                    model=self.config.llm_model,
                    google_api_key=google_key,
                    temperature=self.config.llm_temperature,
                    max_output_tokens=self.config.llm_max_tokens,
                )
            except ImportError:
                print("⚠ langchain-google-genai not installed")
                print("  Run: pip install langchain-google-genai")
                raise
            except Exception as e:
                print(f"⚠ Gemini main LLM init failed: {e}")
                raise
        # GEMINI MAIN LLM — END
        else:
            # Default to GitHub Models
            api_key = os.getenv("GITHUB_TOKEN")
            base_url = "https://models.github.ai/inference"
        
        return ChatOpenAI(
            model=self.config.llm_model,
            temperature=self.config.llm_temperature,
            base_url=base_url,
            api_key=api_key,
            max_tokens=self.config.llm_max_tokens
        )

    def _init_vision_llm(self) -> ChatOpenAI:
        """Create a dedicated vision LLM and gracefully fall back to main LLM."""
        if (self.config.vision_provider == self.config.llm_provider and
                self.config.vision_model == self.config.llm_model):
            return self.llm

        provider = self.config.vision_provider
        api_key = None
        base_url = None

        # GEMINI VISION — START
        if provider == "google":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                google_key = os.getenv("GOOGLE_API_KEY")
                if not google_key:
                    print("⚠ GOOGLE_API_KEY not set in .env — vision falls back to main LLM")
                    return self.llm
                gemini = ChatGoogleGenerativeAI(
                    model=self.config.vision_model,
                    google_api_key=google_key,
                    temperature=self.config.llm_temperature,
                    max_output_tokens=self.config.vision_max_tokens,
                )
                print(f"✅ Gemini vision LLM initialized: {self.config.vision_model}")
                return gemini
            except ImportError:
                print("⚠ langchain-google-genai not installed.")
                print("  Run: pip install langchain-google-genai")
                return self.llm
            except Exception as e:
                print(f"⚠ Gemini init failed: {e} — falling back to main LLM")
                return self.llm
        # GEMINI VISION — END

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return self.llm
        elif provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            base_url = "https://api.groq.com/openai/v1"
        elif provider == "github":
            api_key = os.getenv("GITHUB_TOKEN")
            base_url = "https://models.github.ai/inference"
        elif provider == "ollama":
            api_key = "ollama"
            base_url = "http://localhost:11434/v1"

        try:
            return ChatOpenAI(
                model=self.config.vision_model,
                temperature=self.config.llm_temperature,
                base_url=base_url,
                api_key=api_key,
                max_tokens=self.config.vision_max_tokens,
            )
        except Exception:
            return self.llm
    
    def _build_user_message(self, page_content: str, page_url: str, step: int) -> str:
       
        message = f"""
═══════════════════════════════════════════════════════════════
STEP {step} - Current State
═══════════════════════════════════════════════════════════════

Current URL: {page_url}

Page Content (truncated):
───────────────────────────────────────────────────────────────
{page_content}
───────────────────────────────────────────────────────────────

Based on what you see above, what is your next action?
Remember to respond in the exact format: Thought / Action / Target
"""
        return message
    
    def _trim_history(self):
        
        max_messages = self.max_history_length * 2  # 2 messages per exchange
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    @staticmethod
    def _sanitize_react_output(text: str) -> str:
        """Drop non-ReAct garbage lines once structured output begins."""
        if not isinstance(text, str):
            return str(text)

        lines = text.splitlines()
        cleaned_lines: List[str] = []
        structured_started = False

        for line in lines:
            stripped = line.strip()
            upper = stripped.upper()
            is_structured = (
                upper.startswith("THOUGHT:")
                or (upper.startswith("ACTION:") and not upper.startswith("ACTION_INPUT:"))
                or upper.startswith("ACTION_INPUT:")
                or upper == "DONE"
            )

            if is_structured:
                cleaned_lines.append(stripped)
                structured_started = True
                continue

            # Ignore trailing garbage (e.g., random tokens) after structured block starts.
            if structured_started and stripped:
                continue

            if not structured_started and stripped:
                cleaned_lines.append(stripped)

        sanitized = "\n".join(cleaned_lines).strip()
        return sanitized if sanitized else text.strip()
    
    def decide(self, page_content: str, page_url: str, step: int) -> Dict[str, str]:
        
        # Build the user message
        user_message = self._build_user_message(page_content, page_url, step)
        
        # Build the full message list
        messages = [
            SystemMessage(content=self.system_prompt),
            *self.history,
            HumanMessage(content=user_message)
        ]
        
        # Retry logic with exponential backoff for rate limits
        max_retries = 5
        base_delay = 10  # seconds
        
        for attempt in range(max_retries):
            try:
                # Call the LLM
                response = self.llm.invoke(messages)
                response_text = response.content
                
                # Get token count if available (handles both OpenAI and Groq formats)
                token_count = 0
                if hasattr(response, 'response_metadata'):
                    meta = response.response_metadata
                    usage = meta.get('token_usage') or meta.get('usage') or {}
                    token_count = usage.get('total_tokens', 0)
                
                # Parse the response
                parsed = parse_response(response_text)
                
                # Add raw response and token count to parsed result
                parsed['raw_response'] = response_text
                parsed['token_count'] = token_count
                parsed['input_preview'] = user_message[:500]
                
                # Add to history
                self.history.append(HumanMessage(content=user_message))
                self.history.append(AIMessage(content=response_text))
                
                # Trim history: garder seulement les 2 derniers échanges
                self.history = self.history[-4:]  # 2 échanges x 2 messages
                
                return parsed
                
            except Exception as e:
                error_msg = str(e).lower()
                is_rate_limit = "too many requests" in error_msg or "rate limit" in error_msg or "429" in error_msg
                
                if is_rate_limit and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # 10s, 20s, 40s, 80s, 160s
                    print(f"⚠ Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {delay}s before retry...")
                    time.sleep(delay)
                    continue
                
                # Final attempt failed or non-rate-limit error
                print(f"⚠ LLM Error: {e}")
                return {
                    "thought": f"Error calling LLM: {str(e)}",
                    "action": "scroll",
                    "target": "down",
                    "raw_response": f"ERROR: {str(e)}",
                    "token_count": 0,
                    "input_preview": user_message[:500] if 'user_message' in dir() else ""
                }
    
    def get_history_length(self) -> int:
        """
        Get the current number of messages in history.
        
        Returns:
            Number of messages in the conversation history
        """
        return len(self.history)
    
    def reset_history(self):
        """
        Clear the conversation history.
        """
        self.history = []

    # ═══════════════════════════════════════════════════════════════
    # MCP — Playwright Model Context Protocol integration
    # ═══════════════════════════════════════════════════════════════

    def _build_mcp_task(self, start_url: str) -> str:
        """Compose the task description sent to the MCP-backed agent."""
        sc = self.scenario or {}
        scenario_block = ""
        if sc:
            scenario_block = (
                f"\nScenario : {sc.get('name', '')}\n"
                f"Goal     : {sc.get('objectif', sc.get('description', ''))}\n"
                f"Success  : {sc.get('critere_succes', '')}\n"
            )

        return (
            f"You are acting as: {self.user.get('id', 'persona')}\n"
            f"Objective: {self.user.get('objectif', '')}\n"
            f"{scenario_block}\n"
            f"Starting URL: {start_url}\n\n"
            "Use the available browser tools to complete the task. Navigate to the URL, "
            "interact with the page elements, and fulfil the scenario goal. "
            "When done, summarise what you did and the final outcome."
        )

    @staticmethod
    def _compress_snapshot(raw: str, max_chars: int = 8000, max_products: int = None) -> str:
        """Extract structured product data from a Playwright MCP snapshot.

        Parses the accessibility-tree YAML to find product names, prices,
        and 'Add to cart' refs.  Returns a compact product table that the
        LLM can act on directly.  Deduplicates overlay entries.
        """
        import re

        # Handle repr'd strings from str(tool_result):
        # un-escape \\n → \n and \\' → ' so regex can parse YAML lines
        if "\\n" in raw and ("'text':" in raw or "### " in raw):
            raw = raw.replace('\\n', '\n').replace("\\'", "'")

        parts = []

        # ── Page header ────────────────────────────────────────
        url_m = re.search(r'Page URL:\s*(.+)', raw)
        title_m = re.search(r'Page Title:\s*(.+)', raw)
        if url_m:
            parts.append(f"URL: {url_m.group(1).strip()}")
        if title_m:
            parts.append(f"Title: {title_m.group(1).strip()}")

        # ── Normalize accessibility tree format variations ─────
        # After scrolling, Playwright emits a different heading format:
        #   heading [level=2] [ref=eXX]: Rs. 500   (colon-text style)
        # instead of the initial render format:
        #   heading "Rs. 500" [level=2] [ref=eXX]  (quoted-label style)
        # Normalise colon-text style → quoted-label style so one regex handles both.
        raw = re.sub(
            r'\bheading\s+(\[[^\]]*\]\s*\[ref=e\d+\][^\n:]*?):\s*((?:Rs\.?|USD|EUR|GBP|\$|€|£)\s*[\d.,]+)',
            lambda m: f'heading "{m.group(2)}" {m.group(1).strip()}',
            raw,
        )

        # ── Extract products from accessibility snapshot ───────
        # Prices: heading "Rs. 500" / "$16.50" / "EUR 19" [level=2] [ref=eXX]
        prices = list(re.finditer(
            r'heading\s+"((?:Rs\.?|USD|EUR|GBP|\$|€|£)\s*[\d.,]+)".*?\[ref=(e\d+)\]', raw))
        # Names:   paragraph [ref=eXX]: Blue Top  (actual Playwright format)
        names = list(re.finditer(
            r'paragraph\s*\[ref=(e\d+)\]:\s*(.+)', raw))
        # View format 1:  link "View Product" [ref=eXX]  (initial render)
        views = list(re.finditer(
            r'link\s+"[^"]*[Vv]iew [Pp]roduct[^"]*"\s*\[ref=(e\d+)\]', raw))
        # View format 2:  link [ref=eXX] ... /product_details/N  (lazy-loaded)
        # After scrolling, links lose their quoted name and appear as child text nodes.
        _found_view_refs = {m.group(1) for m in views}
        for _lm in re.finditer(r'link\s+\[ref=(e\d+)\]', raw):
            if _lm.group(1) not in _found_view_refs:
                _snippet = raw[_lm.start(): _lm.start() + 300]
                if re.search(r'/product_details/\d+', _snippet) and \
                   re.search(r'[Vv]iew\s*[Pp]roduct', _snippet):
                    views.append(_lm)
                    _found_view_refs.add(_lm.group(1))

        # DEMOBLAZE SUPPORT — START
        # Demoblaze product cards usually expose product links as:
        #   link "Samsung galaxy s6" [ref=e81]
        #   - /url: prod.html?idp_=1
        # and a nearby price heading such as "$360".
        demoblaze_products = []
        for _lm in re.finditer(r'link\s+"([^"]+)"\s*\[ref=(e\d+)\]', raw):
            _name = _lm.group(1).strip()
            _ref = _lm.group(2)

            # Skip generic non-product links.
            if not _name or re.search(r'home|contact|about|cart|log in|sign up|product store|next|previous', _name, re.IGNORECASE):
                continue

            _snippet = raw[_lm.start(): _lm.start() + 500]
            if not re.search(r'/url:\s*prod\.html\?idp_=\d+', _snippet, re.IGNORECASE):
                continue

            _price_m = re.search(
                r'heading\s+"((?:Rs\.?|USD|EUR|GBP|\$|€|£)\s*[\d.,]+)"',
                _snippet,
            )
            if _price_m:
                demoblaze_products.append((_name, _price_m.group(1).strip(), _ref))
        # DEMOBLAZE SUPPORT — END

        products = []

        # Strategy: group by View Product links (the reliable way to click).
        # Each View Product link follows the product's price+name in the tree.
        # Look BACKWARD from each View Product link to find the nearest price/name.
        used_prices = set()

        for view_m in views:
            view_ref = view_m.group(1)
            view_pos = view_m.start()

            # Find nearest price heading BEFORE this View Product link (within 2000 chars)
            best_price = None
            best_price_dist = 999999
            best_price_idx = -1
            for i, price_m in enumerate(prices):
                if i in used_prices:
                    continue
                dist = view_pos - price_m.start()
                if 0 < dist < 2000 and dist < best_price_dist:
                    best_price = price_m.group(1)
                    best_price_dist = dist
                    best_price_idx = i
            if best_price_idx >= 0:
                used_prices.add(best_price_idx)

            # Find nearest name near this price (within 500 chars)
            price_pos = prices[best_price_idx].start() if best_price_idx >= 0 else view_pos
            best_name = None
            best_name_dist = 999999
            for name_m in names:
                # New format: group(1)=ref, group(2)=name text
                nm = name_m.group(2).strip()
                dist = abs(name_m.start() - price_pos)
                if dist < best_name_dist and dist < 500:
                    best_name = nm
                    best_name_dist = dist

            if best_name and best_price:
                products.append((best_name, best_price, view_ref))

        # DEMOBLAZE SUPPORT — START
        # Merge Demoblaze-style extracted items with standard extraction.
        products.extend(demoblaze_products)
        # DEMOBLAZE SUPPORT — END

        # Deduplicate (overlay creates duplicates with same name)
        seen = set()
        unique = []
        for name, price, ref in products:
            key = name.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(f"- {name} | {price} | View ref={ref}")

        if unique:
            if max_products is not None:
                unique = unique[:max_products]
            parts.append("PRODUCTS:\n" + "\n".join(unique))

        # ── Other interactive elements (search, buttons) ───────
        textboxes = re.findall(
            r'textbox\s+"([^"]*)".*?\[ref=(e\d+)\]', raw)
        buttons_found = re.findall(
            r'button\s+"([^"]*)".*?\[ref=(e\d+)\]', raw)
        links_found = re.findall(
            r'link\s+"([^"]+)"\s*\[ref=(e\d+)\]', raw)
        extras = []
        for label, ref in textboxes[:3]:
            extras.append(f"- textbox \"{label}\" ref={ref}")
        for label, ref in buttons_found[:3]:
            extras.append(f"- button \"{label}\" ref={ref}")
        # Include key navigation links (useful on ParaBank sidebar and similar sites).
        important_link_re = re.compile(
            r'transfer|accounts overview|account activity|open new account|bill pay|find transactions|logout|log in',
            re.IGNORECASE,
        )
        for label, ref in links_found:
            if important_link_re.search(label):
                extras.append(f"- link \"{label}\" ref={ref}")
        if len(extras) > 12:
            extras = extras[:12]
        if extras:
            parts.append("OTHER:\n" + "\n".join(extras))

        result = "\n\n".join(parts)

        # ── Fallback: if no products extracted, use line filter ─
        if not unique:
            keep_re = re.compile(
                r'((?:Rs\.?|USD|EUR|GBP|\$|€|£)\s*[\d.,]+)|add to cart|view product|textbox|button|cart|buy|price'
                r'|heading.*"[^"]*".*ref=e\d{2,}'
                r'|paragraph\s*\[ref=e\d+\]:\s*\S',
                re.IGNORECASE)
            skip_re = re.compile(
                r'banner|navigation|contentinfo|footer|copyright|subscribe'
                r'|Category|Brands',
                re.IGNORECASE)
            lines = []
            for line in raw.splitlines():
                s = line.strip()
                if not s:
                    continue
                if skip_re.search(s):
                    continue
                if keep_re.search(s):
                    lines.append(s)
            result = "\n".join(lines) if lines else raw

        return result[:max_chars] + ("\n... (truncated)" if len(result) > max_chars else "")

    # BROWSER USE INTEGRATION — START
    async def _launch_sandbox(self):
        """Launch Browser Use isolated session and expose CDP endpoint."""
        if not self.config.sandbox or not BROWSER_USE_AVAILABLE:
            return None, None

        try:
            browser_cfg = BrowserConfig(headless=self.config.headless)
            try:
                browser = Browser(config=browser_cfg)
            except TypeError:
                browser = Browser(browser_profile=browser_cfg)

            start_result = await browser.start()
            cdp_url = getattr(browser, "cdp_url", None)
            if not cdp_url and isinstance(start_result, dict):
                cdp_url = start_result.get("cdp_url")

            if not cdp_url:
                print("⚠ Browser Use sandbox started but no CDP endpoint was found. Falling back.")
                try:
                    await browser.stop()
                except Exception:
                    pass
                return None, None

            return browser, cdp_url
        except Exception as e:
            print(f"⚠ Browser Use sandbox launch failed: {e}. Falling back.")
            return None, None

    async def _capture_sandbox_screenshot(self, browser) -> Optional[str]:
        """Capture screenshot from Browser Use session as base64 string."""
        if browser is None:
            return None

        if hasattr(browser, "take_screenshot"):
            shot = await browser.take_screenshot(full_page=False)
            if isinstance(shot, bytes):
                return base64.b64encode(shot).decode("utf-8")
            if isinstance(shot, str):
                if shot.startswith("data:image"):
                    return shot.split(",", 1)[1]
                return shot

        if hasattr(browser, "get_browser_state_summary"):
            state = await browser.get_browser_state_summary(include_screenshot=True)
            screenshot = getattr(state, "screenshot", None)
            if screenshot:
                return screenshot

        return None
    # BROWSER USE INTEGRATION — END

    async def run_with_mcp(self, start_url: str) -> Dict[str, Any]:
        """
        ReAct agent loop: LLM decides each action, MCP executes it.

        Uses ``stdio_client`` + ``ClientSession`` to keep a single stable browser
        session across all steps.
        """
        import re as _re
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from langchain_mcp_adapters.tools import load_mcp_tools

        # BROWSER USE INTEGRATION — START
        bu_browser, cdp_url = await self._launch_sandbox()

        async def _close_sandbox_if_needed() -> None:
            if bu_browser is not None:
                try:
                    if hasattr(bu_browser, "close"):
                        await bu_browser.close()
                    elif hasattr(bu_browser, "stop"):
                        await bu_browser.stop()
                except Exception:
                    pass
        # BROWSER USE INTEGRATION — END

        headless_args = ["--headless"] if self.config.headless else []

        print("\n" + "=" * 80)
        print("🚀 MCP ReAct SESSION STARTING")
        print("=" * 80)
        print(f"📍 Target URL: {start_url}")
        print(f"👤 Persona: {self.user.get('id', self.user.get('nom', 'Unknown'))}")
        print(f"🎯 Scenario: {self.scenario.get('objectif', 'Unknown')}")
        # GEMINI VISION — START
        if self._attach_observation_images:
            print(f"👁️  Vision mode ACTIVE — screenshots → "
                  f"{self.config.vision_model} ({self.config.vision_provider})")
        # GEMINI VISION — END
        else:
            if self.config.vision_enabled:
                print("ℹ Vision disabled — provider API key not set or sandbox inactive")
            else:
                print("ℹ Vision mode OFF (vision_enabled: false in config)")
        print()

        # ── Connect via stdio (keeps session alive) ────────────────
        print("🔌 Connecting to Playwright MCP Server...")
        # BROWSER USE INTEGRATION — START
        mcp_args = ["@playwright/mcp", "--cdp-endpoint", cdp_url] if cdp_url is not None else ["@playwright/mcp"] + headless_args
        # BROWSER USE INTEGRATION — END
        server_params = StdioServerParameters(
            command="npx",
            args=mcp_args,
        )

        async with stdio_client(server_params) as (read, write):
          async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            tools_dict = {t.name: t for t in tools}

            print(f"✓ Connected! {len(tools_dict)} tools available")
            for i, t in enumerate(tools, 1):
                print(f"  {i}. {t.name}: {t.description[:80]}...")
            print()

            tool_names = list(tools_dict.keys())

            # Only list tools the agent actually needs (saves ~75% tokens)
            useful_tools = [
                "browser_navigate", "browser_click", "browser_press_key",
                "browser_snapshot", "browser_type", "browser_evaluate",
                "browser_select_option", "browser_wait_for", "browser_handle_dialog",
            ]
            tools_text = "\n".join(
                f"- {t.name}: {t.description[:80]}"
                for t in tools if t.name in useful_tools
            )

            objectif = self.scenario.get("objectif", "Complete the task")

            # BOOKING.COM — START
            is_booking = "booking.com" in (start_url or "").lower()
            # BOOKING.COM — END

            # DEMOBLAZE SUPPORT — START
            is_demoblaze = "demoblaze" in (start_url or "").lower()
            # DEMOBLAZE SUPPORT — END

            # PARABANK — START
            is_parabank = "parabank" in (start_url or "").lower()
            scenario_context = self.scenario.get("context", {}) if isinstance(self.scenario, dict) else {}
            parabank_username = str(
                scenario_context.get("username")
                or os.getenv("PARABANK_USERNAME")
                or "john"
            )
            parabank_password = str(
                scenario_context.get("password")
                or os.getenv("PARABANK_PASSWORD")
                or "demo"
            )
            parsed_start_url = urlparse(start_url or "")
            parabank_base_url = (
                f"{parsed_start_url.scheme}://{parsed_start_url.netloc}"
                if parsed_start_url.scheme and parsed_start_url.netloc
                else "https://parabank.parasoft.com"
            )
            parabank_transfer_url = f"{parabank_base_url}/parabank/transfer.htm"
            # PARABANK — END

            # ── Persona-specific strategy ──────────────────────
            vitesse        = self.user.get("vitesse_navigation", "rapide")
            sensibilite    = self.user.get("sensibilite_prix", "faible")
            tolerance      = self.user.get("tolerance_erreurs", "haute")
            patience_sec   = self.user.get("patience_attente_sec", 5)
            device         = self.user.get("device", "desktop")
            persona_id     = self.user.get("id", "unknown")

            if vitesse == "rapide":
                # DEMOBLAZE SUPPORT — START
                if is_demoblaze:
                    strategy = (
                        "PERSONA PROFILE (acheteur_impatient):\n"
                        f"  device={device}, vitesse_navigation={vitesse}, "
                        f"sensibilite_prix={sensibilite}, "
                        f"tolerance_erreurs={tolerance}, "
                        f"patience_attente_sec={patience_sec}\n\n"
                        "STRATEGY:\n"
                        "- You are in a hurry and browsing on mobile.\n"
                        "- Navigate to the homepage and click the first visible category (typically Phones).\n"
                        "- Pick the first visible product from that category.\n"
                        "- Open product detail, click Add to cart, then DONE immediately.\n"
                        "- Do NOT browse other categories.\n"
                        f"- If a page takes more than {patience_sec}s, move on immediately.\n"
                    )
                # BOOKING.COM — START
                elif is_booking:
                    strategy = (
                        "PERSONA PROFILE (acheteur_impatient on booking.com):\n"
                        f"  device={device}, vitesse={vitesse}, patience={patience_sec}s\n\n"
                        "STRATEGY — follow these steps IN ORDER:\n"
                        "Step 1: browser_navigate to https://www.booking.com\n"
                        "Step 2: browser_snapshot to see the search form\n"
                        "Step 3: Find the destination textbox ref in the snapshot\n"
                        "        It is labeled 'Destination' or 'Ou allez-vous ?'\n"
                        "        Use browser_type to type 'Paris'\n"
                        "Step 4: browser_snapshot to see the autocomplete dropdown\n"
                        "Step 5: Click the first 'Paris' suggestion in the dropdown\n"
                        "Step 6: Click the Search button (ref from snapshot)\n"
                        "Step 7: browser_snapshot to see hotel results with prices\n"
                        "Step 8: Click on the FIRST visible hotel — no comparison\n"
                        "Step 9: DONE — report hotel name and price\n"
                        "RULES:\n"
                        "- NEVER scroll before using the search form\n"
                        "- ALWAYS use browser_snapshot before browser_click\n"
                        "- Use fresh refs from the latest snapshot only\n"
                        "- If overlay blocks click: browser_press_key Escape first\n"
                        "- If rate limited: wait and retry\n"
                        "- Maximum 10 steps — act fast\n"
                    )
                # BOOKING.COM — END
                # PARABANK — START
                elif is_parabank:
                    strategy = (
                        "PERSONA PROFILE (acheteur_impatient on parabank):\n"
                        f"  device={device}, vitesse={vitesse}, patience={patience_sec}s\n\n"
                        "STRATEGY — follow IN ORDER, max 6 steps:\n"
                        f"Step 1: browser_navigate to {start_url}\n"
                        "Step 2: browser_snapshot to see the login form\n"
                        f"Step 3: browser_type username field (ref from snapshot) with '{parabank_username}'\n"
                        f"Step 4: browser_type password field (ref from snapshot) with '{parabank_password}'\n"
                        "Step 5: browser_click the Login button\n"
                        "Step 6: browser_snapshot to confirm login → DONE immediately\n"
                        "RULES:\n"
                        "- Do NOT browse accounts or check balances — just login fast\n"
                        "- Do NOT transfer money — just confirm you are logged in\n"
                        "- DONE as soon as accounts page is visible\n"
                        "- Maximum 6 steps\n"
                    )
                # PARABANK — END
                else:
                    # DEMOBLAZE SUPPORT — END
                    # ── Impatient buyer ─────────────────────────────
                    # sensibilite_prix: faible  → doesn't care about finding the global minimum
                    # tolerance_erreurs: haute  → skips errors and continues
                    # patience_attente_sec: 5   → won't wait long for pages
                    # device: mobile            → browsing on mobile
                    strategy = (
                        "PERSONA PROFILE (acheteur_impatient):\n"
                        f"  device={device}, vitesse_navigation={vitesse}, "
                        f"sensibilite_prix={sensibilite}, "
                        f"tolerance_erreurs={tolerance}, "
                        f"patience_attente_sec={patience_sec}\n\n"
                        "STRATEGY:\n"
                        "- You are in a hurry and browsing on mobile. You have NO patience.\n"
                        "- Use only what is visible in the current OBSERVATION.\n"
                        "- STRICTLY FORBIDDEN: browser_press_key and any scrolling action.\n"
                        "- Pick a suitable low-price visible product quickly, then open product details or click add-to-cart if clearly available.\n"
                        "- If an error occurs, ignore it and try the next visible product (high error tolerance).\n"
                        f"- If a page takes more than {patience_sec}s, move on immediately.\n"
                        "- When done, say DONE immediately — do NOT take any extra steps.\n"
                    )
            else:
                # DEMOBLAZE SUPPORT — START
                if is_demoblaze:
                    strategy = (
                        "PERSONA PROFILE (acheteur_prudent):\n"
                        f"  device={device}, vitesse_navigation={vitesse}, "
                        f"sensibilite_prix={sensibilite}, "
                        f"tolerance_erreurs={tolerance}, "
                        f"patience_attente_sec={patience_sec}\n\n"
                        "STRATEGY:\n"
                        "- You are careful and thorough, browsing on desktop with no rush.\n"
                        "- Visit ALL categories: Phones, Laptops, Monitors.\n"
                        "- In each category, capture all visible products and prices (use pagination if Next is available).\n"
                        "- Keep a running list across categories, then compare ALL prices globally.\n"
                        "- Select the absolute cheapest product across all categories.\n"
                        "- Open product details, click Add to cart, then DONE.\n"
                        f"- You are patient: you can wait up to {patience_sec}s for page updates.\n"
                    )
                # BOOKING.COM — START
                elif is_booking:
                    strategy = (
                        "PERSONA PROFILE (acheteur_prudent on booking.com):\n"
                        f"  device={device}, vitesse={vitesse}, patience={patience_sec}s\n\n"
                        "STRATEGY — follow these steps IN ORDER:\n"
                        "Step 1: browser_navigate to https://www.booking.com\n"
                        "Step 2: browser_snapshot to see the search form\n"
                        "Step 3: Find the destination textbox ref in the snapshot\n"
                        "        It is labeled 'Destination' or 'Ou allez-vous ?'\n"
                        "        Use browser_type to type 'Paris'\n"
                        "Step 4: browser_snapshot to see the autocomplete dropdown\n"
                        "Step 5: Click 'Paris, Ile-de-France, France' suggestion\n"
                        "Step 6: Look for check-in date button and click it\n"
                        "Step 7: Select next Saturday as check-in date\n"
                        "Step 8: Select next Sunday as check-out date\n"
                        "Step 9: Click the Search button\n"
                        "Step 10: browser_snapshot to see hotel results with prices\n"
                        "Step 11: Scroll through results, note ALL hotel prices\n"
                        "Step 12: Identify the cheapest hotel from all visible results\n"
                        "Step 13: Click on the cheapest hotel\n"
                        "Step 14: DONE — report hotel name and lowest price found\n"
                        "RULES:\n"
                        "- NEVER scroll before using the search form\n"
                        "- ALWAYS use browser_snapshot before browser_click\n"
                        "- Use fresh refs from the latest snapshot only\n"
                        "- If overlay blocks click: browser_press_key Escape first\n"
                        "- If date picker is complex, use the screenshot to identify date cells\n"
                        "- NEVER attempt actual booking or payment\n"
                    )
                # BOOKING.COM — END
                # PARABANK — START
                elif is_parabank:
                    strategy = (
                        "PERSONA PROFILE (acheteur_prudent on parabank):\n"
                        f"  device={device}, vitesse={vitesse}, patience={patience_sec}s\n\n"
                        "STRATEGY — follow IN ORDER:\n"
                        f"Step 1: browser_navigate to {start_url}\n"
                        "Step 2: browser_snapshot to see the login form\n"
                        f"Step 3: browser_type username field with '{parabank_username}'\n"
                        f"Step 4: browser_type password field with '{parabank_password}'\n"
                        "Step 5: browser_click the Login button\n"
                        "Step 6: browser_snapshot to see accounts overview\n"
                        "Step 7: Note ALL account names and balances visible\n"
                        "Step 8: browser_click on the first account to see details\n"
                        "Step 9: browser_snapshot to see transaction history\n"
                        "Step 10: browser_navigate_back to accounts overview\n"
                        "Step 11: Find the Transfer Funds link and click it\n"
                        "Step 12: browser_snapshot to see transfer form\n"
                        "Step 13: Select source account and destination account\n"
                        "Step 14: Enter amount 10 in the amount field\n"
                        "Step 15: browser_click Transfer button\n"
                        "Step 16: DONE — report transfer confirmation\n"
                        "RULES:\n"
                        "- ALWAYS check balances BEFORE transferring\n"
                        "- Transfer the SMALLEST possible amount (10)\n"
                        "- Verify confirmation page after transfer\n"
                        "- Be careful, verify every step before proceeding\n"
                    )
                # PARABANK — END
                else:
                    # DEMOBLAZE SUPPORT — END
                    # ── Prudent buyer ────────────────────────────────
                    # sensibilite_prix: haute   → MUST find the global cheapest
                    # tolerance_erreurs: faible → be careful, verify every step
                    # patience_attente_sec: 30  → willing to wait for pages
                    # device: desktop           → browsing on desktop
                    strategy = (
                        "PERSONA PROFILE (acheteur_prudent):\n"
                        f"  device={device}, vitesse_navigation={vitesse}, "
                        f"sensibilite_prix={sensibilite}, "
                        f"tolerance_erreurs={tolerance}, "
                        f"patience_attente_sec={patience_sec}\n\n"
                        "STRATEGY:\n"
                        "- You are careful and thorough, browsing on desktop with no rush.\n"
                        "- You have HIGH price sensitivity: you MUST find the absolute cheapest product.\n"
                        "- Explore the catalog/listing area first and gather all visible options before choosing.\n"
                        "- MANDATORY scroll pattern:\n"
                        "    1) browser_evaluate {\"function\": \"() => window.scrollBy(0, 3000)\"}\n"
                        "    2) browser_snapshot\n"
                        "    3) Repeat until no new product options appear (same list twice) → bottom reached.\n"
                        "- ALWAYS take a browser_snapshot immediately after each browser_evaluate scroll.\n"
                        "- Keep a running list of product names and prices seen across snapshots.\n"
                        "- Only AFTER reaching the bottom, compare ALL prices and pick the absolute cheapest.\n"
                        "- You have LOW error tolerance: if a step fails, retry it carefully before continuing.\n"
                        f"- You are patient: you can wait up to {patience_sec}s for a page to load.\n"
                        "- Then open the cheapest product details and add to cart.\n"
                        "- Do NOT click any product until confirmed at the bottom of the page.\n"
                    )

            # BOOKING.COM — START
            if is_booking:
                site_rules = (
                    "4. BOOKING.COM RULES (CRITICAL):\n"
                    "- The homepage has a search form — USE IT FIRST\n"
                    "- DO NOT scroll the homepage looking for hotels\n"
                    "- DO NOT click hotel cards on the homepage\n"
                    "  (they are recommendations, not search results)\n"
                    "- CORRECT FLOW:\n"
                    "  1) browser_snapshot -> find destination textbox ref\n"
                    "  2) browser_type destination textbox -> 'Paris'\n"
                    "  3) browser_snapshot -> find Paris suggestion ref\n"
                    "  4) browser_click Paris suggestion\n"
                    "  5) browser_click Search button\n"
                    "  6) browser_snapshot -> see actual search results\n"
                    "  7) Find cheapest hotel in results\n"
                    "  8) browser_click hotel link -> DONE\n"
                    "- NEVER navigate to /searchresults directly\n"
                    "- If an overlay appears: browser_press_key Escape\n"
                    "  then browser_snapshot to refresh refs\n"
                    "- Hotel links open in a NEW TAB — that is normal\n"
                    "  Use browser_tabs to switch to the new tab if needed\n"
                    "- ACTION_INPUT must be valid JSON: {\"key\": \"value\"}\n"
                    "- NEVER attempt actual booking or payment\n"
                    "- If CAPTCHA appears: DONE with reason 'CAPTCHA encountered'\n"
                )
            elif is_demoblaze:
            # BOOKING.COM — END
            # DEMOBLAZE SUPPORT — START
                # DEMOBLAZE FIX — START
                site_rules = (
                    "4. DEMOBLAZE RULES:\n"
                    "- DEMOBLAZE DIALOG RULE (CRITICAL): After clicking Add to cart, an alert 'Product added' appears.\n"
                    "- You MUST call browser_handle_dialog immediately:\n"
                    "  ACTION: browser_handle_dialog\n"
                    "  ACTION_INPUT: {\"accept\": true}\n"
                    "- Do this BEFORE any other action — before navigate, before click, before snapshot.\n"
                    "- The alert blocks ALL tools if not dismissed first.\n"
                    "- Only after browser_handle_dialog succeeds -> navigate to https://www.demoblaze.com/cart.html to verify the item is there.\n"
                    "5. DEMOBLAZE NAVIGATION:\n"
                    "- All categories are on https://www.demoblaze.com (index.html only).\n"
                    "- To browse Phones: click the 'Phones' link in the left sidebar.\n"
                    "- To browse Laptops: click the 'Laptops' link in the left sidebar.\n"
                    "- To browse Monitors: click the 'Monitors' link in the left sidebar.\n"
                    "- NEVER navigate to /phones.html or /laptops.html or /monitors.html — these pages do not exist (404 error).\n"
                    "- After clicking a category link, take browser_snapshot to see products.\n"
                    "6. If you see modal state containing any alert dialog, ALWAYS call browser_handle_dialog {\"accept\": true} as your NEXT action before anything else.\n"
                    "7. ACTION_INPUT must be valid JSON: {\"key\": \"value\"}, not a plain string.\n"
                    "8. Compare all observed prices and pick the absolute cheapest before purchase in prudent mode.\n"
                    "9. If a modal/popup blocks clicks, close it first (Escape or close button), then retry your intended action.\n\n"
                )
                # DEMOBLAZE DIALOG FIX
                # DEMOBLAZE FIX — END
            # PARABANK — START
            elif is_parabank:
                site_rules = (
                    "4. PARABANK RULES:\n"
                    "- Login form is on the homepage left sidebar\n"
                    "- Username field: look for textbox or input labeled 'Username'\n"
                    "- Password field: look for textbox or input labeled 'Password'\n"
                    f"- Credentials: username='{parabank_username}', password='{parabank_password}'\n"
                    "- After login → accounts overview page shows account numbers and balances\n"
                    "- Transfer Funds link is in the left sidebar menu after login\n"
                    f"- If Transfer Funds ref is not visible after a fresh snapshot, navigate directly to {parabank_transfer_url}\n"
                    "- Transfer form has: From Account (select), To Account (select), Amount (input)\n"
                    "- After transfer → confirmation page shows transaction ID\n"
                    "- ALWAYS use browser_snapshot before browser_type to get fresh refs\n"
                    "- ALWAYS use browser_snapshot before browser_click to get fresh refs\n"
                    "- If login fails: browser_snapshot to see error message, then retry\n"
                    "- ACTION_INPUT must be valid JSON: {\"key\": \"value\"}\n"
                    "5. Do NOT attempt to register a new account\n"
                    "6. Do NOT attempt to pay bills or request loans\n"
                )
            # PARABANK — END
            else:
                site_rules = (
                    "4. The ONLY valid use of browser_evaluate is scrolling: "
                    "browser_evaluate {\"function\": \"() => window.scrollBy(0, 3000)\"}. "
                    "NEVER use browser_evaluate to query the DOM, extract data, or inspect elements.\n"
                    "5. To scroll down and load more products: "
                    "browser_evaluate {\"function\": \"() => window.scrollBy(0, 3000)\"}, "
                    "then immediately browser_snapshot to see newly revealed content.\n"
                    "6. If a Google ad appears (URL contains #google_vignette), navigate directly: "
                    "browser_navigate {\"url\": \"" + start_url + "\"}.\n"
                    "7. ACTION_INPUT must be valid JSON: {\"key\": \"value\"}, not a plain string.\n"
                    "8. When bottom is reached (same product list twice), compare ALL observed prices and "
                    "pick the product with the LOWEST price. Do NOT use browser_wait_for to pause or think — it only accepts "
                    "{\"time\": N} and is meant for page-load waits only.\n\n"
                    "9. If a modal/popup blocks clicks, close it first (Escape or close button), then retry your intended action.\n\n"
                )
            # DEMOBLAZE SUPPORT — END

            # ── System prompt (sent once, compact) ─────────────
            system_msg = SystemMessage(content=(
                "You are a web automation agent.\n\n"
                f"TOOLS:\n{tools_text}\n\n"
                f"OBJECTIVE: {objectif}\n"
                f"PERSONA: {persona_id} | device={device} | vitesse={vitesse} | sensibilite_prix={sensibilite} | patience={patience_sec}s\n"
                f"START URL: {start_url}\n\n"
                f"{strategy}\n"
                "RULES:\n"
                "1. After browser_navigate or browser_snapshot, read the OBSERVATION carefully. "
                "If a PRODUCTS or CATALOG summary is present, use it as the source of truth for product names, prices, and refs.\n"
                "2. Prefer stable refs from OBSERVATION (ref=eXXX) when clicking. Never reuse old refs from previous pages.\n"
                "3. To add a product to cart, first open product details when needed, then ALWAYS take browser_snapshot on the detail page and use the CURRENT add-to-cart ref from that snapshot.\n"
                f"{site_rules}"
                "EXAMPLE WORKFLOW:\n"
                "Step 1 → THOUGHT: Navigate to the target catalog page.\n"
                "ACTION: browser_navigate\nACTION_INPUT: {\"url\": \"" + start_url + "\"}\n\n"
                "Step 2 → THOUGHT: I identified the cheapest visible product with a valid details ref.\n"
                "ACTION: browser_click\nACTION_INPUT: {\"ref\": \"eXXX\"}\n\n"
                "Step 3 → THOUGHT: I am on product details, I need fresh refs before clicking add-to-cart.\n"
                "ACTION: browser_snapshot\nACTION_INPUT: {}\n\n"
                "Step 4 → THOUGHT: I found the current add-to-cart ref in the latest snapshot.\n"
                "ACTION: browser_click\nACTION_INPUT: {\"ref\": \"eYYY\"}\n\n"
                "Step 5 → THOUGHT: Product added and cart verified.\nDONE\n\n"
                "FORMAT (required every step):\n"
                "THOUGHT: <reasoning>\n"
                "ACTION: <tool_name>\n"
                "ACTION_INPUT: {\"param\": \"value\"}\n\n"
                "IMPORTANT: Output ONLY ONE action per response. Wait for the OBSERVATION before your next action.\n\n"
                "When done: THOUGHT: <summary>\nDONE"
            ))

            # ── ReAct loop ─────────────────────────────────────
            max_steps = 20
            messages: List = [system_msg]
            steps_detail: List[Dict[str, Any]] = []
            _current_llm = self.llm
            _github_fallback_activated = False
            _use_observation_images = self._attach_observation_images

            goal_text = f"{objectif} {self.user.get('objectif', '')}".lower()
            purchase_keywords = (
                "cart", "checkout", "add to cart", "buy", "purchase",
                "panier", "acheter", "achat", "commander",
            )
            scenario_strict = (self.scenario or {}).get("strict_done_validation")
            strict_done = bool(scenario_strict) if scenario_strict is not None else any(
                kw in goal_text for kw in purchase_keywords
            )
            # PARABANK — START
            if is_parabank:
                # ParaBank scenarios are banking flows, not cart/checkout flows.
                strict_done = False
            # PARABANK — END
            verification_state = {
                "added_to_cart_seen": False,
                "cart_page_seen": False,
                "cart_item_seen": False,
            }

            messages.append(HumanMessage(
                content=(
                    f"Begin at {start_url} and complete the objective.\n"
                    "Use the observation summaries to identify products, prices, and actionable refs."
                )
            ))

            # Running cheapest tracker for prudent buyer (updated after each scroll)
            cheapest_product: dict = {}  # {"name": ..., "price_value": float, "price_label": str, "ref": ...}

            for step in range(max_steps):
                print(f"\n{'=' * 80}")
                print(f"STEP {step + 1}/{max_steps}")
                print("=" * 80)

                # ── Anti-loop: detect repeated identical actions ──
                if len(steps_detail) >= 3:
                    last3 = [s.get("action") for s in steps_detail[-3:]]
                    if len(set(last3)) == 1 and last3[0] in ("browser_snapshot", "browser_press_key", "browser_evaluate"):
                        if vitesse != "rapide" and last3[0] in ("browser_press_key", "browser_evaluate"):
                            # Prudent buyer scrolling: remind to take snapshot after each scroll
                            nudge = (
                                "REMINDER: After each browser_evaluate scroll, you MUST take a "
                                "browser_snapshot immediately to see the new products revealed. "
                                "Take browser_snapshot NOW, then check: did the PRODUCTS table grow? "
                                "If yes (new products appeared), scroll again → snapshot. "
                                "If no (same list as before), compare ALL prices and pick cheapest."
                            )
                        else:
                            nudge = (
                                f"WARNING: You repeated '{last3[0]}' 3 times with no progress. "
                                "Stop repeating. Read the OBSERVATION above — it contains product "
                                "names/prices and actionable refs. Pick the cheapest valid option "
                                "and click its details/add-to-cart ref with browser_click."
                            )
                        print(f"⚠️ Anti-loop nudge injected")
                        messages.append(HumanMessage(content=nudge))
                if len(steps_detail) >= 2:
                    last2_errs = [s for s in steps_detail[-2:] if s.get("error")]
                    if len(last2_errs) == 2:
                        nudge = (
                            "WARNING: 2 consecutive errors. Make sure to include all 3 lines: "
                            "THOUGHT, ACTION, and ACTION_INPUT. ACTION_INPUT must be valid JSON."
                        )
                        messages.append(HumanMessage(content=nudge))
                if len(steps_detail) >= 2:
                    last2_actions = [s.get("action") for s in steps_detail[-2:]]
                    if last2_actions.count("browser_wait_for") == 2:
                        nudge = (
                            "WARNING: You used browser_wait_for twice in a row. STOP. "
                            "The OBSERVATION already contains the data you need. "
                            "Find the cheapest valid product from the latest observation and "
                            "browser_click the relevant ref — no extra waiting."
                        )
                        print("⚠️ Anti-wait_for nudge injected")
                        messages.append(HumanMessage(content=nudge))

                # ── Call LLM (with retry on rate-limit) ────────
                import asyncio as _asyncio
                print("🤖 Calling LLM...")
                ai_text = None
                error_msg = ""
                max_llm_retries = 5
                for _attempt in range(max_llm_retries):
                    try:
                        response = _current_llm.invoke(messages)
                        ai_text = response.content if hasattr(response, "content") else str(response)
                        ai_text = self._sanitize_react_output(ai_text)
                        break  # success
                    except Exception as e:
                        error_msg = str(e)
                        error_msg_lower = error_msg.lower()
                        if "413" in error_msg or "tokens_limit_reached" in error_msg:
                            print(f"❌ Token limit exceeded: {error_msg}")
                            # BROWSER USE INTEGRATION — START
                            await _close_sandbox_if_needed()
                            # BROWSER USE INTEGRATION — END
                            return {
                                "status": "error",
                                "response": f"Token limit exceeded: {error_msg}",
                                "steps": step + 1,
                                "steps_detail": steps_detail,
                            }
                        is_rate_limit = (
                            "too many requests" in error_msg_lower
                            or "rate limit" in error_msg_lower
                            or "resource_exhausted" in error_msg_lower
                            or "429" in error_msg_lower
                        )
                        if is_rate_limit:
                            # Try a one-time provider fallback when Gemini is throttled.
                            if (
                                not _github_fallback_activated
                                and self.config.llm_provider == "google"
                            ):
                                github_key = os.getenv("GITHUB_TOKEN")
                                if github_key:
                                    print("⚠ Gemini rate-limited — switching to GitHub Models fallback")
                                    _current_llm = ChatOpenAI(
                                        model="openai/gpt-4o-mini",
                                        base_url="https://models.github.ai/inference",
                                        api_key=github_key,
                                        temperature=self.config.llm_temperature,
                                        max_tokens=self.config.llm_max_tokens,
                                    )
                                    # Keep fallback for both text and vision turns
                                    # so the loop never switches back to rate-limited Gemini.
                                    self.llm = _current_llm
                                    self.vision_llm = _current_llm
                                    _use_observation_images = False
                                    self._last_screenshot = None
                                    _github_fallback_activated = True
                                    continue

                            # Do not sleep on the final retry.
                            if _attempt < max_llm_retries - 1:
                                wait = 10 * (_attempt + 1)
                                print(
                                    f"⏳ Rate limited (attempt {_attempt + 1}/{max_llm_retries}). "
                                    f"Waiting {wait}s..."
                                )
                            else:
                                continue
                            try:
                                await _asyncio.sleep(wait)
                            except (asyncio.CancelledError, Exception):
                                print("❌ MCP session cancelled during rate-limit wait — aborting")
                                # BROWSER USE INTEGRATION — START
                                await _close_sandbox_if_needed()
                                # BROWSER USE INTEGRATION — END
                                return {
                                    "status": "error",
                                    "response": "MCP session timed out during rate limit wait",
                                    "steps": step + 1,
                                    "steps_detail": steps_detail,
                                }
                            continue
                        # Other error — don't retry
                        print(f"❌ LLM error: {error_msg}")
                        break

                if ai_text is None:
                    if (
                        "too many requests" in error_msg.lower()
                        or "rate limit" in error_msg.lower()
                        or "resource_exhausted" in error_msg.lower()
                        or "429" in error_msg
                    ):
                        print(f"❌ Rate limit exhausted after {max_llm_retries} retries — aborting run")
                        # BROWSER USE INTEGRATION — START
                        await _close_sandbox_if_needed()
                        # BROWSER USE INTEGRATION — END
                        return {
                            "status": "error",
                            "response": f"Rate limit exhausted: {error_msg}",
                            "steps": step + 1,
                            "steps_detail": steps_detail,
                        }
                    steps_detail.append({"step": step + 1, "error": error_msg})
                    messages.append(AIMessage(content="THOUGHT: Error occurred\nACTION: none"))
                    messages.append(HumanMessage(
                        content=f"ERROR: {error_msg}. Try a different approach."
                    ))
                    continue

                print(f"📥 LLM response:\n{ai_text}\n")
                messages.append(AIMessage(content=ai_text))

                # ── Parse ACTION and ACTION_INPUT ──────────────
                # Parse FIRST action only (LLM sometimes plans multiple)
                action_name = None
                action_input = {}

                for line in ai_text.split("\n"):
                    stripped = line.strip()
                    upper = stripped.upper()
                    if upper.startswith("ACTION:") and not upper.startswith("ACTION_INPUT:"):
                        if action_name is None:  # Only take first ACTION
                            action_name = stripped.split(":", 1)[1].strip()
                    elif upper.startswith("ACTION_INPUT:"):
                        if action_name and not action_input:  # Only first INPUT
                            raw_input = stripped.split(":", 1)[1].strip()
                            # Strip trailing comments the LLM sometimes adds
                            json_match = _re.search(r'\{.*\}', raw_input)
                            if json_match:
                                raw_input = json_match.group(0)
                            try:
                                action_input = json.loads(raw_input)
                                # If LLM sent a plain string, wrap for browser_navigate
                                if isinstance(action_input, str):
                                    action_input = {"url": action_input}
                            except Exception:
                                # Try treating as a bare URL
                                if raw_input.startswith(('"', "'")):
                                    url = raw_input.strip('"\' ')
                                    action_input = {"url": url}
                                else:
                                    print(f"⚠️ Could not parse ACTION_INPUT: {raw_input}")

                # ── Check for DONE ─────────────────────────────
                # Only if no valid action was parsed (otherwise LLM is planning ahead)
                if (not action_name or action_name in ("DONE", "None", "none")) and (
                    "DONE" in ai_text or "completed" in ai_text.lower() or "finished" in ai_text.lower()
                ):
                    strict_done_passed = (
                        verification_state["cart_page_seen"] and
                        (verification_state["added_to_cart_seen"] or verification_state["cart_item_seen"])
                    )
                    if strict_done and not strict_done_passed:
                        missing = []
                        if not verification_state["cart_page_seen"]:
                            missing.append("visit cart page")
                        if not (verification_state["added_to_cart_seen"] or verification_state["cart_item_seen"]):
                            missing.append("cart success evidence")
                        msg = (
                            "DONE rejected by strict validation. Missing: "
                            + ", ".join(missing)
                            + ". Continue with tools: navigate/click to cart and verify item presence before DONE."
                        )
                        print(f"⚠ {msg}")
                        steps_detail.append({
                            "step": step + 1,
                            "thought": ai_text,
                            "action": "DONE_REJECTED",
                            "strict_validation": verification_state.copy(),
                            "reason": msg,
                        })
                        messages.append(HumanMessage(content=msg))
                        continue

                    print("✅ Agent says DONE!")
                    steps_detail.append({
                        "step": step + 1,
                        "thought": ai_text,
                        "action": "DONE",
                        "strict_validation": verification_state.copy(),
                    })
                    # ── Close browser cleanly on DONE ──────────
                    if "browser_close" in tools_dict:
                        print("🔒 Closing browser...")
                        try:
                            await tools_dict["browser_close"].ainvoke({})
                        except Exception:
                            pass
                    # BROWSER USE INTEGRATION — START
                    await _close_sandbox_if_needed()
                    # BROWSER USE INTEGRATION — END
                    return {
                        "status": "completed",
                        "response": ai_text,
                        "steps": step + 1,
                        "steps_detail": steps_detail,
                    }

                if not action_name or action_name not in tools_dict:
                    msg = (
                        f"Invalid or unknown action '{action_name}'. "
                        f"Available tools: {tool_names}. "
                        "Remember: to scroll use browser_evaluate with function () => window.scrollBy(0, 3000)."
                    )
                    print(f"⚠️ {msg}")
                    messages.append(HumanMessage(content=msg))
                    steps_detail.append({
                        "step": step + 1, "error": msg, "raw": ai_text
                    })
                    continue

                # ── Execute MCP tool ───────────────────────────
                # Normalize common schema mismatches from model outputs.
                if action_name == "browser_type" and isinstance(action_input, dict):
                    if "text" not in action_input and "value" in action_input:
                        action_input["text"] = action_input.pop("value")
                print(f"🎬 Executing: {action_name}({action_input})")
                try:
                    tool_result = await tools_dict[action_name].ainvoke(action_input)

                    # Extract text content properly (avoid repr escaping)
                    result_str = None
                    if isinstance(tool_result, list):
                        text_parts = []
                        for item in tool_result:
                            if isinstance(item, dict) and 'text' in item:
                                text_parts.append(item['text'])
                            elif hasattr(item, 'text'):
                                text_parts.append(item.text)
                            else:
                                text_parts.append(str(item))
                        result_str = '\n'.join(text_parts)
                    elif hasattr(tool_result, 'text'):
                        result_str = tool_result.text
                    elif isinstance(tool_result, str):
                        result_str = tool_result
                    else:
                        result_str = str(tool_result)

                    # If result_str still looks like repr of MCP content list,
                    # extract the text payload
                    if result_str.startswith("[{") or result_str.startswith("[Content"):
                        try:
                            import ast
                            parsed = ast.literal_eval(result_str)
                            if isinstance(parsed, list):
                                texts = [
                                    it['text'] for it in parsed
                                    if isinstance(it, dict) and 'text' in it
                                ]
                                if texts:
                                    result_str = '\n'.join(texts)
                        except Exception:
                            # Regex fallback: extract text between 'text': '...'
                            text_m = _re.search(
                                r"'text':\s*'((?:[^'\\]|\\.)*)'", result_str)
                            if text_m and len(text_m.group(1)) > 50:
                                result_str = text_m.group(1).replace(
                                    '\\n', '\n').replace("\\'", "'")

                    # Compress snapshots to keep only actionable content
                    max_prod = 3 if vitesse == "rapide" else None
                    if action_name in ("browser_navigate", "browser_snapshot"):
                        result_for_llm = self._compress_snapshot(result_str, max_products=max_prod)
                    else:
                        result_for_llm = result_str[:1500]
                        if len(result_str) > 1500:
                            result_for_llm += "\n... (truncated)"

                    # After a scroll action, wait 2s then auto-take a snapshot
                    # so the LLM sees updated products without a separate step.
                    if action_name == "browser_evaluate" and any(
                        kw in str(action_input.get("function", ""))
                        for kw in ("scrollBy", "scrollTo")
                    ):
                        import asyncio as _asyncio_scroll
                        await _asyncio_scroll.sleep(2)
                        print("📸 Auto-snapshot after scroll...")
                        snap_result = await session.call_tool("browser_snapshot", {})
                        snap_str = str(snap_result)
                        compressed = self._compress_snapshot(snap_str, max_products=max_prod)
                        action_name = "browser_snapshot"
                        # For prudent buyer: track cheapest across all scrolls,
                        # send only a compact summary instead of the full table
                        if vitesse != "rapide":
                            import re as _re2
                            def _extract_price_value(_label: str) -> float:
                                nums = _re2.findall(r'\d+(?:[.,]\d+)?', _label)
                                if not nums:
                                    return float("inf")
                                return float(nums[0].replace(',', '.'))

                            for _m in _re2.finditer(
                                r'- (.+?) \| ([^|]+?) \| View ref=(e\d+)', compressed
                            ):
                                _price_label = _m.group(2).strip()
                                _price_value = _extract_price_value(_price_label)
                                if not cheapest_product or _price_value < cheapest_product["price_value"]:
                                    cheapest_product = {
                                        "name": _m.group(1),
                                        "price_value": _price_value,
                                        "price_label": _price_label,
                                        "ref": _m.group(3),
                                    }
                            _count = len(_re2.findall(r'- .+ \| [^|]+ \| View ref=e\d+', compressed))
                            if cheapest_product:
                                _header = compressed.split("PRODUCTS:")[0].strip()
                                result_for_llm = (
                                    (_header + "\n" if _header else "") +
                                    f"PRODUCTS: {_count} loaded so far.\n"
                                    f"CHEAPEST SO FAR: {cheapest_product['name']} "
                                    f"| {cheapest_product['price_label']} "
                                    f"| View ref={cheapest_product['ref']}\n"
                                    "Scroll again to load more, or click View ref if bottom reached."
                                )
                                print(f"💰 Cheapest so far: {cheapest_product['price_label']} — {cheapest_product['name']}")
                            else:
                                result_for_llm = compressed
                        else:
                            result_for_llm = compressed

                    print(f"📤 Tool result ({len(result_str)} chars → {len(result_for_llm)} compressed):")
                    print(result_for_llm[:500] + "...\n")

                    if strict_done:
                        observed = f"{result_str}\n{result_for_llm}".lower()
                        if _re.search(r"added to cart|product has been added|successfully added", observed):
                            verification_state["added_to_cart_seen"] = True

                        url_match = _re.search(r"page url:\s*(\S+)", observed)
                        in_cart_page = False
                        if url_match:
                            current_url = url_match.group(1)
                            in_cart_page = bool(_re.search(r"view_cart|cart\.html|/cart|checkout", current_url))
                        if in_cart_page:
                            verification_state["cart_page_seen"] = True

                        if in_cart_page:
                            has_price = _re.search(r"(?:rs\.?|usd|eur|gbp|\$|€|£)\s*[\d.,]+", observed)
                            has_cart_terms = _re.search(
                                r"shopping cart|checkout|place order|remove|delete|qty|quantity|total",
                                observed,
                            )
                            if has_price and has_cart_terms:
                                verification_state["cart_item_seen"] = True

                except Exception as e:
                    error_text = str(e)
                    if "intercepts pointer events" in error_text:
                        recovered = False
                        # Try to close blocking overlays automatically (common on many sites).
                        try:
                            if "browser_press_key" in tools_dict:
                                await tools_dict["browser_press_key"].ainvoke({"key": "Escape"})
                                recovered = True
                        except Exception:
                            pass

                        try:
                            snap_after_escape = await session.call_tool("browser_snapshot", {})
                            snap_text = str(snap_after_escape)
                            close_btn = _re.search(
                                r'button\s+"[^"]*[Cc]lose[^"]*"\s*\[ref=(e\d+)\]',
                                snap_text,
                            )
                            if close_btn and "browser_click" in tools_dict:
                                await tools_dict["browser_click"].ainvoke({"ref": close_btn.group(1)})
                                recovered = True
                        except Exception:
                            pass

                        result_for_llm = (
                            f"TOOL ERROR: Click blocked by overlay.\n"
                            f"Auto-recovery attempted: {'success' if recovered else 'failed'}.\n"
                            "If a modal/dialog is open, close it first (Escape or close button), then retry the previous action.\n"
                            "Use browser_snapshot to refresh refs before retrying."
                        )
                    else:
                        result_for_llm = (
                            f"TOOL ERROR: {e}\n"
                            "Hint: if ref not found, use browser_snapshot for fresh refs."
                        )
                    result_str = result_for_llm
                    print(f"❌ Tool error: {e}")

                # BROWSER USE INTEGRATION — START
                # Take screenshot on key steps to give LLM visual context
                # Only on steps that change page content meaningfully
                visual_steps = (
                    "browser_navigate",
                    "browser_snapshot",
                    "browser_click",
                    "browser_type",
                )
                if (_use_observation_images
                        and bu_browser is not None
                        and action_name in visual_steps):
                    try:
                        self._last_screenshot = await self._capture_sandbox_screenshot(
                            bu_browser)
                        if self._last_screenshot:
                            print(f"👁️  Vision: screenshot attached to next LLM call")
                    except Exception as e:
                        print(f"⚠ Screenshot failed silently: {e}")
                        self._last_screenshot = None
                else:
                    self._last_screenshot = None
                # BROWSER USE INTEGRATION — END

                # ── Sliding window: compress old observations ──
                # Keep system msg + last 6 messages in full;
                # truncate older ones to save tokens
                if len(messages) > 6:
                    for i in range(1, len(messages) - 6):
                        msg = messages[i]
                        content = msg.content if hasattr(msg, 'content') else str(msg)
                        if len(content) > 100:
                            short = content[:80] + "..."
                            if isinstance(msg, AIMessage):
                                messages[i] = AIMessage(content=short)
                            elif isinstance(msg, HumanMessage):
                                messages[i] = HumanMessage(content=short)

                # ── Feed observation back ──────────────────────
                # BROWSER USE INTEGRATION — START
                observation_text = (
                    f"OBSERVATION ({action_name}):\n"
                    f"{result_for_llm}\n\n"
                    + (
                        "STRICT_DONE_STATUS: "
                        f"cart_page_seen={verification_state['cart_page_seen']}, "
                        f"added_to_cart_seen={verification_state['added_to_cart_seen']}, "
                        f"cart_item_seen={verification_state['cart_item_seen']}\n\n"
                        if strict_done else ""
                    )
                    + "Next?"
                )
                # VISION MODE — START
                vision_image_attached = False
                if self._last_screenshot and _use_observation_images:
                    messages.append(HumanMessage(
                        content=[
                            {"type": "text", "text": observation_text},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{self._last_screenshot}"
                                },
                            },
                        ]
                    ))
                    _current_llm = self.vision_llm
                    vision_image_attached = True
                else:
                    messages.append(HumanMessage(content=observation_text))
                    _current_llm = self.llm
                # VISION MODE — END
                # BROWSER USE INTEGRATION — END

                steps_detail.append({
                    "step": step + 1,
                    "thought": ai_text,
                    "action": action_name,
                    "input": action_input,
                    "vision_image_attached": vision_image_attached,
                    "result_preview": result_str[:1000],
                })

            # Max steps reached
            print(f"\n⏱️ Reached maximum steps ({max_steps})")
            # BROWSER USE INTEGRATION — START
            await _close_sandbox_if_needed()
            # BROWSER USE INTEGRATION — END
            return {
                "status": "max_steps_reached",
                "response": "Max steps reached",
                "steps": max_steps,
                "steps_detail": steps_detail,
            }
