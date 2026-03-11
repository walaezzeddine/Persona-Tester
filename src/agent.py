

import os
import time
import asyncio
import json
from typing import Dict, List, Optional, Any
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
    def _compress_snapshot(raw: str, max_chars: int = 4000) -> str:
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

        # ── Extract products from accessibility snapshot ───────
        # Prices:  heading "Rs. 500" [level=2] [ref=eXX]
        prices = list(re.finditer(
            r'heading\s+"Rs\.\s*(\d+)".*?\[ref=(e\d+)\]', raw))
        # Names:   paragraph [ref=eXX]: Blue Top  (actual Playwright format)
        names = list(re.finditer(
            r'paragraph\s*\[ref=(e\d+)\]:\s*(.+)', raw))
        # View:    link " View Product" [ref=eXX]
        views = list(re.finditer(
            r'link\s+"[^"]*[Vv]iew [Pp]roduct[^"]*"\s*\[ref=(e\d+)\]', raw))

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

        # Deduplicate (overlay creates duplicates with same name)
        seen = set()
        unique = []
        for name, price, ref in products:
            key = name.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(f"- {name} | Rs. {price} | View ref={ref}")

        if unique:
            parts.append("PRODUCTS:\n" + "\n".join(unique))

        # ── Other interactive elements (search, buttons) ───────
        textboxes = re.findall(
            r'textbox\s+"([^"]*)".*?\[ref=(e\d+)\]', raw)
        buttons_found = re.findall(
            r'button\s+"([^"]*)".*?\[ref=(e\d+)\]', raw)
        extras = []
        for label, ref in textboxes[:3]:
            extras.append(f"- textbox \"{label}\" ref={ref}")
        for label, ref in buttons_found[:3]:
            extras.append(f"- button \"{label}\" ref={ref}")
        if extras:
            parts.append("OTHER:\n" + "\n".join(extras))

        result = "\n\n".join(parts)

        # ── Fallback: if no products extracted, use line filter ─
        if not unique:
            keep_re = re.compile(
                r'Rs\.\s*\d|add to cart|view product|textbox|button'
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

    async def run_with_mcp(self, start_url: str) -> Dict[str, Any]:
        """
        ReAct agent loop: LLM decides each action, MCP executes it.

        Uses ``stdio_client`` + ``ClientSession`` (same as run_with_mcp_direct)
        to keep a single stable browser session across all steps.
        """
        import re as _re
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from langchain_mcp_adapters.tools import load_mcp_tools

        headless_args = ["--headless"] if self.config.headless else []

        print("\n" + "=" * 80)
        print("🚀 MCP ReAct SESSION STARTING")
        print("=" * 80)
        print(f"📍 Target URL: {start_url}")
        print(f"👤 Persona: {self.user.get('id', self.user.get('nom', 'Unknown'))}")
        print(f"🎯 Scenario: {self.scenario.get('objectif', 'Unknown')}")
        print()

        # ── Connect via stdio (keeps session alive) ────────────────
        print("🔌 Connecting to Playwright MCP Server...")
        server_params = StdioServerParameters(
            command="npx",
            args=["@playwright/mcp"] + headless_args,
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
                "browser_select_option", "browser_wait_for",
            ]
            tools_text = "\n".join(
                f"- {t.name}: {t.description[:80]}"
                for t in tools if t.name in useful_tools
            )

            objectif = self.scenario.get("objectif", "Complete the task")

            # ── Persona-specific strategy ──────────────────────
            vitesse = self.user.get("vitesse_navigation", "rapide")
            persona_id = self.user.get("id", "unknown")
            if vitesse == "rapide":
                # Impatient buyer: grab the cheapest visible immediately
                strategy = (
                    "STRATEGY (impatient buyer): You are in a hurry.\n"
                    "- After navigating to /products, look at the PRODUCTS table in the OBSERVATION.\n"
                    "- Pick the cheapest t-shirt you see RIGHT NOW — do NOT scroll down.\n"
                    "- Click its View Product ref immediately, then Add to Cart on the detail page.\n"
                    "- Be fast: navigate → pick cheapest visible → View Product → Add to Cart → DONE.\n"
                )
            else:
                # Prudent buyer: scroll through everything first
                strategy = (
                    "STRATEGY (prudent buyer): You are careful and thorough.\n"
                    "- After navigating to /products, scroll down to see ALL products.\n"
                    "- Use browser_press_key {\"key\": \"PageDown\"} then browser_snapshot MULTIPLE TIMES "
                    "until you have seen every product on the page.\n"
                    "- Keep a mental note of ALL product names and prices as you scroll.\n"
                    "- After scrolling through the entire page, decide which t-shirt is the cheapest.\n"
                    "- Then click its View Product ref, and Add to Cart on the detail page.\n"
                    "- Do NOT pick a product before you have scrolled to the bottom of the page.\n"
                )

            # ── System prompt (sent once, compact) ─────────────
            system_msg = SystemMessage(content=(
                "You are a web automation agent.\n\n"
                f"TOOLS:\n{tools_text}\n\n"
                f"OBJECTIVE: {objectif}\n"
                f"PERSONA: {persona_id} (speed: {vitesse})\n"
                f"START URL: {start_url}\n\n"
                f"{strategy}\n"
                "RULES:\n"
                "1. After browser_navigate or browser_snapshot, the OBSERVATION contains a "
                "PRODUCTS table like:\n"
                "   PRODUCTS:\n"
                "   - Blue Top | Rs. 500 | View ref=e116\n"
                "   - Men Tshirt | Rs. 400 | View ref=e130\n"
                "   READ this table to find product names, prices, and View Product refs.\n"
                "2. To add a product to cart, do these 2 steps:\n"
                "   a) browser_click {\"ref\": \"e130\"} — click the View Product ref for the product\n"
                "   b) On the product detail page, take a browser_snapshot, find the 'Add to Cart' "
                "button ref, and browser_click {\"ref\": \"eXXX\"}\n"
                "3. Do NOT click 'Add to cart' directly on the products list page — it will fail.\n"
                "   Always go through View Product first.\n"
                "4. Do NOT use browser_evaluate. The PRODUCTS table has everything you need.\n"
                "5. To scroll: browser_press_key {\"key\": \"PageDown\"}, then browser_snapshot.\n"
                "6. If a Google ad appears (URL contains #google_vignette), navigate directly: "
                "browser_navigate {\"url\": \"" + start_url + "/products\"}.\n"
                "7. ACTION_INPUT must be valid JSON: {\"key\": \"value\"}, not a plain string.\n\n"
                "EXAMPLE WORKFLOW:\n"
                "Step 1 → THOUGHT: Navigate to products.\n"
                "ACTION: browser_navigate\nACTION_INPUT: {\"url\": \"" + start_url + "/products\"}\n\n"
                "Step 2 → THOUGHT: I see Men Tshirt at Rs. 400 with View ref=e130. "
                "This is the cheapest. I'll click View Product.\n"
                "ACTION: browser_click\nACTION_INPUT: {\"ref\": \"e130\"}\n\n"
                "Step 3 → THOUGHT: I'm on the product detail page. I see Add to Cart ref=e50.\n"
                "ACTION: browser_click\nACTION_INPUT: {\"ref\": \"e50\"}\n\n"
                "Step 4 → THOUGHT: Product added to cart.\nDONE\n\n"
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

            messages.append(HumanMessage(
                content=(
                    f"Begin. Navigate to {start_url}/products and complete the objective.\n"
                    "Read the PRODUCTS table in the observation to find product names, prices, and refs."
                )
            ))

            for step in range(max_steps):
                print(f"\n{'=' * 80}")
                print(f"STEP {step + 1}/{max_steps}")
                print("=" * 80)

                # ── Anti-loop: detect repeated identical actions ──
                if len(steps_detail) >= 3:
                    last3 = [s.get("action") for s in steps_detail[-3:]]
                    if len(set(last3)) == 1 and last3[0] in ("browser_snapshot", "browser_press_key"):
                        nudge = (
                            f"WARNING: You repeated '{last3[0]}' 3 times with no progress. "
                            "Stop repeating. Read the OBSERVATION above — it contains a PRODUCTS "
                            "table with names, prices, and Add-to-cart refs. Pick the cheapest "
                            "t-shirt and click its ref with browser_click."
                        )
                        print(f"⚠️ Anti-loop nudge injected")
                        messages.append(HumanMessage(content=nudge))
                    elif len(set(last3)) == 1 and last3[0] == "browser_evaluate":
                        nudge = (
                            "WARNING: browser_evaluate failed 3 times. STOP using it. "
                            "Instead, take a browser_snapshot — the OBSERVATION will contain "
                            "a PRODUCTS table with names, prices, and Add-to-cart refs. "
                            "Read the table and use browser_click {\"ref\": \"eXXX\"} to add to cart."
                        )
                        print(f"⚠️ Anti-evaluate-loop nudge injected")
                        messages.append(HumanMessage(content=nudge))
                if len(steps_detail) >= 2:
                    last2_errs = [s for s in steps_detail[-2:] if s.get("error")]
                    if len(last2_errs) == 2:
                        nudge = (
                            "WARNING: 2 consecutive errors. Make sure to include all 3 lines: "
                            "THOUGHT, ACTION, and ACTION_INPUT. ACTION_INPUT must be valid JSON."
                        )
                        messages.append(HumanMessage(content=nudge))

                # ── Call LLM (with retry on rate-limit) ────────
                import asyncio as _asyncio
                print("🤖 Calling LLM...")
                ai_text = None
                error_msg = ""
                for _attempt in range(5):
                    try:
                        response = self.llm.invoke(messages)
                        ai_text = response.content if hasattr(response, "content") else str(response)
                        break  # success
                    except Exception as e:
                        error_msg = str(e)
                        if "413" in error_msg or "tokens_limit_reached" in error_msg:
                            print(f"❌ Token limit exceeded: {error_msg}")
                            return {
                                "status": "error",
                                "response": f"Token limit exceeded: {error_msg}",
                                "steps": step + 1,
                                "steps_detail": steps_detail,
                            }
                        if "Too many requests" in error_msg or "429" in error_msg:
                            wait = 20 * (_attempt + 1)
                            print(f"⏳ Rate limited (attempt {_attempt+1}/5). Waiting {wait}s...")
                            try:
                                await _asyncio.sleep(wait)
                            except (asyncio.CancelledError, Exception):
                                print("❌ MCP session cancelled during rate-limit wait — aborting")
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
                    if "Too many requests" in error_msg or "429" in error_msg:
                        print("❌ Rate limit exhausted after 5 retries — aborting run")
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
                    print("✅ Agent says DONE!")
                    steps_detail.append({
                        "step": step + 1,
                        "thought": ai_text,
                        "action": "DONE",
                    })
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
                        "Remember: to scroll use browser_press_key with key PageDown."
                    )
                    print(f"⚠️ {msg}")
                    messages.append(HumanMessage(content=msg))
                    steps_detail.append({
                        "step": step + 1, "error": msg, "raw": ai_text
                    })
                    continue

                # ── Execute MCP tool ───────────────────────────
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
                    if action_name in ("browser_navigate", "browser_snapshot"):
                        result_for_llm = self._compress_snapshot(result_str)
                    else:
                        result_for_llm = result_str[:1500]
                        if len(result_str) > 1500:
                            result_for_llm += "\n... (truncated)"

                    print(f"📤 Tool result ({len(result_str)} chars → {len(result_for_llm)} compressed):")
                    print(result_for_llm[:500] + "...\n")

                except Exception as e:
                    error_text = str(e)
                    if "intercepts pointer events" in error_text:
                        result_for_llm = (
                            f"TOOL ERROR: Click blocked by overlay.\n"
                            "IMPORTANT: Do NOT click 'Add to cart' on the product list page.\n"
                            "Instead: 1) Click the View Product ref for that product, "
                            "2) On the detail page, use browser_snapshot to find the 'Add to Cart' button ref, "
                            "3) browser_click that ref."
                        )
                    else:
                        result_for_llm = (
                            f"TOOL ERROR: {e}\n"
                            "Hint: if ref not found, use browser_snapshot for fresh refs."
                        )
                    result_str = result_for_llm
                    print(f"❌ Tool error: {e}")

                # ── Sliding window: compress old observations ──
                # Keep system msg + last 6 messages in full;
                # truncate older ones to save tokens
                if len(messages) > 8:
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
                messages.append(HumanMessage(
                    content=(
                        f"OBSERVATION ({action_name}):\n"
                        f"{result_for_llm}\n\n"
                        "Next?"
                    )
                ))

                steps_detail.append({
                    "step": step + 1,
                    "thought": ai_text,
                    "action": action_name,
                    "input": action_input,
                    "result_preview": result_str[:1000],
                })

            # Max steps reached
            print(f"\n⏱️ Reached maximum steps ({max_steps})")
            return {
                "status": "max_steps_reached",
                "response": "Max steps reached",
                "steps": max_steps,
                "steps_detail": steps_detail,
            }

    async def run_with_mcp_direct(self, url: str, objectif: str) -> Dict[str, Any]:
        """
        Hybrid approach: Python drives navigation directly via MCP tools,
        LLM only analyzes the snapshot to find the target element ref.
        """
        import time as _time
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from langchain_mcp_adapters.tools import load_mcp_tools

        t_start = _time.time()

        # ── STEP 1 : Connect to Playwright MCP Server ─────────────────────
        print("\n" + "="*70)
        print("🔌 STEP 1 — Connecting to Playwright MCP Server...")
        server_params = StdioServerParameters(
            command="npx",
            args=["@playwright/mcp"],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                tools_dict = {t.name: t for t in tools}
                print(f"✓ Connected — {len(tools_dict)} tools available")

                # ── STEP 2 : Navigate directly (Python, not LLM) ──────────
                print("\n" + "="*70)
                print("🌐 STEP 2 — Navigating to products page...")
                await tools_dict["browser_navigate"].arun(
                    {"url": "https://automationexercise.com/products"}
                )
                print("✓ Navigation complete")
                await asyncio.sleep(3)

                # Remove the advertisement overlay that intercepts clicks
                if "browser_evaluate" in tools_dict:
                    try:
                        await tools_dict["browser_evaluate"].arun(
                            {"function": "() => { const ad = document.querySelector('#advertisement'); if (ad) ad.remove(); document.querySelectorAll('.overlay-content').forEach(e => e.style.pointerEvents = 'none'); return 'done'; }"}
                        )
                        print("✓ Ad overlay removed")
                    except Exception as e:
                        print(f"  ⚠ Could not remove overlay: {e}")

                # Take a fresh snapshot with updated refs
                snapshot_result = await tools_dict["browser_snapshot"].arun({})
                await asyncio.sleep(1)

                # ── STEP 3 : Ask LLM to analyse snapshot ──────────────────
                print("\n" + "="*70)
                print("🤖 STEP 3 — Asking LLM to find cheapest T-SHIRT...")
                snapshot_text = str(snapshot_result)[:15000]

                # Extract product lines from MCP accessibility snapshot
                # Each product card: paragraph with name, "Rs. XXX", then "Add to cart" button [ref=eXXX]
                import re
                raw_text = str(snapshot_result)
                # Use non-greedy matching within each product card block
                # The snapshot has: paragraph "ProductName" ... Rs. XXX ... "Add to cart" [ref=eXXX]
                blocks = re.findall(
                    r'paragraph\s*\[ref=e\d+\]:\s*"([^"]+)".*?Rs\.\s*(\d+).*?(?:link|button)\s+"[^"]*Add to cart[^"]*"\s*\[ref=(e\d+)\]',
                    raw_text
                )
                if not blocks:
                    # Try heading pattern
                    blocks = re.findall(
                        r'heading\s+"([^"]+)"\s*\[level=\d+\].*?Rs\.\s*(\d+).*?(?:link|button)\s+"[^"]*Add to cart[^"]*"\s*\[ref=(e\d+)\]',
                        raw_text
                    )
                if blocks:
                    products_summary = "\n".join(
                        f"{name} — Rs. {price} — Add to cart ref={ref}"
                        for name, price, ref in blocks
                    )
                    print(f"  → Extracted {len(blocks)} products")
                else:
                    # Fallback: send truncated raw snapshot (stay within ~8000 token limit)
                    products_summary = snapshot_text[:3000]
                    print("  → Using truncated snapshot (3000 chars)")

                persona_id = self.user.get("id", "unknown")
                vitesse = self.user.get("vitesse_navigation", "normale")
                sensibilite_prix = self.user.get("sensibilite_prix", "moyenne")
                patience = self.user.get("patience_attente_sec", 10)

                if vitesse == "rapide":
                    comportement = "Tu navigues VITE et tu n'as pas le temps de comparer. Tu cliques sur le PREMIER produit que tu vois sans lire tous les prix."
                else:
                    comportement = "Tu navigues LENTEMENT et tu compares TOUS les prix avant de décider. Tu choisis toujours le produit LE MOINS CHER."

                analysis_prompt = f"""
Tu es un acheteur avec ce profil :
- ID: {persona_id}
- Vitesse de navigation: {vitesse}
- Sensibilité au prix: {sensibilite_prix}
- Patience: {patience} secondes

{comportement}

Voici les produits disponibles :
{products_summary}

Quel produit T-SHIRT tu achètes ?

Réponds UNIQUEMENT avec ce JSON :
{{"produit": "nom", "prix": "Rs. XXX", "ref": "eXXX", "raison": "explication en 1 phrase"}}

Le ref est celui du bouton "Add to cart" du produit choisi.
"""

                messages = [
                    SystemMessage(content="Tu es un assistant d'extraction de données web."),
                    HumanMessage(content=analysis_prompt),
                ]

                llm_response = self.llm.invoke(messages)
                raw = llm_response.content.strip()
                print(f"\n📥 LLM raw response:\n{raw}")

                # ── STEP 4 : Parse JSON response ───────────────────────────
                print("\n" + "="*70)
                print("🔍 STEP 4 — Parsing LLM response...")
                # Strip markdown code fences if present
                cleaned = raw
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("```", 1)[0]
                cleaned = cleaned.strip()

                choice = json.loads(cleaned)
                print(f"✓ Cheapest T-SHIRT : {choice['produit']}")
                print(f"  Prix             : {choice['prix']}")
                print(f"  Ref bouton       : {choice['ref']}")

                # ── STEP 5 : Click the chosen product ──────────────────
                print("\n" + "="*70)
                print(f"🖱️  STEP 5 — Clicking 'Add to cart' (ref={choice['ref']})...")
                click_result = await tools_dict["browser_click"].arun(
                    {"ref": choice["ref"]}
                )
                print(f"✓ Click result:\n{click_result}")
                await asyncio.sleep(5)

                # ── STEP 6 : Return result ─────────────────────────────────
                duree = round(_time.time() - t_start, 2)
                print("\n" + "="*70)
                print(f"✅ Done in {duree}s")

                return {
                    "statut": "success",
                    "output": str(click_result),
                    "persona": persona_id,
                    "produit": choice["produit"],
                    "prix": choice["prix"],
                    "ref": choice["ref"],
                    "url": url,
                    "objectif": objectif,
                    "duree_sec": duree,
                    "nb_etapes": 2,
                }

