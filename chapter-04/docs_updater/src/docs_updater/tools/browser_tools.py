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


def get_current_url(page: Page) -> str:
    """Get current URL via JavaScript (handles SPAs where page.url may be stale)."""
    return page.evaluate("() => window.location.href")


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


def is_playwright_selector(selector: str) -> bool:
    """Check if selector is already a valid Playwright selector."""
    prefixes = ('text=', 'role=', '#', '.', '[', 'button', 'a', 'input', 'textarea')
    keywords = (':has-text(', ':text(')
    return selector.startswith(prefixes) or any(k in selector for k in keywords)


def wait_for_stable(page: Page, timeout: int = 5000):
    """Wait for page to be stable after navigation/interaction."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
        page.wait_for_timeout(500)
    except Exception:
        pass


# --- Input Schemas ---

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


# --- Tool Implementations ---

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


class BrowserCloseTool(BaseTool):
    name: str = "browser_close"
    description: str = "Close the browser when done with all tasks."

    def _run(self) -> str:
        try:
            close_browser()
            return "Browser closed."
        except Exception as e:
            return f"Error closing browser: {e}"


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
