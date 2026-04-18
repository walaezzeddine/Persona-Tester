#!/usr/bin/env python3
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


@dataclass
class SectionResult:
    name: str
    clicked: bool
    snippet: str


def first_visible(page, selectors: List[str], timeout_ms: int = 4000):
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            loc.wait_for(state="visible", timeout=timeout_ms)
            return loc
        except PlaywrightTimeoutError:
            continue
    return None


def safe_click(page, selectors: List[str], timeout_ms: int = 4000) -> bool:
    loc = first_visible(page, selectors, timeout_ms=timeout_ms)
    if not loc:
        return False
    try:
        loc.click(timeout=timeout_ms)
        return True
    except Exception:
        try:
            loc.click(timeout=timeout_ms, force=True)
            return True
        except Exception:
            return False


def safe_click_any(page, selectors: List[str], timeout_ms: int = 3000) -> bool:
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if loc.count() == 0:
                continue
            try:
                loc.scroll_into_view_if_needed(timeout=1000)
            except Exception:
                pass
            loc.click(timeout=timeout_ms, force=True)
            return True
        except Exception:
            continue
    return False


def click_by_text_variants(page, variants: List[str]) -> bool:
    script = r"""
        (variants) => {
            const norm = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
            const all = Array.from(document.querySelectorAll('a,button,[role="tab"],li,span,div'));
            for (const v of variants) {
                const target = norm(v);
                for (const el of all) {
                    const t = norm(el.innerText || el.textContent || '');
                    if (!t) continue;
                    if (t === target || t.includes(target)) {
                        const clickable = el.closest('a,button,[role="tab"]') || el;
                        clickable.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                        return true;
                    }
                }
            }
            return false;
        }
        """
    try:
        return bool(page.evaluate(script, variants))
    except Exception:
        return False


def find_section_href(page, variants: List[str]) -> Optional[str]:
    script = r"""
        (variants) => {
            const norm = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
            const links = Array.from(document.querySelectorAll('a[href]'));
            for (const v of variants) {
                const target = norm(v);
                for (const a of links) {
                    const text = norm(a.innerText || a.textContent || '');
                    const href = a.getAttribute('href') || '';
                    if ((text && (text === target || text.includes(target))) || href.toLowerCase().includes(target.replace(' ', ''))) {
                        return a.href || href;
                    }
                }
            }
            return null;
        }
        """
    try:
        href = page.evaluate(script, variants)
        if href and isinstance(href, str):
            return href
    except Exception:
        pass
    return None


def on_msft_quote_page(page) -> bool:
    url = page.url.lower()
    if "app.wallstreetsurvivor.com/quotes/quotes" not in url:
        return False
    return "symbol=msft" in url


def ensure_msft_quote_page(page) -> None:
    if not on_msft_quote_page(page):
        page.goto(
            "https://app.wallstreetsurvivor.com/quotes/quotes?type=fullnewssummary&symbol=MSFT&exchange=US",
            wait_until="domcontentloaded",
        )
        page.wait_for_timeout(1200)


def dismiss_overlays(page) -> None:
    # Close generic overlays/modals that block pointer events.
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass

    close_selectors = [
        "button:has-text('Close')",
        "button:has-text('OK')",
        "button:has-text('Got it')",
        "button[aria-label='Close']",
        ".modal button.close",
        "text=X",
    ]
    for sel in close_selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=800):
                loc.click(timeout=800, force=True)
        except Exception:
            continue


def capture_section_snippet(page, max_len: int = 1200) -> str:
    text = page.locator("body").inner_text(timeout=5000)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def score_buy_decision(section_snippets: Dict[str, str]) -> Dict[str, str]:
    text = "\n".join(section_snippets.values()).lower()

    buy_signals = 0
    no_buy_signals = 0

    if re.search(r"\bbuy\b|strong buy|outperform|overweight", text):
        buy_signals += 2
    if re.search(r"\bsell\b|underperform|underweight|downgrade", text):
        no_buy_signals += 2

    if re.search(r"revenue\s+(up|growth|increased)|eps\s+(beat|up)", text):
        buy_signals += 1
    if re.search(r"revenue\s+(down|decline|decreased)|eps\s+(miss|down)", text):
        no_buy_signals += 1

    if re.search(r"52[- ]week\s+(high|uptrend|bullish)|price\s+(up|rally)", text):
        buy_signals += 1
    if re.search(r"52[- ]week\s+low|downtrend|bearish|price\s+(down|drop)", text):
        no_buy_signals += 1

    decision = "BUY" if buy_signals >= no_buy_signals else "DO NOT BUY"
    reasoning = (
        f"Signals BUY={buy_signals}, DO_NOT_BUY={no_buy_signals}. "
        "Decision based on analyst tone, trend language, and financial keywords found across sections."
    )

    return {"decision": decision, "reasoning": reasoning}


