#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { chromium, firefox, webkit } from "playwright";

/**
 * Execute a Playwright test script
 * @param {string} testScript - The JavaScript test code to execute
 * @param {string} browserName - The browser to use (chromium, firefox, webkit)
 * @param {boolean} showBrowser - Whether to run with visible browser window
 * @param {number} keepBrowserOpenMs - Keep browser open after execution (ms)
 * @param {number} slowMoMs - Playwright slowMo in ms for visible step-by-step execution
 * @returns {Promise<Object>} Test execution results
 */
async function executePlaywrightTest(testScript, browserName, showBrowser = true, keepBrowserOpenMs = 1500, slowMoMs = 0) {
  let browser = null;
  let context = null;
  let page = null;
  const executionLog = [];
  const screenshots = [];

  const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  try {
    const validBrowsers = ["chromium", "firefox", "webkit"];
    if (!validBrowsers.includes(browserName.toLowerCase())) {
      throw new Error(
        `Invalid browser name: ${browserName}. Must be one of: ${validBrowsers.join(", ")}`
      );
    }

    const browserType = browserName.toLowerCase() === "chromium"
      ? chromium
      : browserName.toLowerCase() === "firefox"
      ? firefox
      : webkit;

    const headless = !showBrowser;
    const launchSlowMo = Number.isFinite(Number(slowMoMs)) ? Math.max(0, Number(slowMoMs)) : 0;
    const openDelayMs = Number.isFinite(Number(keepBrowserOpenMs))
      ? Math.max(0, Math.min(60000, Number(keepBrowserOpenMs)))
      : 0;

    executionLog.push(`Launching ${browserName} browser (headless=${headless}, slowMo=${launchSlowMo}ms)...`);
    browser = await browserType.launch({ headless, slowMo: launchSlowMo });

    executionLog.push("Creating browser context...");
    context = await browser.newContext();

    executionLog.push("Creating new page...");
    page = await context.newPage();

    // Default timeout policy: 30s for both navigation and general page operations.
    page.setDefaultNavigationTimeout(30000);
    page.setDefaultTimeout(30000);

    const testFunction = new Function(
      "page",
      "context",
      "browser",
      "executionLog",
      `
      return (async () => {
        ${testScript}
      })();
      `
    );

    executionLog.push("Executing test script...");
    await testFunction(page, context, browser, executionLog);

    executionLog.push("Test execution completed successfully!");

    try {
      const screenshot = await page.screenshot({ encoding: "base64" });
      screenshots.push({
        name: "final-state",
        data: screenshot,
      });
    } catch (screenshotError) {
      executionLog.push(`Warning: Could not capture screenshot: ${screenshotError.message}`);
    }

    if (!headless && openDelayMs > 0) {
      executionLog.push(`Live mode: keeping browser open for ${openDelayMs}ms to inspect result...`);
      await pause(openDelayMs);
    }

    return {
      success: true,
      browserName,
      liveMode: !headless,
      executionLog,
      screenshots,
      message: "Test executed successfully",
    };

  } catch (error) {
    executionLog.push(`Error: ${error.message}`);

    if (page) {
      try {
        const screenshot = await page.screenshot({ encoding: "base64" });
        screenshots.push({
          name: "error-state",
          data: screenshot,
        });
      } catch (screenshotError) {
        executionLog.push(`Warning: Could not capture error screenshot: ${screenshotError.message}`);
      }
    }

    const openDelayMs = Number.isFinite(Number(keepBrowserOpenMs))
      ? Math.max(0, Math.min(60000, Number(keepBrowserOpenMs)))
      : 0;
    if (showBrowser && openDelayMs > 0) {
      executionLog.push(`Live mode: keeping browser open for ${openDelayMs}ms after error...`);
      await pause(openDelayMs);
    }

    return {
      success: false,
      browserName,
      liveMode: !!showBrowser,
      executionLog,
      screenshots,
      error: {
        message: error.message,
        stack: error.stack,
        name: error.name,
      },
    };

  } finally {
    try {
      if (page) {
        executionLog.push("Closing page...");
        await page.close();
      }
      if (context) {
        executionLog.push("Closing context...");
        await context.close();
      }
      if (browser) {
        executionLog.push("Closing browser...");
        await browser.close();
      }
    } catch (cleanupError) {
      executionLog.push(`Cleanup warning: ${cleanupError.message}`);
    }
  }
}

