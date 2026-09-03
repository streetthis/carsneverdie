"""
Helper script to perform a one-time login to Beehiiv and export the authenticated session state.
Run this locally:
    python save_beehiiv_session.py

A browser window will open. Log into your Beehiiv account normally.
Once you reach the dashboard, press Enter in the terminal to save your session.
The saved 'beehiiv_session.json' can be used locally or pasted into the GitHub Secret 'BEEHIIV_STORAGE_STATE'.
"""

import os
import sys
from playwright.sync_api import sync_playwright

SESSION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beehiiv_session.json")

def main():
    print("=" * 60)
    print("BEEHIIV SESSION CAPTURE UTILITY")
    print("=" * 60)
    print("Launching Chromium browser window...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print("Navigating to Beehiiv login page...")
        page.goto("https://app.beehiiv.com/login", wait_until="networkidle")
        
        print("\n>>> Please complete login in the opened browser window.")
        print(">>> Once you are on the Beehiiv dashboard / publications page, return here and press ENTER.")
        input("\nPress ENTER when you have successfully logged in: ")
        
        # Save storage state
        context.storage_state(path=SESSION_PATH)
        print(f"\n[SUCCESS] Session successfully saved to: {SESSION_PATH}")
        print(f"File size: {os.path.getsize(SESSION_PATH)} bytes")
        print("\nYou can now:")
        print("1. Keep 'beehiiv_session.json' locally for testing.")
        print("2. Copy the entire contents of 'beehiiv_session.json' and paste it as the GitHub Secret: BEEHIIV_STORAGE_STATE")
        
        browser.close()

if __name__ == "__main__":
    main()
