"""
Website Context Agent - LLM-powered website understanding
Uses web search to gather context, then LLM to synthesize a description.

Input: Website URL
Output: Structured website analysis (same schema as WebsiteAnalyzer for compatibility)
"""

import os
import json
import re
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..tools.web_search_tool import WebSearchTool


class WebsiteContextAgent:
    """
    Agent that understands websites using web search + LLM synthesis.
    
    Flow:
    1. Web search tool gathers information about the website
    2. LLM synthesizes a comprehensive description
    3. Output matches WebsiteAnalyzer schema for compatibility
    """

    def __init__(self, provider: str = "groq", model: str = None, temperature: float = 0.3):
        """
        Initialize the Website Context Agent.

        Args:
            provider: LLM provider ('openai', 'groq', 'github', 'google')
            model: Model name (defaults based on provider)
            temperature: LLM temperature (lower = more factual)
        """
        self.provider = provider
        self.temperature = temperature
        self.llm = self._init_llm(provider, model)
        self.search_tool = WebSearchTool(max_results=5)

    def _init_llm(self, provider: str, model: str = None) -> ChatOpenAI:
        """Initialize LLM based on provider - matches existing project pattern."""
        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
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

    def analyze(self, url: str) -> Dict[str, Any]:
        """
        Analyze a website using web search and LLM synthesis.

        Args:
            url: Website URL to analyze

        Returns:
            Structured website analysis (compatible with WebsiteAnalyzer output)
        """
        print(f"\n🌐 Analyzing website: {url}")
        print("=" * 60)

        # Step 1: Gather context via web search
        print("\n📡 Step 1: Gathering web search context...")
        search_info = self.search_tool.search_website_info(url)

        if search_info["num_results"] == 0:
            print("⚠️ No search results found. Using URL-only analysis.")
            search_context = f"No external information found. Analyze based on URL: {url}"
        else:
            print(f"✓ Found {search_info['num_results']} search results")
            search_context = search_info["combined_context"]

        # Step 2: LLM synthesizes description
        print("\n🧠 Step 2: LLM synthesizing website description...")
        analysis = self._synthesize_description(url, search_info["domain"], search_context)

        print(f"\n✅ Analysis complete for: {analysis.get('domain', url)}")
        return analysis

    def _synthesize_description(
        self, url: str, domain: str, search_context: str
    ) -> Dict[str, Any]:
        """
        Use LLM to synthesize a structured website description.

        Args:
            url: Website URL
            domain: Extracted domain
            search_context: Combined search results text

        Returns:
            Structured analysis dict
        """
        synthesis_prompt = f"""
Based on the following web search results about a website, create a comprehensive website analysis.

## Website Information
- **URL**: {url}
- **Domain**: {domain}

## Search Results Context
{search_context[:3000]}

---

## Task
Synthesize this information into a structured JSON analysis.

**CRITICAL**: Focus on the website's FUNCTIONALITY - what END USERS actually DO on this website.
- If it's a banking site, the users are CUSTOMERS who transfer money, pay bills, check accounts
- If it's e-commerce, the users are SHOPPERS who browse, compare, buy products
- If it's a demo/test site that simulates a real service, treat it AS THAT SERVICE (banking, shopping, etc.)
- Do NOT generate personas for developers/testers unless the site is actually a developer tool

Include:

1. **domain**: The website domain
2. **url**: Full URL
3. **site_type**: One of: "e-commerce", "banking", "social", "news", "saas", "demo", "education", "other"
4. **primary_purpose**: What END USERS use this website for (1-2 sentences)
5. **description**: Detailed description of the website's FUNCTIONALITY (2-3 sentences)
6. **target_audience**: List of END USER segments (customers, shoppers, account holders - NOT developers):
   [
     {{"segment": "name", "characteristics": ["trait1", "trait2"], "goals": ["goal1"]}},
     ...
   ]
7. **key_features**: List of main features END USERS interact with
8. **user_actions**: Common actions END USERS perform (login, transfer, buy, browse, etc.)
9. **pricing_model**: "free", "freemium", "paid", "demo", or "unknown"
10. **industry**: Industry/vertical the site belongs to

## Output Format
Return ONLY valid JSON (no markdown, no explanation):

{{
  "domain": "example.com",
  "url": "https://example.com",
  "site_type": "e-commerce",
  "primary_purpose": "...",
  "description": "...",
  "target_audience": [...],
  "key_features": [...],
  "user_actions": [...],
  "pricing_model": "...",
  "industry": "..."
}}
"""

        messages = [
            SystemMessage(content="""You are a web analyst expert. Analyze websites and provide structured descriptions.

IMPORTANT: Focus on END USER functionality. If a website simulates a service (like a demo banking site), 
analyze it AS THAT SERVICE - the target audience should be the simulated users (bank customers), 
not the people who built or test it (developers).

Always respond with valid JSON only. Be factual and base analysis on the provided search context.
If information is uncertain, make reasonable inferences based on the website's apparent functionality."""),
            HumanMessage(content=synthesis_prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            response_text = response.content

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                analysis = json.loads(json_match.group(0))
            else:
                raise ValueError("No JSON found in LLM response")

            # Ensure required fields
            analysis["domain"] = analysis.get("domain", domain)
            analysis["url"] = analysis.get("url", url)

            return analysis

        except Exception as e:
            print(f"❌ LLM synthesis failed: {e}")
            # Return minimal fallback
            return {
                "domain": domain,
                "url": url,
                "site_type": "other",
                "primary_purpose": f"Website at {domain}",
                "description": f"A website located at {url}. Unable to determine detailed information.",
                "target_audience": [{"segment": "general", "characteristics": [], "goals": []}],
                "key_features": [],
                "user_actions": ["browse", "navigate"],
                "pricing_model": "unknown",
                "industry": "unknown",
            }


def analyze_website(url: str, provider: str = "groq") -> Dict[str, Any]:
    """
    Convenience function to analyze a website.

    Args:
        url: Website URL
        provider: LLM provider

    Returns:
        Website analysis dict
    """
    agent = WebsiteContextAgent(provider=provider)
    return agent.analyze(url)


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("Website Context Agent - Test")
    print("=" * 60)

    # Test with ParaBank (demo banking site)
    agent = WebsiteContextAgent(provider="groq")
    analysis = agent.analyze("https://parabank.parasoft.com")

    print("\n📊 Analysis Result:")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))