/**
 * Fetch the DOM content of a page at a given URL
 * @param {string} url - The URL to navigate to
 * @returns {Promise<Object>} The simplified DOM content
 */
async function fetchPageDom(url) {
  let browser = null;
  let page = null;

  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    page = await context.newPage();

    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForLoadState("load", { timeout: 30000 }).catch(() => {});

    const dom = await page.evaluate(() => {
      const removeSelectors = [
        "script", "style", "noscript", "svg", "link[rel='stylesheet']",
        "meta", "iframe", "video", "audio", "canvas", "picture > source",
      ];
      removeSelectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => el.remove());
      });

      document.querySelectorAll("*").forEach(el => {
        el.removeAttribute("style");
        Array.from(el.attributes).forEach(attr => {
          if (attr.name.startsWith("on")) {
            el.removeAttribute(attr.name);
          }
        });
      });

      return document.documentElement.outerHTML;
    });

    const pageTitle = await page.title();
    const pageUrl = page.url();

    await page.close();
    await context.close();
    await browser.close();
    browser = null;

    return {
      success: true,
      url: pageUrl,
      title: pageTitle,
      dom,
    };
  } catch (error) {
    return {
      success: false,
      url,
      error: {
        message: error.message,
        name: error.name,
      },
    };
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
  }
}

// Create MCP server instance
const mcpServer = new McpServer(
  {
    name: "playwright-test-executor",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

const server = mcpServer.server;

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "execute_playwright_test",
        description:
          "Execute a Playwright test script in a specified browser. " +
          "The test script should contain valid JavaScript code that uses the Playwright API. " +
          "Available variables in the test script: page (Page object), context (BrowserContext), browser (Browser), executionLog (array to log messages).",
        inputSchema: {
          type: "object",
          properties: {
            testScript: {
              type: "string",
              description:
                "The JavaScript code containing the Playwright test to execute. " +
                "Example: await page.goto('https://example.com'); await page.click('button');",
            },
            browserName: {
              type: "string",
              enum: ["chromium", "firefox", "webkit"],
              description: "The browser to use for test execution",
              default: "chromium",
            },
            showBrowser: {
              type: "boolean",
              description: "If true, run with visible browser window for live test observation",
              default: true,
            },
            keepBrowserOpenMs: {
              type: "number",
              description: "How long to keep visible browser open after execution (ms)",
              default: 1500,
            },
            slowMoMs: {
              type: "number",
              description: "Playwright slowMo delay in ms between operations",
              default: 0,
            },
          },
          required: ["testScript", "browserName"],
        },
      },
      {
        name: "fetch_page_dom",
        description:
          "Fetch the DOM content of a web page at the given URL. " +
          "Launches a headless Chromium browser, navigates to the page, " +
          "and returns a cleaned HTML DOM (scripts, styles, and non-visible elements removed). " +
          "Useful for providing page structure context to an LLM.",
        inputSchema: {
          type: "object",
          properties: {
            url: {
              type: "string",
              description: "The full URL of the page to fetch (e.g. https://example.com/page)",
            },
          },
          required: ["url"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "execute_playwright_test") {
    const {
      testScript,
      browserName = "chromium",
      showBrowser = true,
      keepBrowserOpenMs = 1500,
      slowMoMs = 0,
    } = request.params.arguments;

    if (!testScript) {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              success: false,
              error: "testScript parameter is required",
            }, null, 2),
          },
        ],
      };
    }

    const result = await executePlaywrightTest(
      testScript,
      browserName,
      showBrowser,
      keepBrowserOpenMs,
      slowMoMs,
    );

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  }

  if (request.params.name === "fetch_page_dom") {
    const { url } = request.params.arguments;

    if (!url) {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              success: false,
              error: "url parameter is required",
            }, null, 2),
          },
        ],
      };
    }

    const result = await fetchPageDom(url);

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({
          success: false,
          error: `Unknown tool: ${request.params.name}`,
        }, null, 2),
      },
    ],
  };
});

async function main() {
  const transport = new StdioServerTransport();
  await mcpServer.connect(transport);
  console.error("Playwright Custom MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
