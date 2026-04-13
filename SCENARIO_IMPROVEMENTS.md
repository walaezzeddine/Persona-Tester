# Scenario Improvement Guide

## Problem Identified 🔴

Your Wall Street Survivor test showed these issues:
1. Agent got stuck in loops (25 steps with no progress)
2. Agent kept clicking same links repeatedly
3. No clear understanding of the task
4. LLM returned "Invalid action None" (confusion)

## Root Causes

| Issue | Cause | Impact |
|-------|-------|--------|
| Vague scenario | "Analyze a company" - too open-ended | Agent doesn't know where to start |
| No success criteria | Unclear when task is done | Agent keeps searching |
| No guidance | Agent must figure out navigation alone | Gets stuck in loops |
| SPA confusion | Website uses hash navigation | Agent thinks page isn't working |

## Solutions Implemented ✅

### 1. Improved Scenario File
**File:** `scenarios/wallstreet_improved.yaml`

**What changed:**
```yaml
# BEFORE (vague):
description: "Analyze a company (e.g., Apple) using the research tools..."

# AFTER (clear):
description: |
  You are on Wall Street Survivor. Your task:
  1. Search for and analyze Apple (AAPL) stock
  2. Review its price, performance, metrics
  3. Make a BUY or SELL decision

key_actions:
  - "Search for AAPL using search box"
  - "Navigate to Apple stock details page"
  - "Review price and performance trends"
  - "Decide: Will you BUY or SELL?"
```

### 2. Enhanced Prompt Builder
**File:** `src/prompt_builder.py`

**Features added:**
- ✅ Display `key_actions` in system prompt
- ✅ Add navigation tips for SPA websites
- ✅ Show constraints (time limit, max retries)
- ✅ Better success/abandon criteria formatting

### 3. Advanced Navigation Guidance

Now the LLM gets these tips:
```
🚀 ADVANCED NAVIGATION TIPS:
- If links only add "#": This is a Single Page App (SPA)
  → Try scrolling down to load content
  → Use browser_evaluate for hidden elements
  → Look for search boxes or input fields
  → Try typing text directly
- If page seems stuck: Try scrolling or JavaScript evaluation
```

## New Scenario Structure

Create new scenarios in `scenarios/` following this template:

```yaml
name: "Task Name"

description: |
  Clear, step-by-step description
  What user needs to do:
  1. First action
  2. Second action
  3. Final goal

constraints:
  time_limit: 300
  max_retries: 3

success_criteria:
  - "Specific measurable outcome 1"
  - "Specific measurable outcome 2"
  - "Specific measurable outcome 3"

abandon_criteria:
  - "Cannot find required functionality"
  - "Website is non-functional"
  - "Unable to progress after N attempts"

key_actions:
  - "Step 1: Do this first..."
  - "Step 2: Then..."
  - "Step 3: Finally..."
```

## Example Scenarios

### Example 1: Stock Analysis (Wall Street)
```yaml
name: "Stock Analysis & Trading Decision"
description: |
  Search for Apple (AAPL) stock on Wall Street Survivor,
  review its price and metrics, then decide to BUY or SELL

key_actions:
  - "Search for AAPL using the stock search box"
  - "Navigate to Apple's stock details page"
  - "Review current price and P/E ratio"
  - "Make a BUY or SELL decision"

success_criteria:
  - "Found Apple (AAPL) with current price"
  - "Reviewed at least 2 metrics"
  - "Made explicit BUY or SELL decision"
```

### Example 2: Hotel Booking
```yaml
name: "Weekend Hotel Booking"
description: |
  Book a hotel on Booking.com for a weekend trip
  in Paris

key_actions:
  - "Enter destination: Paris"
  - "Set check-in date: 2026-04-18"
  - "Set check-out date: 2026-04-20"
  - "Search for hotels"
  - "Review options and click 'Book Now'"

success_criteria:
  - "Hotel reservation is confirmed"
  - "Confirmation number received"
```

## Testing the Improvements

### Quick Test
```bash
python test_wallstreet_improved.py
```

### Full Test with Backend
```bash
# Terminal 1: Backend
python run_backend.py

# Terminal 2: Test
python test_wallstreet_improved.py
```

## Expected Improvements

| Metric | Before | After |
|--------|--------|-------|
| Loop prevention | ❌ Loops forever | ✅ Clear exit criteria |
| Task clarity | ❌ Vague | ✅ Step-by-step |
| Navigation help | ❌ None | ✅ SPA tips included |
| Success rate | 0% | ⬆️ Should improve |

## Key Takeaways

1. **Vague scenarios = Lost agents**
   - Be specific and actionable

2. **Clear success criteria = Agent knows when to finish**
   - Don't just say "analyze", say "analyze X and make decision Y"

3. **SPA websites need special guidance**
   - Tell agent about hash navigation
   - Suggest JavaScript evaluation
   - Mention search boxes and inputs

4. **Step-by-step actions help enormously**
   - List key_actions in scenario
   - Agent will follow them more reliably

## Next Steps

1. ✅ Test improved scenario with `python test_wallstreet_improved.py`
2. ✅ Monitor first few steps - should be more purposeful
3. ✅ Adjust scenario based on actual results
4. ✅ Create more improved scenarios for other websites

---

**Questions?** Check `src/prompt_builder.py` to see how scenarios are processed, or review `scenarios/wallstreet_improved.yaml` as a template.
