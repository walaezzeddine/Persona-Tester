import asyncio, traceback, sys
from pathlib import Path

sys.path.insert(0, str(Path("mcp-server/playwright-custom").resolve()))
from agent import PlaywrightTestAgent

async def main():
    agent = PlaywrightTestAgent(provider="ollama")
    try:
        r = await agent.fetch_dom("https://app.wallstreetsurvivor.com")
        print("fetch_dom success:", r.get("success"))
        print("fetch_dom error:", r.get("error"))
    except BaseException as e:
        traceback.print_exc()
        if hasattr(e, "exceptions"):
            print("\nSub-exceptions:")
            for i, sub in enumerate(getattr(e, "exceptions", []), 1):
                print(f"{i}. {type(sub).__name__}: {sub}")

asyncio.run(main())
