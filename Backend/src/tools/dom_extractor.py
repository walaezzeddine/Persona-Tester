"""
DOM Extractor Module
Extracts structured content from web pages for LLM consumption.
"""

from typing import Dict, List, Any


async def extract_page_content(page, content_limit: int = 1500) -> Dict[str, Any]:
   
    
    try:
        # Get basic page info
        url = page.url
        title = await page.title()
        
        # Extract clickable elements (buttons, links)
        clickables = await _extract_clickables(page)
        
        # Extract form inputs
        inputs = await _extract_inputs(page)
        
        # Extract main text content
        text_content = await _extract_text_content(page, content_limit)
        
        # Extract any visible error messages
        errors = await _extract_errors(page)
        
        # Extract product info if present
        products = await _extract_products(page)
        
        # Extract scroll position
        scroll_position = await _extract_scroll_position(page)
        
        # Extract navigation state (back/forward availability)
        nav_state = await _extract_nav_state(page)
        
        # Extract current category
        category = await _extract_category(page)
        
        # Extract visible modal/popup content (e.g. cart confirmation)
        modal = await _extract_modal(page)
        
        return {
            "url": url,
            "title": title,
            "clickables": clickables,
            "inputs": inputs,
            "text_content": text_content,
            "errors": errors,
            "products": products,
            "scroll_position": scroll_position,
            "nav_state": nav_state,
            "category": category,
            "modal": modal
        }
        
    except Exception as e:
        # Fallback to simple extraction
        return {
            "url": page.url,
            "title": "",
            "text_content": await page.inner_text("body")[:content_limit] if await page.inner_text("body") else "",
            "error": str(e)
        }


