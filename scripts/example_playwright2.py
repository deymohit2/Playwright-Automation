#!/usr/bin/env python3
"""
Minimal Playwright example (synchronous API) that fills and submits a form.

Usage:
  python scripts/example_playwright.py

Replace `TARGET_URL` and selectors with the real form fields from the site you want to automate.
"""
from playwright.sync_api import sync_playwright

import os

TARGET_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdibBJen81aKFs7BpsAb1s7IUk6K_1YzvBPCM3dBaSvPPve0g/viewform?usp=dialog"  # <-- change to your target URL

# By default run headless (suitable for CI / containers). To see the browser set
# environment variable `HEADLESS=0` when running the script.
HEADLESS = os.environ.get("HEADLESS", "1") not in ("0", "false", "False")


def run():
    with sync_playwright() as pw:
        # Use `HEADLESS` env var to control headed/headless mode.
        browser = pw.chromium.launch(headless=HEADLESS)
        page = browser.new_page()

        print(f"Opening {TARGET_URL}")
        page.goto(TARGET_URL)

        # Example field fills - update selectors to match the page you're automating
        try:
            page.fill("input[name='first_name']", "John")
            page.fill("input[name='last_name']", "Doe")
            page.fill("input[name='email']", "john.doe@example.com")
        except Exception:
            # If selectors don't match, show page HTML snippet to help debugging
            snippet = page.content()[:2000]
            print("Could not fill fields with the example selectors. Page snippet:\n", snippet)

        # Click submit (adjust selector as necessary)
        try:
            page.click("button[type='submit']")
        except Exception:
            # Some forms use input[type=submit]
            page.click("input[type='submit']")

        # Wait for network to be idle or a success element to appear
        page.wait_for_load_state("networkidle")

        # Optionally check for a success message
        # success = page.query_selector(".success-message")
        # if success:
        #     print('Form submitted, success message:', success.inner_text())

        print("Done — page title:", page.title())
        browser.close()


if __name__ == "__main__":
    run()
