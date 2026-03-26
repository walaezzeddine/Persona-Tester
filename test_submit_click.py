"""
Test if the submit button is actually clickable
"""
import asyncio
from playwright.async_api import async_playwright

async def test_submit_click():
    """Test if the submit input can be clicked"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            await page.goto("https://parabank.parasoft.com/parabank/index.htm")
            print("\n✓ Page loaded")
            
            # Fill credentials
            await page.fill('input[name="username"]', "john")
            await page.fill('input[name="password"]', "demo")
            print("✓ Credentials entered")
            
            # Try different ways to click the submit button
            print("\n[1] Trying input[type='submit'] selector...")
            submit_input = await page.query_selector('input[type="submit"]')
            if submit_input:
                submit_value = await submit_input.get_attribute("value")
                print(f"  ✓ Submit input found: '{submit_value}'")
                
                # Check if it's visible and enabled
                is_visible = await submit_input.is_visible()
                is_enabled = await submit_input.is_enabled()
                print(f"  - Visible: {is_visible}")
                print(f"  - Enabled: {is_enabled}")
                
                # Try to click it
                print("  - Attempting click...")
                await submit_input.click()
                
                # Wait for response
                print("  ⏳ Waiting for response...")
                await page.wait_for_load_state("networkidle", timeout=5000)
                
                print(f"✓ Response received!")
                print(f"  - URL: {page.url}")
                print(f"  - Title: {await page.title()}")
                
                # Check the result
                content = await page.content()
                if "Error" in content and "internal error" in content.lower():
                    print("\n❌ Result: Internal error page returned by server")
                    print("   -> ParaBank server issue, not a selector/button issue")
                elif "accounts" in page.url.lower() or "overview" in page.url.lower():
                    print("\n✅ Result: Successfully logged in!")
                else:
                    print("\n⚠️  Result: Unclear - could be logged in")
            else:
                print("  ❌ Submit input not found")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        finally:
            print("\nKeeping browser open for inspection...")
            await asyncio.sleep(3)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_submit_click())
