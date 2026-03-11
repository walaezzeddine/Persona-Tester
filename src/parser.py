

import re
from typing import Dict


def resolve_target(target: str) -> str:
    """
    Resolve a target identifier to a Playwright-compatible selector.

    If the target matches 'add-to-cart-N' (a btn id injected by dom_extractor),
    return a CSS attribute selector that Playwright can use directly.
    Otherwise return the target unchanged.

    Args:
        target: The target string from the parsed LLM response

    Returns:
        A Playwright-compatible selector string
    """
    if re.match(r'^add-to-cart-\d+$', target.strip()):
        return f'[data-btn-id="{target.strip()}"]'
    return target



def _parse_prose_response(text: str, result: Dict[str, str]) -> Dict[str, str]:
    """
    Fallback parser for prose-style responses without clear Thought/Action/Target format.
    
    Attempts to infer action and target from natural language.
    
    Args:
        text: Raw response text from the LLM
        result: Current result dictionary with defaults
        
    Returns:
        Updated result dictionary
    """
    text_lower = text.lower()
    
    # Pattern for "I will click on X" or "Let me click X" or "clicking on X"
    click_patterns = [
        r"(?:i will|let me|going to|i'll|i should|need to)\s+click\s+(?:on\s+)?[\"']?(.+?)[\"']?(?:\.|$|\n)",
        r"click(?:ing)?\s+(?:on\s+)?[\"']?(.+?)[\"']?(?:\.|$|\n)",
        r"(?:select|press|tap)\s+(?:on\s+)?[\"']?(.+?)[\"']?(?:\.|$|\n)"
    ]
    
    for pattern in click_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            result["action"] = "click"
            target = match.group(1).strip()
            # Clean up common suffixes
            target = re.sub(r'\s+(button|link|element|option)$', '', target)
            result["target"] = target
            result["thought"] = text[:300] + "..." if len(text) > 300 else text
            return result
    
    # Pattern for scrolling
    scroll_patterns = [
        r"(?:i will|let me|going to|i'll|i should|need to)\s+scroll\s+(up|down)",
        r"scroll(?:ing)?\s+(up|down)",
        r"(?:go|move)\s+(up|down)\s+(?:the page|on the page)"
    ]
    
    for pattern in scroll_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            result["action"] = "scroll"
            result["target"] = match.group(1).lower()
            result["thought"] = text[:300] + "..." if len(text) > 300 else text
            return result
    
    # Pattern for typing/searching
    type_patterns = [
        r"(?:i will|let me|going to|i'll|i should|need to)\s+(?:type|search|enter|input)\s+[\"']?(.+?)[\"']?(?:\s+in|\s+into|\.|$|\n)",
        r"(?:search|type|enter)\s+[\"'](.+?)[\"']",
        r"(?:searching|typing)\s+(?:for\s+)?[\"']?(.+?)[\"']?(?:\.|$|\n)"
    ]
    
    for pattern in type_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            result["action"] = "type"
            result["target"] = match.group(1).strip()
            result["thought"] = text[:300] + "..." if len(text) > 300 else text
            return result
    
    # Pattern for finishing/completing
    finish_patterns = [
        r"(?:task|objective|goal|mission)\s+(?:is\s+)?(?:complete|accomplished|done|finished)",
        r"(?:i have|i've)\s+(?:successfully\s+)?(?:completed|finished|accomplished)",
        r"(?:successfully\s+)?(?:added|purchased|completed)"
    ]
    
    for pattern in finish_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            result["action"] = "FINISH"
            result["target"] = "Task completed based on prose response"
            result["thought"] = text[:300] + "..." if len(text) > 300 else text
            return result
    
    # Pattern for abandoning/giving up
    abandon_patterns = [
        r"(?:cannot|can't|unable to)\s+(?:complete|finish|accomplish|find)",
        r"(?:giving up|abandoning|stopping)",
        r"(?:too many|excessive)\s+(?:errors|failures|problems)"
    ]
    
    for pattern in abandon_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            result["action"] = "ABANDON"
            result["target"] = "Task abandoned based on prose response"
            result["thought"] = text[:300] + "..." if len(text) > 300 else text
            return result
    
    # Default: use first sentence as thought, keep default scroll action
    first_sentence = re.split(r'[.!?]', text)[0]
    result["thought"] = first_sentence.strip() if first_sentence else text[:200]
    
    return result


