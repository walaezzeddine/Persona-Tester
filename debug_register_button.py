#!/usr/bin/env python3
"""
Debug script to find Register/Sign Up button on Wall Street Survivor
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_register_button():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("📍 Navigating to Wall Street Survivor homepage...")
        await page.goto("https://www.wallstreetsurvivor.com/")
        await page.wait_for_load_state("networkidle")
        
        print("\n" + "="*80)
        print("🔍 ANALYZING PAGE STRUCTURE")
        print("="*80)
        
        # Get page title
        title = await page.title()
        print(f"\n✓ Page Title: {title}")
        
        # Find all buttons and links
        print("\n📋 ALL BUTTONS ON PAGE:")
        buttons = await page.locator("button").all()
        for i, button in enumerate(buttons):
            text = await button.text_content()
            visible = await button.is_visible()
            print(f"   {i+1}. '{text.strip()}' - Visible: {visible}")
        
        print("\n📋 ALL LINKS ON PAGE:")
        links = await page.locator("a").all()
        visible_links = []
        for i, link in enumerate(links):
            text = await link.text_content()
            href = await link.get_attribute("href")
            visible = await link.is_visible()
            if visible and text and text.strip():
                visible_links.append((text.strip(), href))
                if i < 50:  # Show first 50
                    print(f"   {i+1}. '{text.strip()}' - href: {href}")
        
        print("\n🔎 SEARCHING FOR REGISTER/SIGNUP KEYWORDS:")
        # Search in page content
        page_content = await page.content()
        
        keywords = ["register", "signup", "sign up", "join", "create account"]
        for keyword in keywords:
            count = page_content.lower().count(keyword)
            if count > 0:
                print(f"   ✓ '{keyword}' found {count} times")
            else:
                print(f"   ✗ '{keyword}' NOT found")
        
        print("\n🔍 SEARCHING IN PAGE HTML:")
        # Find elements with register text
        register_elements = await page.evaluate("""
            () => {
                const elements = [];
                document.querySelectorAll('*').forEach(el => {
                    const text = el.textContent?.toLowerCase() || '';
                    const html = el.outerHTML?.toLowerCase() || '';
                    if (text.includes('register') || text.includes('sign up') || html.includes('signup')) {
                        elements.push({
                            tag: el.tagName,
                            text: el.textContent?.substring(0, 50),
                            visible: el.offsetParent !== null,
                            class: el.className,
                            id: el.id
                        });
                    }
                });
                return elements;
            }
        """)
        
        if register_elements:
            print("\n   Found elements with 'register'/'signup':")
            for el in register_elements[:10]:
                print(f"   - <{el['tag']}> visible={el['visible']} class='{el['class']}' id='{el['id']}'")
                print(f"     text: {el['text']}")
        else:
            print("   ✗ No elements found with 'register' or 'signup'")
        
        print("\n🔍 LOOKING FOR HEADER/NAV BUTTONS:")
        # Check header area
        nav_structure = await page.evaluate("""
            () => {
                const header = document.querySelector('header') || document.querySelector('nav') || document.querySelector('[role=banner]');
                if (!header) return 'No header/nav found';
                
                const buttons = header.querySelectorAll('button, a[class*=button], a[class*=btn]');
                return Array.from(buttons).map(b => ({
                    tag: b.tagName,
                    text: b.textContent?.trim(),
                    href: b.href,
                    class: b.className
                }));
            }
        """)
        
        print(f"   {nav_structure}")
        
        print("\n📸 Taking screenshot to see what's visible...")
        await page.screenshot(path="debug_homepage.png")
        print("   ✓ Screenshot saved to: debug_homepage.png")
        
        print("\n💡 POSSIBLE REASONS REGISTER NOT IN ACCESSIBILITY TREE:")
        print("   1. Button might be hidden with CSS (display: none)")
        print("   2. Button might be inside an iframe")
        print("   3. Button might be dynamically added via JavaScript")
        print("   4. Button might have aria-hidden=true")
        print("   5. Button might not exist on homepage (check /signup URL)")
        
        print("\n🎯 NEXT STEPS:")
        print("   1. Check debug_homepage.png to SEE the button visually")
        print("   2. If button exists but not in tree, check CSS")
        print("   3. If button doesn't exist, check /signup or /register URL")
        print("   4. Check if button appears after page interaction")
        
        await browser.close()
        print("\n✓ Debug complete!\n")

if __name__ == "__main__":
    asyncio.run(debug_register_button())
