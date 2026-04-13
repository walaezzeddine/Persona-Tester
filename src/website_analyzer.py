"""
Website Analyzer - LLM 1
Analyzes a website to understand its structure, features, and target audience.

Input: Website URL
Output: Website description (JSON with structure, features, target users, pricing model, etc.)
"""

import os
import json
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Import web search tool for enriched analysis
from src.web_search_tool import WebSearchTool


class WebsiteAnalyzer:
    """
    LLM-powered website analyzer that:
    1. Searches the web for information about the website
    2. Fetches website content
    3. Understands structure and features
    4. Generates a comprehensive description
    """

    def __init__(self, provider: str = "openai", model: str = None, temperature: float = 0.7, 
                 enable_web_search: bool = True):
        """
        Initialize the Website Analyzer with an LLM.

        Args:
            provider: LLM provider ('openai', 'groq', 'github', 'google')
            model: Model name (defaults based on provider)
            temperature: LLM temperature for creativity
            enable_web_search: Whether to use web search for enriched analysis
        """
        self.provider = provider
        self.temperature = temperature
        self.llm = self._init_llm(provider, model)
        self.enable_web_search = enable_web_search
        self.web_search = WebSearchTool(max_results=3) if enable_web_search else None

    def _init_llm(self, provider: str, model: str = None) -> ChatOpenAI:
        """Initialize LLM based on provider."""
        if provider == "google":
            google_key = os.getenv("GOOGLE_API_KEY")
            if not google_key:
                raise ValueError("GOOGLE_API_KEY not set in .env")
            return ChatGoogleGenerativeAI(
                model=model or "gemini-1.5-flash",
                google_api_key=google_key,
                temperature=self.temperature,
                max_output_tokens=2000,
            )
        elif provider == "groq":
            from langchain_groq import ChatGroq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set in .env")
            return ChatGroq(
                model=model or "llama-3.3-70b-versatile",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=2000,
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
                max_tokens=2000,
            )
        else:  # openai (default)
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in .env")
            return ChatOpenAI(
                model=model or "gpt-4o-mini",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=2000,
            )

    def _fetch_website_content(self, url: str, timeout: int = 10) -> tuple[str, bool]:
        """
        Fetch website content using multiple strategies.
        Returns (content, success) tuple for graceful fallback.

        Falls back gracefully if one method fails:
        - Returns empty string if scraping is unavailable/blocked
        - Allows analysis to continue with URL-based inference only
        """
        from urllib.request import urlopen, Request
        import ssl

        print(f"📥 Attempting to fetch content from {url}...")

        # Try urllib first (built-in)
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # Add user-agent to avoid being blocked
            request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(request, timeout=timeout, context=context) as response:
                content = response.read(50000)  # Limit to first 50KB
                print(f"✅ Successfully fetched content ({len(content)} bytes)")
                return content.decode('utf-8', errors='ignore'), True
        except Exception as e:
            print(f"⚠️  urllib failed: {e}")

        # Try requests library if available
        try:
            import requests
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, timeout=timeout, headers=headers)
            if resp.status_code == 200:
                print(f"✅ Successfully fetched with requests ({len(resp.text)} bytes)")
                return resp.text[:50000], True
            else:
                print(f"⚠️  HTTP {resp.status_code}")
        except ImportError:
            print("⚠️  requests library not available")
        except Exception as e:
            print(f"⚠️  requests failed: {e}")

        # Graceful fallback: return empty string but mark as not fetched
        print("⚠️  Could not fetch website content (site may block bots or be unavailable)")
        print("   ℹ️  Continuing with URL-based analysis...")
        return "", False

    def _extract_text_from_html(self, html: str) -> str:
        """Extract readable text from HTML."""
        try:
            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text_parts = []
                    self.skip_script = False

                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style"):
                        self.skip_script = True

                def handle_endtag(self, tag):
                    if tag in ("script", "style"):
                        self.skip_script = False

                def handle_data(self, data):
                    if not self.skip_script:
                        cleaned = data.strip()
                        if cleaned:
                            self.text_parts.append(cleaned)

            extractor = TextExtractor()
            extractor.feed(html)
            return "\n".join(extractor.text_parts)[:3000]  # Limit output

        except Exception as e:
            print(f"⚠️  HTML extraction failed: {e}")
            # Fallback: simple regex
            import re
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)
            return text[:3000]

    def analyze(self, url: str, enable_scraping: bool = True) -> Dict[str, Any]:
        """
        Analyze a website and generate a comprehensive description.

        Args:
            url: Website URL to analyze
            enable_scraping: Whether to attempt web scraping (default: True)
                If False, uses URL-based analysis only

        Returns:
            Dictionary with website analysis
        """
        print(f"🔍 Analyzing website: {url}")

        # Parse URL
        parsed = urlparse(url)
        domain = parsed.netloc or url

        # ═══════════════════════════════════════════════════════════════════
        # STEP 1: Web Search for additional context
        # ═══════════════════════════════════════════════════════════════════
        web_search_context = ""
        web_search_results = {}
        
        if self.enable_web_search and self.web_search:
            print("🌐 Searching web for website information...")
            try:
                search_info = self.web_search.search_website_info(url)
                web_search_context = search_info.get("combined_context", "")
                web_search_results = search_info.get("search_results", {})
                print(f"   ✓ Found {search_info.get('num_results', 0)} search results")
            except Exception as e:
                print(f"   ⚠️ Web search failed: {e}")
                web_search_context = ""

        # ═══════════════════════════════════════════════════════════════════
        # STEP 2: Fetch website content (optional)
        # ═══════════════════════════════════════════════════════════════════
        html_content = ""
        scraping_enabled = enable_scraping

        if enable_scraping:
            html_content, scraping_success = self._fetch_website_content(url)
        else:
            print("ℹ️  Scraping disabled - using URL-based analysis only")
            scraping_success = False

        if not html_content or not scraping_success:
            print("ℹ️  Proceeding with URL-based analysis (no scraped content)")
            extracted_text = f"Domain: {domain}\nURL: {url}\nAnalysis type: URL-based"
        else:
            extracted_text = self._extract_text_from_html(html_content)

        # ═══════════════════════════════════════════════════════════════════
        # STEP 3: Build prompt with web search context
        # ═══════════════════════════════════════════════════════════════════
        web_context_section = ""
        if web_search_context:
            web_context_section = f"""
**Web Search Results (additional context):**
{web_search_context[:2000]}

---
"""

        # Build prompt for LLM analysis
        analysis_prompt = f"""
Analyze this website and generate a comprehensive description.

**Website URL:** {url}
**Domain:** {domain}

{web_context_section}
**Website Content (extracted):**
{extracted_text[:2000]}

---

Provide a detailed analysis in JSON format with the following structure:
{{
  "domain": "{domain}",
  "site_type": "e-commerce|blog|saas|social|news|other",
  "primary_purpose": "Brief description of main purpose",
  "target_audience": [
    {{
      "segment": "Segment name",
      "characteristics": "Who are they?",
      "motivation": "Why do they visit?"
    }}
  ],
  "key_features": [
    "Feature 1",
    "Feature 2",
    "Feature 3"
  ],
  "pricing_model": "free|freemium|paid|subscription|marketplace|other",
  "main_products_services": ["Product/Service 1", "Product/Service 2"],
  "user_journey": {{
    "entry_point": "How users first arrive",
    "key_steps": ["Step 1", "Step 2", "Step 3"],
    "conversion_goal": "What is the site trying to achieve?"
  }},
  "navigation_patterns": "Description of how users navigate",
  "content_organization": "How is content organized?",
  "competitive_advantages": ["Advantage 1", "Advantage 2"],
  "user_pain_points": ["Pain 1", "Pain 2"],
  "estimated_audience_size": "large|medium|small",
  "design_style": "minimalist|modern|corporate|creative|other"
}}

Be specific and use the website content to make informed decisions.
"""

        print("🤖 Calling LLM for analysis...")
        messages = [
            SystemMessage(
                content="You are a web analyst expert. Analyze websites and provide detailed, structured insights about their structure, target audience, and features. Always respond with valid JSON."
            ),
            HumanMessage(content=analysis_prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            response_text = response.content

            # Extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                analysis = json.loads(json_match.group(0))
            else:
                raise ValueError("No JSON found in LLM response")

            analysis["url"] = url
            analysis["scraping_enabled"] = scraping_enabled
            analysis["scraping_successful"] = scraping_success
            analysis["web_search_enabled"] = self.enable_web_search
            analysis["web_search_results_count"] = len(web_search_results) if web_search_results else 0
            analysis["analysis_type"] = "enriched" if web_search_context else ("content-based" if scraping_success else "url-based")
            return analysis

        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            return {
                "url": url,
                "domain": domain,
                "error": str(e),
                "scraping_enabled": scraping_enabled,
                "scraping_successful": False,
                "web_search_enabled": self.enable_web_search,
                "analysis_type": "url-based (error fallback)",
            }

    def save_analysis(self, analysis: Dict[str, Any], output_path: str) -> None:
        """Save analysis to JSON file."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"✅ Analysis saved to {output_path}")

    def print_analysis(self, analysis: Dict[str, Any]) -> None:
        """Print analysis in readable format."""
        print("\n" + "=" * 80)
        print(f"Website Analysis: {analysis.get('domain', 'Unknown')}")
        print("=" * 80)

        # Print key sections
        for key in [
            "site_type",
            "primary_purpose",
            "pricing_model",
            "key_features",
            "target_audience",
            "estimated_audience_size",
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