def parse_response(text: str) -> Dict[str, str]:
    """
    Parse the LLM response and extract thought, action, and target fields.
    Includes fallback logic for prose-style responses.
    
    FALLBACK: Si 'Action:' n'est pas trouvé, retourne:
    {"thought": réponse complète, "action": "scroll", "target": "down"}
    Ne retourne JAMAIS un dict vide.
    
    Args:
        text: Raw response text from the LLM
        
    Returns:
        Dictionary with keys: thought, action, target
        Returns default values if parsing fails
    """
    
    # Default values - NEVER return empty dict
    result = {
        "thought": "Unable to parse response",
        "action": "scroll",
        "target": "down"
    }
    
    if not text or not isinstance(text, str):
        return result
    
    # Clean the text
    text = text.strip()
    
    # Check if response contains Action: pattern
    action_match = re.search(
        r'Action\s*:\s*(\w+)',
        text,
        re.IGNORECASE
    )
    
    # FALLBACK: Si 'Action:' n'est pas trouvé
    if not action_match:
        # Retourne la réponse complète comme thought, avec scroll/down par défaut
        result["thought"] = text[:500] + "..." if len(text) > 500 else text
        result["action"] = "scroll"
        result["target"] = "down"
        # Try prose parsing as secondary fallback
        result = _parse_prose_response(text, result)
        return result
    
    # Try to extract Thought
    thought_match = re.search(
        r'Thought\s*:\s*(.+?)(?=Action\s*:|$)',
        text,
        re.IGNORECASE | re.DOTALL
    )
    if thought_match:
        result["thought"] = thought_match.group(1).strip()
    else:
        result["thought"] = text[:200]  # Use beginning of response
    
    # Process the action
    action = action_match.group(1).strip().lower()
    valid_actions = ["click", "scroll", "type", "back", "navigate", "finish", "abandon"]
    if action in valid_actions:
        result["action"] = action.upper() if action in ["finish", "abandon"] else action
    else:
        # Try to match partial or similar actions
        if "click" in action:
            result["action"] = "click"
        elif "scroll" in action:
            result["action"] = "scroll"
        elif "back" in action or "return" in action or "previous" in action:
            result["action"] = "back"
        elif "navigate" in action or "goto" in action or "go_to" in action:
            result["action"] = "navigate"
        elif "type" in action or "input" in action or "write" in action:
            result["action"] = "type"
        elif "finish" in action or "done" in action or "complete" in action:
            result["action"] = "FINISH"
        elif "abandon" in action or "quit" in action or "give" in action:
            result["action"] = "ABANDON"
    
    # Try to extract Target
    target_match = re.search(
        r'Target\s*:\s*(.+?)(?=Thought\s*:|Action\s*:|$)',
        text,
        re.IGNORECASE | re.DOTALL
    )
    if target_match:
        result["target"] = target_match.group(1).strip()
    
    # Clean up target - remove trailing punctuation and newlines
    result["target"] = result["target"].rstrip('.,;:\n\r ')
    
    # Limit thought length for display
    if len(result["thought"]) > 500:
        result["thought"] = result["thought"][:500] + "..."
    
    return result


def validate_action(action: str) -> bool:
    """
    Check if the action is a valid action type.
    
    Args:
        action: The action string to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_actions = ["click", "scroll", "type", "back", "navigate", "FINISH", "ABANDON"]
    return action in valid_actions


def is_terminal_action(action: str) -> bool:
    """
    Check if the action is a terminal action (ends the loop).
    
    Args:
        action: The action string to check
        
    Returns:
        True if this action should end the navigation loop
    """
    return action in ["FINISH", "ABANDON"]