async def _extract_clickables(page, limit: int = 20) -> List[Dict[str, str]]:
    """Extract visible buttons and links."""
    clickables = []
    
    try:
        # Extract buttons
        buttons = await page.query_selector_all("button:visible, [role='button']:visible")
        for btn in buttons[:limit // 2]:
            text = await btn.inner_text()
            if text and text.strip():
                clickables.append({
                    "type": "button",
                    "text": text.strip()[:50]
                })
        
        # Extract important links
        links = await page.query_selector_all("a:visible")
        for link in links[:limit // 2]:
            text = await link.inner_text()
            href = await link.get_attribute("href")
            if text and text.strip() and href:
                clickables.append({
                    "type": "link",
                    "text": text.strip()[:50],
                    "href": href[:100] if href else ""
                })
    except:
        pass
    
    return clickables[:limit]


async def _extract_inputs(page, limit: int = 10) -> List[Dict[str, str]]:
    """Extract form inputs."""
    inputs = []
    
    try:
        input_elements = await page.query_selector_all("input:visible, textarea:visible, select:visible")
        for inp in input_elements[:limit]:
            input_type = await inp.get_attribute("type") or "text"
            name = await inp.get_attribute("name") or ""
            placeholder = await inp.get_attribute("placeholder") or ""
            
            inputs.append({
                "type": input_type,
                "name": name,
                "placeholder": placeholder
            })
    except:
        pass
    
    return inputs


async def _extract_text_content(page, limit: int = 1500) -> str:
    """Extract main text content."""
    try:
        # Try to get main content areas first
        selectors = ["main", "article", "#content", ".content", "[role='main']", "body"]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and len(text.strip()) > 100:
                        # Clean up whitespace
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        cleaned = '\n'.join(lines)
                        return cleaned[:limit]
            except:
                continue
        
        # Fallback to body
        text = await page.inner_text("body")
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned = '\n'.join(lines)
        return cleaned[:limit]
        
    except:
        return ""


async def _extract_errors(page) -> List[str]:
    """Extract visible error messages."""
    errors = []
    
    try:
        # Common error selectors
        error_selectors = [
            ".error", ".error-message", "[role='alert']",
            ".alert-danger", ".alert-error", ".notification-error",
            "#error", ".form-error", ".validation-error"
        ]
        
        for selector in error_selectors:
            try:
                elements = await page.query_selector_all(f"{selector}:visible")
                for el in elements:
                    text = await el.inner_text()
                    if text and text.strip():
                        errors.append(text.strip()[:200])
            except:
                continue
    except:
        pass
    
    return errors[:5]


async def _extract_products(page, limit: int = 50) -> List[Dict[str, str]]:
    """Extract product information and tag each Add-to-cart button with a unique id."""
    products = []
    
    try:
        # Common product container selectors (order matters: most specific first)
        product_selectors = [
            ".product-image-wrapper",
            ".single-products",
            ".features_items .col-sm-4",
            ".product", ".product-card", ".product-item",
            "[data-product]", ".item", ".card"
        ]

        for selector in product_selectors:
            try:
                elements = await page.query_selector_all(f"{selector}:visible")
                if elements:
                    idx = 0
                    for el in elements[:limit]:
                        # Try to get name from <p> inside .productinfo, then fallback to first line
                        name = ""
                        price = ""
                        try:
                            name_el = await el.query_selector(".productinfo p, .product-name, h4, h5")
                            if name_el:
                                name = (await name_el.inner_text()).strip()[:100]
                            price_el = await el.query_selector(".productinfo h2, .product-price, .price")
                            if price_el:
                                price = (await price_el.inner_text()).strip()[:50]
                        except:
                            pass

                        # Fallback: parse inner_text lines
                        if not name:
                            text = await el.inner_text()
                            if text:
                                lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
                                for line in lines:
                                    if not any(c in line for c in ["$", "\u20ac", "TND", "DT", "Rs"]) and len(line) > 2:
                                        name = line[:100]
                                        break
                        if not price:
                            text = await el.inner_text()
                            if text:
                                for line in text.strip().split("\n"):
                                    if any(c in line for c in ["$", "\u20ac", "TND", "DT", "Rs"]):
                                        price = line.strip()[:50]
                                        break

                        if name:
                            idx += 1
                            btn_id = f"add-to-cart-{idx}"
                            # Extract detail link (View Product / product details)
                            detail_link = ""
                            try:
                                detail_el = await el.query_selector(
                                    "a[href*='product_details'], a:has-text('View Product')"
                                )
                                if detail_el:
                                    href = await detail_el.get_attribute("href")
                                    if href:
                                        detail_link = href if href.startswith("/") else f"/{href}"
                            except:
                                pass
                            # Tag the first "Add to cart" style button inside this product
                            btn = await el.query_selector(
                                "a.add-to-cart, a[data-product-id], "
                                "button.add-to-cart, [class*='add-to-cart'], "
                                "button, a.btn, "
                                "a[href*='add_to_cart'], input[type='submit']"
                            )
                            if btn:
                                await btn.evaluate(
                                    '(el, id) => el.setAttribute("data-btn-id", id)',
                                    btn_id
                                )
                            products.append({
                                "name": name,
                                "price": price,
                                "btn_id": btn_id,
                                "detail": detail_link
                            })
                    if products:
                        break
            except:
                continue
    except:
        pass

    return products[:limit]


async def _extract_scroll_position(page) -> str:
    """Determine current scroll position: top, middle, or bottom."""
    try:
        position = await page.evaluate("""
            () => {
                const scrollTop = window.scrollY || document.documentElement.scrollTop;
                const scrollHeight = document.documentElement.scrollHeight;
                const clientHeight = document.documentElement.clientHeight;
                if (scrollHeight <= clientHeight) return 'top';
                const ratio = scrollTop / (scrollHeight - clientHeight);
                if (ratio < 0.15) return 'top';
                if (ratio > 0.85) return 'bottom';
                return 'middle';
            }
        """)
        return position
    except:
        return "unknown"


async def _extract_nav_state(page) -> Dict[str, bool]:
    """Check if browser back/forward navigation is available."""
    try:
        can_go_back = await page.evaluate("() => window.history.length > 1")
        return {
            "back_available": bool(can_go_back),
            "forward_available": False  # conservative default
        }
    except:
        return {"back_available": False, "forward_available": False}


async def _extract_modal(page) -> str:
    """Detect visible modal/popup overlays and return their text content.

    This is critical for sites like automationexercise.com where
    clicking 'Add to cart' opens a Bootstrap modal confirmation
    (e.g. 'Your product has been added to cart!  Continue Shopping | View Cart').

    Also checks for feedback stored by execute_action (page._cart_feedback)
    after auto-dismissing the modal, so the agent still gets confirmation
    even if the modal was already closed.
    """
    # 1) Check stored feedback from execute_action (modal already dismissed)
    try:
        feedback = getattr(page, '_cart_feedback', None)
        if feedback:
            # Clear it so we don't report it twice
            page._cart_feedback = None
            return feedback
    except:
        pass

    # 2) Check for a currently-visible modal
    try:
        modal_text = await page.evaluate("""
            () => {
                // automationexercise.com specific: #cartModal
                const cartModal = document.querySelector('#cartModal');
                if (cartModal) {
                    const style = window.getComputedStyle(cartModal);
                    if (style.display !== 'none' && cartModal.classList.contains('show') || cartModal.style.display === 'block') {
                        const body = cartModal.querySelector('.modal-body') || cartModal;
                        return body.innerText.trim();
                    }
                }
                // Generic Bootstrap modal
                const modal = document.querySelector('.modal.show, .modal.in, .modal[style*="display: block"]');
                if (modal) {
                    const body = modal.querySelector('.modal-body') || modal;
                    return body.innerText.trim();
                }
                return '';
            }
        """)
        return modal_text if modal_text else ""
    except:
        return ""


async def _extract_category(page) -> str:
    """Extract current category from breadcrumb or active sidebar link."""
    try:
        # Try breadcrumb first
        breadcrumb_sels = [
            ".breadcrumb", ".breadcrumbs", "[aria-label='breadcrumb']",
            ".panel-group .panel-title a.active",
            ".left-sidebar .panel-body a[style*='color']"
        ]
        for sel in breadcrumb_sels:
            try:
                el = await page.query_selector(sel)
                if el:
                    text = (await el.inner_text()).strip()
                    if text and len(text) < 100:
                        return text
            except:
                continue

        # Try active category in sidebar
        try:
            active_cats = await page.query_selector_all(".panel-body ul li a")
            for a in active_cats:
                style = await a.get_attribute("style") or ""
                if "color" in style or "bold" in style:
                    parent_panel = await a.evaluate(
                        '(el) => el.closest(".panel")?.querySelector(".panel-title a")?.textContent || ""'
                    )
                    cat_text = (await a.inner_text()).strip()
                    if parent_panel and cat_text:
                        return f"{parent_panel.strip()} > {cat_text}"
        except:
            pass

        # Fallback: check page title for category hints
        title = await page.title()
        if title:
            for keyword in ["Tops", "Dress", "Saree", "Tshirt", "Jeans", "Men", "Women", "Kids"]:
                if keyword.lower() in title.lower():
                    return keyword

        return ""
    except:
        return ""


def format_for_llm(extracted: Dict[str, Any]) -> str:
    """
    Format extracted page content for LLM consumption.
    
    Format exact demandé:
    CLICKABLES: Products | Cart | Login | Search
    INPUTS: search_input (placeholder: Search Products)
    PRODUCTS: Blue Top - 500 TND | Men Tshirt - 400 TND
    ERRORS: aucune
    
    Args:
        extracted: Dictionary from extract_page_content()
        
    Returns:
        Formatted string for LLM prompt
    """
    parts = []
    
    # URL and title
    parts.append(f"URL: {extracted.get('url', 'Unknown')}")
    if extracted.get('title'):
        parts.append(f"Page Title: {extracted['title']}")
    
    # NAVIGATION state
    nav = extracted.get('nav_state', {})
    back = nav.get('back_available', False)
    forward = nav.get('forward_available', False)
    parts.append(f"\nNAVIGATION: back_available={back} | forward_available={forward}")

    # SCROLL position
    scroll_pos = extracted.get('scroll_position', 'unknown')
    parts.append(f"SCROLL: position={scroll_pos}")

    # CURRENT_CATEGORY
    category = extracted.get('category', '')
    if category:
        parts.append(f"CURRENT_CATEGORY: {category}")
    
    # CLICKABLES - format: Products | Cart | Login
    if extracted.get('clickables'):
        clickable_texts = [item['text'] for item in extracted['clickables'][:15] if item.get('text')]
        parts.append(f"\nCLICKABLES: {' | '.join(clickable_texts)}")
    else:
        parts.append("\nCLICKABLES: aucun")
    
    # INPUTS - format: search_input (placeholder: Search Products)
    if extracted.get('inputs'):
        input_descs = []
        for inp in extracted['inputs'][:5]:
            name = inp.get('name', inp.get('type', 'input'))
            placeholder = inp.get('placeholder', '')
            if placeholder:
                input_descs.append(f"{name} (placeholder: {placeholder})")
            else:
                input_descs.append(name)
        parts.append(f"INPUTS: {' | '.join(input_descs)}")
    else:
        parts.append("INPUTS: aucun")
    
    # PRODUCTS - indexed list with unique btn ids and detail links
    if extracted.get('products'):
        parts.append("PRODUCTS:")
        for i, prod in enumerate(extracted['products'], 1):
            price_str = f" - {prod['price']}" if prod.get('price') else ""
            btn_id = prod.get('btn_id', f'add-to-cart-{i}')
            line = f"  [{i}] {prod['name']}{price_str} - btn: {btn_id}"
            if prod.get('detail'):
                line += f"\n       → To see details: Action=navigate Target={prod['detail']}"
            parts.append(line)
    else:
        parts.append("PRODUCTS: aucun visible")
    
    # MODAL / POPUP OVERLAY (e.g. cart confirmation)
    modal = extracted.get('modal', '')
    if modal:
        parts.append(f"\nMODAL_POPUP: {modal}")

    # ERRORS
    if extracted.get('errors'):
        parts.append(f"ERRORS: {' | '.join(extracted['errors'])}")
    else:
        parts.append("ERRORS: aucune")
    
    # Main content (optional, shorter)
    if extracted.get('text_content'):
        content = extracted['text_content'][:500]
        parts.append(f"\nPAGE CONTENT:\n{content}")
    
    return '\n'.join(parts)
