"""
PlaywrightTestAgent - Generates and executes Playwright test scripts using two MCP servers:
  1. fetch_page_dom  → custom MCP server: fetches cleaned DOM for LLM context
  2. LLM             → generates a Playwright JS test script from DOM + persona objective
  3. execute_playwright_test → custom MCP server: runs the script and returns logs/screenshots

Input : persona dict, website URL
Output: { script, logs, success, screenshot, duration_ms }
"""

import os
import json
import time
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Path to the custom MCP server
CUSTOM_MCP_SERVER_PATH = Path(__file__).parent / "server.js"


class PlaywrightTestAgent:
    """
    Orchestrates:
      1. DOM fetching via custom MCP server
      2. LLM script generation
      3. Script execution via custom MCP server
      4. Result collection
    """

    def __init__(self, provider: str = "groq", model: str = None, temperature: float = 0.2):
        self.provider = provider
        self.temperature = temperature
        self.llm = self._init_llm(provider, model)

    def _init_llm(self, provider: str, model: str = None) -> ChatOpenAI:
        if provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            return ChatOpenAI(
                model=model or os.getenv("OLLAMA_MODEL", "qwen3.5:cloud"),
                base_url=base_url,
                api_key="ollama",
                temperature=self.temperature,
                max_tokens=4000,
            )
        if provider == "groq":
            from langchain_groq import ChatGroq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set")
            return ChatGroq(
                model=model or "llama-3.3-70b-versatile",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=4000,
            )
        elif provider == "github":
            api_key = os.getenv("GITHUB_TOKEN")
            if not api_key:
                raise ValueError("GITHUB_TOKEN not set")
            return ChatOpenAI(
                model=model or "gpt-4o-mini",
                base_url="https://models.github.ai/inference",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=4000,
            )
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not set")
            return ChatGoogleGenerativeAI(
                model=model or "gemini-1.5-flash",
                google_api_key=api_key,
                temperature=self.temperature,
                max_output_tokens=4000,
            )
        else:  # openai default
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            return ChatOpenAI(
                model=model or "gpt-4o-mini",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=4000,
            )

    def _generate_script(
        self,
        url: str,
        dom_html: str,
        persona: Dict[str, Any],
        page_title: str = "",
    ) -> str:
        """
        Use LLM to generate a Playwright JS test script from the DOM and persona context.
        """
        objectif = persona.get("objectif", "Test the website functionality")
        vitesse = persona.get("vitesse_navigation", "normale")
        device = persona.get("device", "desktop")
        persona_name = persona.get("nom", "Test User")
        comportements = persona.get("comportements_specifiques", [])
        actions_site = persona.get("actions_site", [])

        comportements_text = "\n".join(f"- {c}" for c in comportements) if comportements else ""
        actions_text = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(actions_site)) if actions_site else ""

        # Truncate DOM to avoid token limits — keep first 8000 chars (most important structure)
        dom_truncated = dom_html[:8000] + "\n... [DOM truncated]" if len(dom_html) > 8000 else dom_html

        prompt = f"""You are an expert Playwright test script generator.

Generate a complete, executable Playwright JavaScript test script for the following context.

## Target Website
- URL: {url}
- Page Title: {page_title}

## Persona: {persona_name}
- Objective: {objectif}
- Navigation Speed: {vitesse}
- Device: {device}
{f"- Specific Behaviors:{chr(10)}{comportements_text}" if comportements_text else ""}
{f"- Expected Action Sequence:{chr(10)}{actions_text}" if actions_text else ""}

## Page DOM Structure
```html
{dom_truncated}
```

## Requirements
1. The script uses variables already available: `page`, `context`, `browser`, `executionLog` (array)
2. Use `executionLog.push('message')` to log important steps
3. The script must navigate to: `{url}`
4. Implement the persona's objective: {objectif}
5. Use realistic selectors derived from the actual DOM above
6. Configure defaults at the beginning of the script:
    - `await page.setDefaultNavigationTimeout(30000)`
    - `await page.setDefaultTimeout(30000)`
    Always use 30s timeout for navigation and loading waits by default.
7. Add appropriate loading waits with explicit timeout when relevant, e.g. `await page.waitForLoadState('load', {{ timeout: 30000 }})` or `await page.waitForLoadState('networkidle', {{ timeout: 30000 }})`
8. Handle potential popups, cookie banners, or overlays that may block interaction
9. {'Navigate quickly, minimal waits (500ms max)' if vitesse == 'rapide' else 'Navigate carefully with longer waits (1000-2000ms)'}
10. {'Use mobile viewport: await page.setViewportSize({{ width: 390, height: 844 }})' if device == 'mobile' else 'Use desktop viewport: await page.setViewportSize({{ width: 1280, height: 800 }})'}
11. End with logging a summary of what was accomplished

## Output Format
Return ONLY the raw JavaScript code — no markdown fences, no explanation, no comments outside the script.
The script body will be injected into an async function. Do NOT include `async function` wrapper.

Example structure:
executionLog.push('Starting test for {persona_name}...');
await page.setViewportSize({{ width: 1280, height: 800 }});
await page.setDefaultNavigationTimeout(30000);
await page.setDefaultTimeout(30000);
await page.goto('{url}', {{ waitUntil: 'domcontentloaded', timeout: 30000 }});
await page.waitForLoadState('networkidle', {{ timeout: 30000 }});
// ... rest of test ...
executionLog.push('Test completed successfully');
"""

        messages = [
            SystemMessage(content=(
                "You are an expert Playwright test automation engineer. "
                "You generate precise, executable JavaScript test scripts based on real DOM structure. "
                "Always use selectors that exist in the provided DOM. "
                "At the top of every generated script, set Playwright defaults with "
                "page.setDefaultNavigationTimeout(30000) and page.setDefaultTimeout(30000). "
                "Use 30000ms timeout by default for page.goto and page.waitForLoadState calls. "
                "Return ONLY raw JavaScript — no markdown, no explanations."
            )),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        script = response.content.strip()

        # Strip any accidental markdown fences
        if script.startswith("```"):
            lines = script.split("\n")
            script = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        return script

    async def fetch_dom(self, url: str) -> Dict[str, Any]:
        """Fetch cleaned DOM for URL through the custom MCP server."""
        server_params = StdioServerParameters(
            command="node",
            args=[str(CUSTOM_MCP_SERVER_PATH)],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                dom_result_raw = await session.call_tool("fetch_page_dom", {"url": url})

                dom_text = ""
                if isinstance(dom_result_raw, list):
                    for item in dom_result_raw:
                        if isinstance(item, dict) and "text" in item:
                            dom_text += item["text"]
                        elif hasattr(item, "text"):
                            dom_text += item.text
                elif hasattr(dom_result_raw, "content"):
                    for item in dom_result_raw.content:
                        if hasattr(item, "text"):
                            dom_text += item.text
                else:
                    dom_text = str(dom_result_raw)

                try:
                    dom_data = json.loads(dom_text)
                except (json.JSONDecodeError, TypeError):
                    dom_data = {"success": False, "dom": "", "title": "", "error": {"message": "Parse error"}}

                return dom_data

    async def generate_test_script(
        self,
        url: str,
        persona: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate and return Playwright script without executing it."""
        start_time = time.time()
        dom_snapshot = None
        page_title = ""
        generation_log = []

        try:
            generation_log.append(f"Fetching DOM for {url}")
            dom_data = await self.fetch_dom(url)
            if dom_data.get("success"):
                dom_snapshot = dom_data.get("dom", "")
                page_title = dom_data.get("title", "")
                generation_log.append(f"DOM fetched ({len(dom_snapshot)} chars)")
            else:
                err_msg = (dom_data.get("error") or {}).get("message", "unknown error")
                generation_log.append(f"DOM fetch failed: {err_msg}. Using URL-only context")
                dom_snapshot = f"<html><body><p>Could not fetch DOM for {url}</p></body></html>"

            generation_log.append("Generating Playwright script with LLM")
            script = self._generate_script(url, dom_snapshot or "", persona, page_title)
            generation_log.append(f"Script generated ({len(script.splitlines())} lines)")

            return {
                "status": "pending",
                "dom_snapshot": dom_snapshot,
                "generated_script": script,
                "execution_log": generation_log,
                "error_message": None,
                "duration_ms": int((time.time() - start_time) * 1000),
            }
        except Exception as e:
            return {
                "status": "error",
                "dom_snapshot": dom_snapshot,
                "generated_script": None,
                "execution_log": generation_log,
                "error_message": str(e),
                "duration_ms": int((time.time() - start_time) * 1000),
            }

    async def execute_script(
        self,
        test_script: str,
        browser_name: str = "chromium",
        show_browser: bool = True,
        keep_browser_open_ms: int = 3000,
        slow_mo_ms: int = 100,
    ) -> Dict[str, Any]:
        """Execute an existing Playwright script through custom MCP server."""
        start_time = time.time()
        server_params = StdioServerParameters(
            command="node",
            args=[str(CUSTOM_MCP_SERVER_PATH)],
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    exec_result_raw = await session.call_tool(
                        "execute_playwright_test",
                        {
                            "testScript": test_script,
                            "browserName": browser_name,
                            "showBrowser": show_browser,
                            "keepBrowserOpenMs": keep_browser_open_ms,
                            "slowMoMs": slow_mo_ms,
                        },
                    )

                    exec_text = ""
                    if isinstance(exec_result_raw, list):
                        for item in exec_result_raw:
                            if isinstance(item, dict) and "text" in item:
                                exec_text += item["text"]
                            elif hasattr(item, "text"):
                                exec_text += item.text
                    elif hasattr(exec_result_raw, "content"):
                        for item in exec_result_raw.content:
                            if hasattr(item, "text"):
                                exec_text += item.text
                    else:
                        exec_text = str(exec_result_raw)

                    try:
                        exec_data = json.loads(exec_text)
                    except (json.JSONDecodeError, TypeError):
                        exec_data = {"success": False, "executionLog": [], "error": {"message": "Parse error"}}

                    logs = exec_data.get("executionLog", [])
                    screenshots = exec_data.get("screenshots", [])
                    screenshot_b64 = screenshots[0]["data"] if screenshots else None

                    err = exec_data.get("error") or {}
                    error_message = err.get("message") if not exec_data.get("success") else None

                    return {
                        "status": "success" if exec_data.get("success") else "error",
                        "execution_log": logs,
                        "error_message": error_message,
                        "screenshot_base64": screenshot_b64,
                        "duration_ms": int((time.time() - start_time) * 1000),
                    }
        except Exception as e:
            return {
                "status": "error",
                "execution_log": [],
                "error_message": str(e),
                "screenshot_base64": None,
                "duration_ms": int((time.time() - start_time) * 1000),
            }

    async def run(
        self,
        url: str,
        persona: Dict[str, Any],
        browser_name: str = "chromium",
    ) -> Dict[str, Any]:
        """
        Full pipeline:
          1. Connect to custom MCP server
          2. fetch_page_dom(url) → DOM context
          3. LLM generates script from DOM + persona
          4. execute_playwright_test(script) → logs + screenshot
          5. Return structured result
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()

        print(f"\n{'='*60}")
        print(f"🎭 PlaywrightTestAgent starting")
        print(f"   URL: {url}")
        print(f"   Persona: {persona.get('nom', 'Unknown')}")
        print(f"   Execution ID: {execution_id}")
        print(f"{'='*60}\n")

        result = {
            "id": execution_id,
            "url": url,
            "persona_id": persona.get("id", "unknown"),
            "browser_name": browser_name,
            "dom_snapshot": None,
            "generated_script": None,
            "status": "error",
            "execution_log": [],
            "error_message": None,
            "screenshot_base64": None,
            "duration_ms": 0,
        }

        try:
            print(f"\n📄 Step 1: Fetching DOM from {url}...")
            generated = await self.generate_test_script(url=url, persona=persona)
            result["dom_snapshot"] = generated.get("dom_snapshot")
            result["generated_script"] = generated.get("generated_script")
            result["execution_log"] = generated.get("execution_log", [])

            if generated.get("status") == "error" or not result["generated_script"]:
                result["status"] = "error"
                result["error_message"] = generated.get("error_message") or "Script generation failed"
                duration_ms = int((time.time() - start_time) * 1000)
                result["duration_ms"] = duration_ms
                return result

            print(f"\n▶️  Step 3: Executing script in {browser_name}...")
            executed = await self.execute_script(result["generated_script"], browser_name=browser_name)
            result["status"] = executed.get("status", "error")
            result["execution_log"] = executed.get("execution_log", [])
            result["screenshot_base64"] = executed.get("screenshot_base64")
            result["error_message"] = executed.get("error_message")

            print(f"\n📋 Execution Log ({len(result['execution_log'])} entries):")
            for line in result["execution_log"]:
                print(f"   {line}")

        except Exception as e:
            result["error_message"] = str(e)
            result["status"] = "error"
            print(f"❌ Agent error: {e}")

        duration_ms = int((time.time() - start_time) * 1000)
        result["duration_ms"] = duration_ms
        print(f"\n⏱️  Total duration: {duration_ms}ms")
        return result


async def run_playwright_test(
    url: str,
    persona: Dict[str, Any],
    provider: str = "groq",
    browser_name: str = "chromium",
) -> Dict[str, Any]:
    """Convenience wrapper."""
    agent = PlaywrightTestAgent(provider=provider)
    return await agent.run(url=url, persona=persona, browser_name=browser_name)
