#!/usr/bin/env python3
"""Debug script to examine registration form structure"""
import asyncio
from playwright.async_api import async_playwright

async def inspect_registration_form():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("=" * 80)
        print("🔍 INSPECTING REGISTRATION FORM STRUCTURE")
        print("=" * 80)
        
        print("\n📍 Navigating to registration page...")
        await page.goto("https://app.wallstreetsurvivor.com/members/register", wait_until="networkidle")
        print("✅ Page loaded\n")
        
        # Get all form inputs
        print("📋 FORM FIELDS DETECTED:")
        all_inputs = await page.query_selector_all("input")
        for i, input_el in enumerate(all_inputs):
            input_type = await input_el.get_attribute("type")
            input_name = await input_el.get_attribute("name")
            input_id = await input_el.get_attribute("id")
            input_placeholder = await input_el.get_attribute("placeholder")
            label = await page.evaluate(f"""
                (selector) => {{
                    const el = document.evaluate(selector, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (!el) return null;
                    // Find associated label
                    if (el.id) {{
                        const label = document.querySelector(`label[for="${{el.id}}"]`);
                        if (label) return label.textContent.trim();
                    }}
                    // Check parent label
                    const parentLabel = el.closest('label');
                    if (parentLabel) return parentLabel.textContent.trim();
                    return null;
                }}
            """, f"//input[{i+1}]")
            
            print(f"\n  Field {i+1}:")
            print(f"    Type: {input_type}")
            print(f"    Name: {input_name}")
            print(f"    ID: {input_id}")
            print(f"    Placeholder: {input_placeholder}")
            print(f"    Label: {label}")
        
        # Get all buttons
        print("\n\n🔘 BUTTONS DETECTED:")
        all_buttons = await page.query_selector_all("button")
        for i, button in enumerate(all_buttons):
            button_text = await button.text_content()
            button_type = await button.get_attribute("type")
            print(f"  Button {i+1}: {button_text.strip()} (type: {button_type})")
        
        # Check for checkboxes specifically
        print("\n\n☑️ CHECKBOXES:")
        checkboxes = await page.query_selector_all("input[type='checkbox']")
        if checkboxes:
            for i, cb in enumerate(checkboxes):
                cb_label = await page.evaluate(f"""
                    (selector) => {{
                        const el = document.evaluate(selector, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                        const label = el.closest('label') || document.querySelector(`label[for="${{el.id}}"]`);
                        return label ? label.textContent.trim() : el.name;
                    }}
                """, f"//input[@type='checkbox'][{i+1}]")
                print(f"  Checkbox {i+1}: {cb_label}")
        else:
            print("  ❌ No checkboxes found")
        
        # Take screenshot
        await page.screenshot(path="debug_registration_form.png")
        print("\n\n📸 Screenshot saved to: debug_registration_form.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_registration_form())
