#!/usr/bin/env python3
"""Debug script to examine login form structure"""
import asyncio
from playwright.async_api import async_playwright

async def inspect_login_form():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("=" * 80)
        print("🔍 INSPECTING LOGIN FORM STRUCTURE")
        print("=" * 80)
        
        print("\n📍 Navigating to login page...")
        await page.goto("https://app.wallstreetsurvivor.com/login", wait_until="networkidle")
        print("✅ Page loaded\n")
        
        # Get all form inputs
        print("📋 LOGIN FORM FIELDS DETECTED:")
        all_inputs = await page.query_selector_all("input")
        for i, input_el in enumerate(all_inputs):
            input_type = await input_el.get_attribute("type")
            input_name = await input_el.get_attribute("name")
            input_id = await input_el.get_attribute("id")
            input_placeholder = await input_el.get_attribute("placeholder")
            
            print(f"\n  Field {i+1}:")
            print(f"    Type: {input_type}")
            print(f"    Name: {input_name}")
            print(f"    ID: {input_id}")
            print(f"    Placeholder: {input_placeholder}")
        
        # Get all buttons
        print("\n\n🔘 BUTTONS DETECTED:")
        all_buttons = await page.query_selector_all("button")
        for i, button in enumerate(all_buttons):
            button_text = await button.text_content()
            button_type = await button.get_attribute("type")
            button_id = await button.get_attribute("id")
            print(f"  Button {i+1}: '{button_text.strip()}' (type: {button_type}, id: {button_id})")
        
        # Take screenshot
        await page.screenshot(path="debug_login_form.png")
        print("\n\n📸 Screenshot saved to: debug_login_form.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_login_form())
