#!/usr/bin/env python3
"""
Quick test to find and click Register button using JavaScript directly
Then fill in registration form
"""
import asyncio
from playwright.async_api import async_playwright

async def test_registration_manual():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("📍 Step 1: Navigating to Wall Street Survivor homepage...")
        await page.goto("https://www.wallstreetsurvivor.com/")
        await page.wait_for_load_state("networkidle")
        print("✅ Homepage loaded\n")
        
        print("📍 Step 2: Finding Register button using JavaScript...")
        register_link = await page.evaluate("""
            () => {
                // Try to find the register link/button
                const links = document.querySelectorAll('a, li, button');
                for (let el of links) {
                    if (el.textContent?.toLowerCase().includes('register')) {
                        console.log('Found register element:', el.tagName, el.className);
                        console.log('Text:', el.textContent?.trim());
                        console.log('Href:', el.href || el.getAttribute('href'));
                        
                        // If it's a li, find the link inside
                        if (el.tagName === 'LI') {
                            const link = el.querySelector('a');
                            if (link) {
                                return link.href;
                            }
                        }
                        
                        // If it has an href, use it
                        if (el.href) {
                            return el.href;
                        }
                        
                        // If it's clickable, we'll click it
                        return 'FOUND_ELEMENT';
                    }
                }
                return null;
            }
        """)
        
        if register_link:
            print(f"✅ Register element found!")
            print(f"   Result: {register_link}\n")
            
            if register_link == 'FOUND_ELEMENT':
                print("📍 Step 3: Clicking Register button via JavaScript...")
                await page.evaluate("""
                    () => {
                        const links = document.querySelectorAll('a, li, button');
                        for (let el of links) {
                            if (el.textContent?.toLowerCase().includes('register')) {
                                console.log('Clicking:', el.textContent);
                                el.click();
                                return true;
                            }
                        }
                    }
                """)
                print("✅ Click executed!")
            else:
                print(f"📍 Step 3: Navigating to Register link...")
                await page.goto(register_link)
                print("✅ Navigated to register page!")
        else:
            print("❌ Register button not found!\n")
            print("Let me check the full page HTML for 'register' keyword...")
            
            # Check if "register" appears anywhere in the page
            has_register = await page.evaluate("""
                () => {
                    const html = document.documentElement.outerHTML.toLowerCase();
                    return html.includes('register');
                }
            """)
            
            if has_register:
                print("✅ Word 'register' found in HTML!")
                print("   Taking screenshot for manual inspection...")
                await page.screenshot(path="register_button_search.png")
                print("   Saved to: register_button_search.png")
            else:
                print("❌ 'register' keyword not found in page HTML!")
        
        print("\n📸 Taking final screenshot...")
        await page.screenshot(path="registration_page.png")
        print("✅ Screenshot saved to: registration_page.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_registration_manual())