def run_test() -> None:
    out_json = Path("test_microsoft_deterministic_results.json")
    out_txt = Path("test_microsoft_deterministic_output.txt")

    logs: List[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_default_timeout(15000)

        logs.append("1) Navigate to WallStreetSurvivor homepage")
        page.goto("https://www.wallstreetsurvivor.com/", wait_until="domcontentloaded")

        logs.append("2) Click Login")
        safe_click(
            page,
            [
                "a:has-text('Login')",
                "text=Login",
                "a[href*='login']",
            ],
        )

        # If click did not navigate, go directly to login.
        if "login" not in page.url.lower():
            page.goto("https://app.wallstreetsurvivor.com/login", wait_until="domcontentloaded")

        logs.append("3) Fill credentials and submit")
        dismiss_overlays(page)
        user = first_visible(page, ["input[name='username']", "input[placeholder*='Username']", "input[type='text']"])
        pwd = first_visible(page, ["input[type='password']", "input[name*='pass']"])
        if user:
            user.fill("WALAEZZEDINE")
        if pwd:
            pwd.fill("WALA@123")
        safe_click(page, ["button:has-text('Log me in')", "button:has-text('Login')", "text=Log me in"])
        page.wait_for_timeout(2500)

        logs.append("4) Go to Stock Game -> Stocks")
        dismiss_overlays(page)
        # Prefer UI path first.
        safe_click(page, ["text=Stock Game", "a:has-text('Stock Game')", "button:has-text('Stock Game')"], timeout_ms=3000)
        if not safe_click(page, ["text=Stocks", "a:has-text('Stocks')"], timeout_ms=3000):
            page.goto("https://app.wallstreetsurvivor.com/trading/equities", wait_until="domcontentloaded")

        logs.append("5) Search for MSFT in top symbol input")
        dismiss_overlays(page)
        symbol_input = first_visible(
            page,
            [
                "input[placeholder*='Search for symbol']",
                "input[aria-label*='Search for symbol']",
                "input[placeholder*='Ticker']",
                "input:near(:text('Symbol'))",
                "input[type='text']",
            ],
            timeout_ms=5000,
        )
        if symbol_input:
            try:
                symbol_input.click(timeout=3000)
            except Exception:
                dismiss_overlays(page)
                symbol_input.click(timeout=3000, force=True)
            symbol_input.fill("MSFT")
            page.keyboard.press("Enter")
        safe_click(page, ["button:has-text('Preview')", "text=Preview"], timeout_ms=2000)
        page.wait_for_timeout(1800)

        # Fallback to direct MSFT quote page if still stuck.
        ensure_msft_quote_page(page)

        logs.append("6) Click each Microsoft section and collect data")
        sections_to_try = [
            ("Company Profile", ["Company Profile"], ["text=Company Profile", "a:has-text('Company Profile')", "button:has-text('Company Profile')", "[role='tab']:has-text('Company Profile')"]),
            ("Company News", ["Company News", "News and Media"], ["text=Company News", "a:has-text('Company News')", "button:has-text('Company News')", "text=News"]),
            ("Analyst Rating", ["Analyst Ratings", "Analyst Rating"], ["text=Analyst Ratings", "text=Analyst Rating", "a:has-text('Analyst')", "button:has-text('Analyst')"]),
            ("Price History", ["Price History"], ["text=Price History", "a:has-text('Price History')", "button:has-text('Price History')", "text=Chart"]),
            ("Financial Statements", ["Financial Statements"], ["text=Financial Statements", "a:has-text('Financial Statements')", "button:has-text('Financial Statements')", "text=Financial"]),
        ]

        section_results: List[SectionResult] = []
        snippets: Dict[str, str] = {}

        for section_name, variants, selectors in sections_to_try:
            ensure_msft_quote_page(page)
            dismiss_overlays(page)
            clicked = safe_click(page, selectors, timeout_ms=3500)
            if not clicked:
                clicked = safe_click_any(page, selectors, timeout_ms=3000)
            if not clicked:
                clicked = click_by_text_variants(page, variants)
            if not clicked:
                href = find_section_href(page, variants)
                if href:
                    try:
                        page.goto(href, wait_until="domcontentloaded")
                        clicked = True
                    except Exception:
                        clicked = False
            page.wait_for_timeout(1200)
            # Guardrail: section attempt is only valid if we remain in MSFT quote context.
            if clicked and not on_msft_quote_page(page):
                clicked = False
                ensure_msft_quote_page(page)
            snippet = capture_section_snippet(page)
            section_results.append(SectionResult(name=section_name, clicked=clicked, snippet=snippet))
            snippets[section_name] = snippet

        logs.append("7) Compute BUY/DO NOT BUY decision")
        decision_info = score_buy_decision(snippets)

        result = {
            "scenario": "Microsoft Stock - Detailed Company Analysis (Deterministic)",
            "url": page.url,
            "sections": [
                {"name": s.name, "clicked": s.clicked, "snippet": s.snippet}
                for s in section_results
            ],
            "decision": decision_info,
            "logs": logs,
        }

        out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        lines = []
        lines.append("MICROSOFT DETERMINISTIC TEST")
        lines.append("=" * 80)
        for item in logs:
            lines.append(item)
        lines.append("-" * 80)
        for s in section_results:
            lines.append(f"{s.name}: {'CLICKED' if s.clicked else 'NOT CONFIRMED'}")
        lines.append("-" * 80)
        lines.append(f"Decision: {decision_info['decision']}")
        lines.append(f"Reasoning: {decision_info['reasoning']}")
        out_txt.write_text("\n".join(lines), encoding="utf-8")

        browser.close()


if __name__ == "__main__":
    run_test()
