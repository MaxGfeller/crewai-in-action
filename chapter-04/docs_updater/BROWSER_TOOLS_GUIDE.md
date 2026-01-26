# Implementing Browser Tools for the Screenshot Agent

This section continues from where we set up the screenshot agent's role, goal, and backstory. Now we need to give the agent the ability to actually control a browser.

## Why Custom Browser Tools?

CrewAI does not provide built-in tools for local browser automation. While we could theoretically use the official Playwright MCP server and bind it to an agent, CrewAI's MCP support at the time of writing was not sufficient for reliable browser automation. Instead, we'll implement our own set of Playwright-based tools that give the screenshot agent full control over a local browser.

The key challenge with browser automation in an agentic context is state management. When an agent calls multiple tools in sequence—navigate to a page, type credentials, click a button, take a screenshot—each tool invocation must operate on the same browser instance. If we created a new browser for each tool call, we'd lose all session state between calls.

To solve this, we'll maintain a global browser instance that persists across tool calls within a single crew run.

## Setting Up the Browser State

First, let's install the Playwright dependency if you haven't already:

```bash
uv add playwright
```

Now create the file `src/docs_updater/tools/browser_tools.py` and start with the imports and global state management:

```python
"""
Custom Playwright-based browser tools for the screenshotter agent.
These tools maintain a persistent browser instance across calls.
"""

from crewai.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
from playwright.sync_api import sync_playwright, Browser, Page, Playwright
import os


# Global browser state - persists across tool calls
_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
_page: Optional[Page] = None
```

These three global variables will hold our Playwright instance, browser, and page objects. By keeping them at module level, they persist across multiple tool invocations within the same Python process.

Next, we need a function that lazily initializes the browser when first needed and returns the existing instance on subsequent calls:

```python
def get_page() -> Page:
    """Get or create the browser page instance."""
    global _playwright, _browser, _page

    # Check if existing page/browser is still valid
    try:
        if _page is not None and _page.context.browser:
            return _page
    except Exception:
        _page = _browser = None

    if _playwright is None:
        _playwright = sync_playwright().start()
    if _browser is None:
        _browser = _playwright.chromium.launch(headless=True)
    _page = _browser.new_page()
    return _page
```

This function checks whether we already have a valid page. If the browser crashed or is in a bad state, it resets everything and creates fresh instances. The browser runs in headless mode, which means no visible window appears—ideal for automated screenshots.

## Handling Single-Page Applications

Modern web applications like our Next.js demo app use client-side navigation. When you click a link, the browser URL changes without a full page reload. This causes a subtle problem: Playwright's `page.url` property may return a stale value because it only updates on actual navigation events.

To get the real current URL, we need to ask the browser directly via JavaScript:

```python
def get_current_url(page: Page) -> str:
    """Get current URL via JavaScript (handles SPAs where page.url may be stale)."""
    return page.evaluate("() => window.location.href")
```

We also need a cleanup function to properly close the browser when the agent finishes its work:

```python
def close_browser():
    """Close the browser and cleanup resources."""
    global _playwright, _browser, _page
    if _page:
        _page.close()
        _page = None
    if _browser:
        _browser.close()
        _browser = None
    if _playwright:
        _playwright.stop()
        _playwright = None
```

## Helper Functions

Two more helper functions will reduce code duplication across our tools. First, a function to detect whether a string is already a valid Playwright selector:

```python
def is_playwright_selector(selector: str) -> bool:
    """Check if selector is already a valid Playwright selector."""
    prefixes = ('text=', 'role=', '#', '.', '[', 'button', 'a', 'input', 'textarea')
    keywords = (':has-text(', ':text(')
    return selector.startswith(prefixes) or any(k in selector for k in keywords)
```

This allows agents to pass either plain text (like "Login") or proper Playwright selectors (like `#login-btn` or `text=Login`), and our tools will handle both correctly.

Second, a function to wait for page stability after interactions:

```python
def wait_for_stable(page: Page, timeout: int = 5000):
    """Wait for page to be stable after navigation/interaction."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
        page.wait_for_timeout(500)
    except Exception:
        pass
```

The `networkidle` state means no network requests have been made for 500ms, which usually indicates the page has finished loading. The extra 500ms wait gives JavaScript frameworks time to render after data arrives.

## Defining Input Schemas

Each tool needs an input schema that tells the LLM what parameters it accepts. We define these using Pydantic models:

```python
class NavigateInput(BaseModel):
    url: str = Field(..., description="The URL to navigate to")


class ClickInput(BaseModel):
    selector: str = Field(..., description="CSS selector or text content. Examples: 'text=Login', '#submit-btn', 'button:has-text(\"Submit\")'")


class TypeInput(BaseModel):
    selector: str = Field(..., description="CSS selector or placeholder. Examples: '#email', '[placeholder=\"Email\"]', 'input[type=\"password\"]'")
    text: str = Field(..., description="The text to type")
    press_enter: bool = Field(default=False, description="Whether to press Enter after typing")


class ScreenshotInput(BaseModel):
    output_path: str = Field(..., description="Filename for the screenshot (e.g., 'dashboard.png')")
    full_page: bool = Field(default=False, description="Capture full scrollable page")


class WaitInput(BaseModel):
    selector: str = Field(..., description="CSS selector of the element to wait for")
    timeout: int = Field(default=10000, description="Maximum wait time in milliseconds")
```

The `Field` descriptions are crucial—they appear in the tool's schema and help the LLM understand how to use each parameter correctly.

## Implementing the Navigation Tool

Now let's implement the actual tools, starting with navigation:

```python
class BrowserNavigateTool(BaseTool):
    name: str = "browser_navigate"
    description: str = "Navigate the browser to a URL."
    args_schema: Type[BaseModel] = NavigateInput

    def _run(self, url: str) -> str:
        try:
            page = get_page()
            page.goto(url, wait_until="networkidle")
            return f"Navigated to {url}. Title: {page.title()}"
        except Exception as e:
            return f"Error navigating to {url}: {e}"
```

The tool uses `wait_until="networkidle"` to ensure the page has fully loaded before returning. The response includes the page title, which helps the agent confirm it reached the expected page.

## Implementing the Snapshot Tool

The snapshot tool is the most complex. It extracts a structured representation of the page's interactive elements, giving the agent visibility into what it can click, type into, or read:

```python
class BrowserSnapshotTool(BaseTool):
    name: str = "browser_snapshot"
    description: str = "Get a snapshot of visible page elements (buttons, inputs, links, headings). Use before interacting with elements."

    def _run(self) -> str:
        try:
            page = get_page()
            wait_for_stable(page)

            url = get_current_url(page)
            elements = page.evaluate("""() => {
                const results = [];
                const visible = el => el.offsetParent !== null;

                document.querySelectorAll('button, [role="button"], input[type="submit"]').forEach(el => {
                    if (visible(el)) results.push({type: 'BUTTON', text: el.innerText?.slice(0,50) || el.value || 'unnamed'});
                });

                document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]), textarea').forEach(el => {
                    if (visible(el)) {
                        const label = document.querySelector(`label[for="${el.id}"]`)?.innerText || el.placeholder || el.name || '';
                        results.push({type: 'INPUT', inputType: el.type || 'text', label, selector: el.id ? '#'+el.id : `[name="${el.name}"]`});
                    }
                });

                document.querySelectorAll('a[href]').forEach(el => {
                    if (visible(el) && el.innerText?.trim()) results.push({type: 'LINK', text: el.innerText.slice(0,50)});
                });

                document.querySelectorAll('h1, h2, h3').forEach(el => {
                    if (visible(el) && el.innerText?.trim()) results.push({type: 'HEADING', level: el.tagName, text: el.innerText.slice(0,80)});
                });

                return results;
            }""")

            lines = [f"URL: {url}", f"Title: {page.title()}", ""]

            for category in ['HEADING', 'BUTTON', 'INPUT', 'LINK']:
                items = [e for e in elements if e['type'] == category][:15]
                if items:
                    lines.append(f"=== {category}S ===")
                    for item in items:
                        if category == 'BUTTON':
                            lines.append(f"  • {item['text']}")
                        elif category == 'INPUT':
                            lines.append(f"  • ({item['inputType']}) {item['label']} → {item['selector']}")
                        elif category == 'LINK':
                            lines.append(f"  • {item['text']}")
                        elif category == 'HEADING':
                            lines.append(f"  • {item['level']}: {item['text']}")
                    lines.append("")

            return "\n".join(lines)
        except Exception as e:
            return f"Error getting snapshot: {e}"
```

The JavaScript code runs in the browser context and collects information about buttons, inputs, links, and headings. The `visible` helper ensures we only report elements the user can actually see and interact with. For inputs, we also extract selectors that the agent can use with subsequent tool calls.

Notice that this tool has no `args_schema`—when a tool needs no input parameters, we simply omit the schema definition.

## Implementing Click and Type Tools

The click tool handles element interaction:

```python
class BrowserClickTool(BaseTool):
    name: str = "browser_click"
    description: str = "Click an element. Use text=, CSS selectors, or plain text. After clicking, use browser_snapshot to see new state."
    args_schema: Type[BaseModel] = ClickInput

    def _run(self, selector: str) -> str:
        try:
            page = get_page()
            url_before = get_current_url(page)

            if is_playwright_selector(selector):
                page.click(selector)
            else:
                page.click(f'text="{selector}"')

            wait_for_stable(page)
            new_url = get_current_url(page)

            if new_url != url_before:
                return f"Clicked '{selector}'. Navigated to {new_url}"
            return f"Clicked '{selector}'. URL unchanged."
        except Exception as e:
            return f"Error clicking '{selector}': {e}"
```

