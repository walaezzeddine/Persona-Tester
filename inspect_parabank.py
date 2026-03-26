"""
Inspect ParaBank page to find the correct login button selector
"""
import asyncio
from playwright.async_api import async_playwright

async def inspect_login_button():
    """Find the correct login button selector"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("https://parabank.parasoft.com/parabank/index.htm")
        
        print("\n" + "="*60)
        print("PARABANK BUTTON ANALYSIS")
        print("="*60)
        
        # Find all buttons
        buttons = await page.query_selector_all("button")
        print(f"\n[1] Found {len(buttons)} buttons on the page:")
        
        for i, btn in enumerate(buttons):
            btn_text = await btn.text_content()
            btn_type = await btn.get_attribute("type")
            btn_class = await btn.get_attribute("class")
            btn_id = await btn.get_attribute("id")
            btn_name = await btn.get_attribute("name")
            
            print(f"\n  Button {i+1}:")
            print(f"    Text: {btn_text.strip()}")
            print(f"    Type: {btn_type}")
            print(f"    Class: {btn_class}")
            print(f"    ID: {btn_id}")
            print(f"    Name: {btn_name}")
        
        # Try alternative selectors
        print("\n[2] Testing button selectors:")
        
        selectors = [
            'button:has-text("Log In")',
            'button:has-text("LOGIN")',
            'input[type="submit"]',
            'input[type="button"]',
            'button[value="Log In"]',
            'form button',
            '[onclick*="submit"]',
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    print(f"  ✓ Found: {selector} -> '{text.strip()}'")
            except:
                pass
        
        # Find form element
        print("\n[3] Form element analysis:")
        form = await page.query_selector("form")
        if form:
            print("  ✓ Form found")
            form_action = await form.get_attribute("action")
            form_method = await form.get_attribute("method")
            print(f"    - Action: {form_action}")
            print(f"    - Method: {form_method}")
            
            # Get all buttons in form
            form_buttons = await form.query_selector_all("button")
            print(f"    - Buttons in form: {len(form_buttons)}")
            for i, btn in enumerate(form_buttons):
                text = await btn.text_content()
                print(f"      [{i+1}] {text.strip()}")
        
        await browser.close()
        print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(inspect_login_button())
