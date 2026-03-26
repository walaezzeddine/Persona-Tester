"""
Manual test for ParaBank login to diagnose the issue
"""
import asyncio
from playwright.async_api import async_playwright

async def test_parabank_login():
    """Test ParaBank login with john/demo credentials"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            print("\n" + "="*60)
            print("PARABANK LOGIN TEST - Manual Verification")
            print("="*60)
            
            # Step 1: Navigate to login page
            print("\n[1] Navigating to https://parabank.parasoft.com/")
            await page.goto("https://parabank.parasoft.com/parabank/index.htm")
            print(f"✓ Page loaded: {page.url}")
            print(f"✓ Title: {await page.title()}")
            
            # Take screenshot of login form
            print("\n[2] Checking login form...")
            username_field = await page.query_selector('input[name="username"]')
            password_field = await page.query_selector('input[name="password"]')
            login_button = await page.query_selector('button[type="submit"]')
            
            if username_field and password_field and login_button:
                print("✓ Login form found with all required fields")
            else:
                print("❌ Login form incomplete")
                print(f"  - Username field: {'✓' if username_field else '❌'}")
                print(f"  - Password field: {'✓' if password_field else '❌'}")
                print(f"  - Login button: {'✓' if login_button else '❌'}")
            
            # Step 2: Fill in credentials
            print("\n[3] Entering credentials...")
            await page.fill('input[name="username"]', "john")
            print("✓ Username 'john' entered")
            
            await page.fill('input[name="password"]', "demo")
            print("✓ Password 'demo' entered")
            
            # Step 3: Click login button
            print("\n[4] Clicking Login button...")
            await page.click('button[type="submit"]')
            print("⏳ Waiting for response...")
            
            # Wait for navigation or error
            await page.wait_for_load_state("networkidle", timeout=5000)
            
            print(f"✓ Response received: {page.url}")
            print(f"✓ Page title: {await page.title()}")
            
            # Check for error messages
            error_heading = await page.query_selector('h1')
            if error_heading:
                error_text = await error_heading.text_content()
                print(f"  Error heading: {error_text}")
            
            error_paragraphs = await page.query_selector_all('p')
            print(f"\n[5] Page content analysis:")
            if "Error" in await page.content():
                print("❌ Login failed - Error page detected")
                for i, p in enumerate(error_paragraphs[:5]):
                    text = await p.text_content()
                    if text.strip():
                        print(f"  - {text.strip()[:80]}")
            else:
                print("✓ No error page - checking for accounts/overview...")
                if "accounts" in page.url.lower() or "overview" in page.url.lower():
                    print("✅ SUCCESS - Logged in and redirected to accounts page!")
                else:
                    print("⚠️  Page loaded but not clear if login succeeded")
            
            # Get console errors
            print(f"\n[6] Console check:")
            # Try to get console messages if available
            try:
                content = await page.content()
                if "console" in content.lower():
                    print("  - Page has console errors visible")
            except:
                pass
            
            # Take final screenshot
            await page.screenshot(path="parabank_login_test.png")
            print("\n✓ Screenshot saved: parabank_login_test.png")
            
            # Keep browser open for 5 seconds for inspection
            print("\n⏳ Keeping browser open for 5 seconds for manual inspection...")
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()
            print("\n" + "="*60)
            print("TEST COMPLETE")
            print("="*60)

if __name__ == "__main__":
    asyncio.run(test_parabank_login())