The tool tracks whether clicking caused navigation, which helps the agent understand the effect of its action.

The type tool fills in form fields:

```python
class BrowserTypeTool(BaseTool):
    name: str = "browser_type"
    description: str = "Type text into an input field identified by CSS selector or placeholder."
    args_schema: Type[BaseModel] = TypeInput

    def _run(self, selector: str, text: str, press_enter: bool = False) -> str:
        try:
            page = get_page()

            if is_playwright_selector(selector):
                page.fill(selector, text)
            else:
                try:
                    page.fill(f'[placeholder="{selector}"]', text)
                except Exception:
                    page.fill(f'input:near(:text("{selector}"))', text)

            if press_enter:
                page.keyboard.press("Enter")
                wait_for_stable(page)
                return f"Typed '{text}' and pressed Enter."
            return f"Typed '{text}' into {selector}"
        except Exception as e:
            return f"Error typing into '{selector}': {e}"
```

If the selector isn't a proper Playwright selector, we first try matching by placeholder text, then fall back to finding an input near matching text (useful for label associations).

## Implementing the Screenshot Tool

The screenshot tool captures the current page state:

```python
class BrowserScreenshotTool(BaseTool):
    name: str = "browser_screenshot"
    description: str = "Take a screenshot of the current page."
    args_schema: Type[BaseModel] = ScreenshotInput
    docs_base_directory: str = ""

    def _run(self, output_path: str, full_page: bool = False) -> str:
        try:
            page = get_page()

            if self.docs_base_directory:
                from docs_updater.tools.scoped_file_tools import validate_and_resolve_path
                abs_path = validate_and_resolve_path(output_path, self.docs_base_directory)
            else:
                abs_path = output_path

            os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
            page.screenshot(path=abs_path, full_page=full_page)
            return f"Screenshot saved to: {output_path}"
        except Exception as e:
            return f"Error taking screenshot: {e}"
```

Notice the `docs_base_directory` attribute. When set, screenshots are saved relative to the documentation folder, and we reuse the `validate_and_resolve_path` function from our scoped file tools to ensure screenshots can only be saved within the allowed directory. This maintains the same security boundaries we established for file operations.

## Implementing Wait and Close Tools

The wait tool helps with timing-sensitive interactions:

```python
class BrowserWaitTool(BaseTool):
    name: str = "browser_wait"
    description: str = "Wait for an element to appear on the page."
    args_schema: Type[BaseModel] = WaitInput

    def _run(self, selector: str, timeout: int = 10000) -> str:
        try:
            page = get_page()
            page.wait_for_selector(selector, timeout=timeout)
            return f"Element '{selector}' is visible."
        except Exception as e:
            return f"Timeout waiting for '{selector}': {e}"
```

Finally, the close tool releases browser resources:

```python
class BrowserCloseTool(BaseTool):
    name: str = "browser_close"
    description: str = "Close the browser when done with all tasks."

    def _run(self) -> str:
        try:
            close_browser()
            return "Browser closed."
        except Exception as e:
            return f"Error closing browser: {e}"
```

## The Factory Function

To make it easy to get all browser tools configured for a specific documentation directory, we provide a factory function:

```python
def get_browser_tools(docs_base_directory: str = ""):
    """Get all browser tools for the agent."""
    screenshot_tool = BrowserScreenshotTool()
    if docs_base_directory:
        screenshot_tool.docs_base_directory = docs_base_directory

    return [
        BrowserNavigateTool(),
        BrowserSnapshotTool(),
        BrowserClickTool(),
        BrowserTypeTool(),
        screenshot_tool,
        BrowserWaitTool(),
        BrowserCloseTool(),
    ]
```

This function instantiates all seven tools and optionally configures the screenshot tool with a base directory for saving images.

## Using the Browser Tools

With the browser tools implemented, you can now update the screenshot agent in `crew.py` to use them:

```python
from docs_updater.tools.browser_tools import get_browser_tools

@agent
def screenshotter(self) -> Agent:
    return Agent(
        config=self.agents_config['screenshotter'],
        tools=get_browser_tools(self.docs_base_directory),
        verbose=self.verbose,
    )
```

The screenshot agent now has everything it needs to:
1. Navigate to the demo application
2. Log in with the demo credentials
3. Navigate to specific pages
4. Take screenshots and save them to the documentation folder

When the documentation writer agent detects that a screenshot needs updating, it can delegate to the screenshot agent, which will use these tools to capture the current state of the UI.


