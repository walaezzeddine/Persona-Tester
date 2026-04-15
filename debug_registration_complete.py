#!/usr/bin/env python3
"""
Debug script to extract ALL registration form fields from Wall Street Survivor
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Setup browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to registration
            print("📍 Navigating to registration page...")
            await page.goto("https://app.wallstreetsurvivor.com/members/register")
            await page.wait_for_load_state("networkidle")
            
            # Extract ALL form fields using JavaScript
            print("\n🔍 Extracting all form fields...")
            
            script = """
            () => {
                const fields = [];
                
                // Get all inputs
                document.querySelectorAll('input').forEach(input => {
                    fields.push({
                        type: 'input',
                        tag: input.tagName,
                        type_attr: input.type,
                        id: input.id || 'NO_ID',
                        name: input.name || 'NO_NAME',
                        placeholder: input.placeholder || '',
                        value: input.value,
                        required: input.required,
                        visible: input.offsetParent !== null
                    });
                });
                
                // Get all selects
                document.querySelectorAll('select').forEach(select => {
                    const options = Array.from(select.options).map(o => o.text);
                    fields.push({
                        type: 'select',
                        tag: select.tagName,
                        id: select.id || 'NO_ID',
                        name: select.name || 'NO_NAME',
                        options: options.slice(0, 5),
                        required: select.required,
                        visible: select.offsetParent !== null
                    });
                });
                
                // Get all textareas
                document.querySelectorAll('textarea').forEach(textarea => {
                    fields.push({
                        type: 'textarea',
                        id: textarea.id || 'NO_ID',
                        name: textarea.name || 'NO_NAME',
                        placeholder: textarea.placeholder || '',
                        required: textarea.required,
                        visible: textarea.offsetParent !== null
                    });
                });
                
                // Get all checkboxes and labels
                document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    fields.push({
                        type: 'checkbox',
                        id: cb.id || 'NO_ID',
                        name: cb.name || 'NO_NAME',
                        checked: cb.checked,
                        required: cb.required,
                        visible: cb.offsetParent !== null,
                        label: cb.labels ? cb.labels[0]?.textContent : ''
                    });
                });
                
                // Get all radio buttons
                document.querySelectorAll('input[type="radio"]').forEach(radio => {
                    fields.push({
                        type: 'radio',
                        id: radio.id || 'NO_ID',
                        name: radio.name || 'NO_NAME',
                        value: radio.value,
                        checked: radio.checked,
                        visible: radio.offsetParent !== null,
                        label: radio.labels ? radio.labels[0]?.textContent : ''
                    });
                });
                
                // Get all buttons
                document.querySelectorAll('button').forEach(btn => {
                    fields.push({
                        type: 'button',
                        id: btn.id || 'NO_ID',
                        name: btn.name || 'NO_NAME',
                        text: btn.textContent.trim().slice(0, 30),
                        visible: btn.offsetParent !== null
                    });
                });
                
                return fields;
            }
            """
            
            result = await page.evaluate(script)
            
            # Print organized results
            print("\n" + "="*80)
            print("REGISTRATION FORM FIELDS")
            print("="*80)
            
            inputs = [f for f in result if f['type'] == 'input']
            selects = [f for f in result if f['type'] == 'select']
            checkboxes = [f for f in result if f['type'] == 'checkbox']
            radios = [f for f in result if f['type'] == 'radio']
            buttons = [f for f in result if f['type'] == 'button']
            
            print(f"\n📝 TEXT INPUTS ({len(inputs)}):")
            for i, inp in enumerate(inputs):
                visibility = "✓ VISIBLE" if inp['visible'] else "✗ HIDDEN"
                required = "* REQUIRED" if inp['required'] else ""
                print(f"  {i+1}. ID: {inp['id']:<20} Name: {inp['name']:<20} Type: {inp['type_attr']:<15} {visibility} {required}")
                if inp['placeholder']:
                    print(f"     Placeholder: {inp['placeholder']}")
            
            print(f"\n📋 SELECT DROPDOWNS ({len(selects)}):")
            for i, sel in enumerate(selects):
                visibility = "✓ VISIBLE" if sel['visible'] else "✗ HIDDEN"
                required = "* REQUIRED" if sel['required'] else ""
                print(f"  {i+1}. ID: {sel['id']:<20} Name: {sel['name']:<20} {visibility} {required}")
                print(f"     Options: {sel['options']}")
            
            print(f"\n✓ CHECKBOXES ({len(checkboxes)}):")
            for i, cb in enumerate(checkboxes):
                visibility = "✓ VISIBLE" if cb['visible'] else "✗ HIDDEN"
                required = "* REQUIRED" if cb['required'] else ""
                print(f"  {i+1}. ID: {cb['id']:<20} Label: {cb['label']:<30} {visibility} {required}")
            
            print(f"\n◯ RADIO BUTTONS ({len(radios)}):")
            for i, radio in enumerate(radios):
                visibility = "✓ VISIBLE" if radio['visible'] else "✗ HIDDEN"
                print(f"  {i+1}. ID: {radio['id']:<20} Name: {radio['name']:<20} Label: {radio['label']:<30} {visibility}")
            
            print(f"\n🔘 BUTTONS ({len(buttons)}):")
            for i, btn in enumerate(buttons):
                visibility = "✓ VISIBLE" if btn['visible'] else "✗ HIDDEN"
                print(f"  {i+1}. ID: {btn['id']:<20} Text: {btn['text']:<30} {visibility}")
            
            print("\n" + "="*80)
            print(f"TOTAL FIELDS: {len(result)}")
            print("="*80)
            
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

