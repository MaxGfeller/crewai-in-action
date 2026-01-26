#!/usr/bin/env python3
"""Debug script to test login flow and check URL tracking."""

from playwright.sync_api import sync_playwright
import time

def test_login():
    print("Testing login flow - checking URL tracking...")
    print("-" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Navigate to app
        print("\n1. Navigating to http://localhost:4100/")
        page.goto("http://localhost:4100/")
        print(f"   page.url: {page.url}")

        # Fill login form
        print("\n2. Filling login form...")
        page.fill('[placeholder="you@example.com"]', 'demo@example.com')
        page.fill('input[type="password"]', 'password123')

        # Click login
        print("\n3. Clicking login button...")
        page.click('button:has-text("Login")')

        # Wait and check URL multiple ways
        print("\n4. Waiting 3 seconds...")
        time.sleep(3)

        print("\n5. Checking URL with different methods:")
        print(f"   page.url property:        {page.url}")
        print(f"   page.evaluate location:   {page.evaluate('() => window.location.href')}")
        print(f"   main_frame.url:           {page.main_frame.url}")

        # Check what's visible on page
        print("\n6. Page content check:")
        body_text = page.evaluate("() => document.body.innerText.slice(0, 200)")
        print(f"   First 200 chars of body: {body_text[:200]}...")

        input("\nPress Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    test_login()
