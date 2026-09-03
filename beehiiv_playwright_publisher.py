"""
Playwright-based Beehiiv Publisher.
Automates creating a new post on Beehiiv by loading an authenticated session state (from BEEHIIV_STORAGE_STATE env or beehiiv_session.json).
"""

import os
import json
import time
from playwright.sync_api import sync_playwright

def get_session_file_path() -> str:
    """Ensures a valid session file exists. If BEEHIIV_STORAGE_STATE env var is set, writes it to disk."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    session_path = os.path.join(base_dir, "beehiiv_session.json")
    
    env_state = os.getenv("BEEHIIV_STORAGE_STATE")
    if env_state and env_state.strip():
        try:
            # Validate JSON before writing
            parsed = json.loads(env_state)
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f)
            print(f"[Beehiiv Playwright] Loaded session state from BEEHIIV_STORAGE_STATE env var.")
        except Exception as e:
            print(f"[Beehiiv Playwright] Warning: could not parse BEEHIIV_STORAGE_STATE JSON: {e}")
            
    return session_path

def publish_newsletter_via_browser(
    title: str,
    subtitle: str,
    body_html_path: str = None,
    publish_now: bool = False
) -> dict:
    """
    Automates logging into Beehiiv via storage state, creating a draft or scheduled post,
    and injecting the newsletter HTML into the Beehiiv editor.
    """
    session_path = get_session_file_path()
    
    if not os.path.exists(session_path):
        return {
            "success": False,
            "error": "No Beehiiv session file found. Please run 'python save_beehiiv_session.py' locally or set BEEHIIV_STORAGE_STATE secret."
        }
        
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if not body_html_path:
        body_html_path = os.path.join(base_dir, "output_body_content.html")
        if not os.path.exists(body_html_path):
            body_html_path = os.path.join(base_dir, "output_newsletter.html")
            
    if not os.path.exists(body_html_path):
        return {
            "success": False,
            "error": f"Newsletter HTML file not found at {body_html_path}"
        }
        
    with open(body_html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    pub_id = os.getenv("BEEHIIV_PUBLICATION_ID", "pub_ec5a45c5-fcef-4515-8372-2b500843ed81")
    # Clean publication ID if needed
    clean_pub_id = pub_id.replace("pub_", "")
    
    print(f"[Beehiiv Playwright] Starting browser automation (Publish immediate: {publish_now})...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            storage_state=session_path,
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 1. Navigate to publications dashboard / post creation
            new_post_url = f"https://app.beehiiv.com/publications/{clean_pub_id}/posts/new"
            print(f"[Beehiiv Playwright] Navigating to: {new_post_url}")
            response = page.goto(new_post_url, wait_until="networkidle", timeout=45000)
            
            # Check if redirected to login (expired session)
            if "login" in page.url:
                browser.close()
                return {
                    "success": False,
                    "error": "Beehiiv session has expired or is invalid. Redirected to login page. Please refresh BEEHIIV_STORAGE_STATE."
                }
                
            time.sleep(3)
            
            # 2. Fill Title & Subtitle if fields exist
            # Beehiiv's new post page typically has an editable title area
            title_selector = 'input[placeholder*="Title"], textarea[placeholder*="Title"], [data-testid="post-title"], h1[contenteditable="true"]'
            if page.locator(title_selector).count() > 0:
                print(f"[Beehiiv Playwright] Setting post title: {title}")
                page.locator(title_selector).first.fill(title)
                page.keyboard.press("Enter")
            else:
                print("[Beehiiv Playwright] Title input not directly found by selector, attempting keyboard entry...")
                page.keyboard.type(title)
                page.keyboard.press("Enter")
                
            time.sleep(1)
            
            # 3. Insert HTML into the editor block
            # Beehiiv editor allows HTML block insertion via slash menu or clipboard paste
            print("[Beehiiv Playwright] Injecting HTML content into editor...")
            # Try to trigger Slash command for HTML or direct clipboard paste
            page.keyboard.type("/html")
            time.sleep(1)
            page.keyboard.press("Enter")
            time.sleep(1)
            
            # In HTML block or raw editor, insert html_content
            # Fallback: Use clipboard paste of HTML
            page.evaluate("""(html) => {
                const active = document.activeElement;
                if (active) {
                    const dt = new DataTransfer();
                    dt.setData('text/html', html);
                    dt.setData('text/plain', html);
                    const pasteEvent = new ClipboardEvent('paste', {
                        bubbles: true,
                        cancelable: true,
                        clipboardData: dt
                    });
                    active.dispatchEvent(pasteEvent);
                }
            }""", html_content)
            
            time.sleep(3)
            
            # 4. Save draft or publish
            # Look for 'Save', 'Schedule', or 'Publish' button
            save_button = page.locator('button:has-text("Save"), button:has-text("Draft")').first
            if save_button.count() > 0:
                save_button.click()
                print("[Beehiiv Playwright] Clicked Save/Draft button.")
                time.sleep(2)
                
            current_url = page.url
            print(f"[Beehiiv Playwright] Done. Current page URL: {current_url}")
            
            browser.close()
            return {
                "success": True,
                "post_url": current_url,
                "message": f"Successfully loaded and drafted post '{title}' in Beehiiv editor."
            }
            
        except Exception as e:
            # Capture error screenshot for debugging
            screenshot_path = os.path.join(base_dir, "beehiiv_error.png")
            page.screenshot(path=screenshot_path)
            browser.close()
            return {
                "success": False,
                "error": f"Browser automation error: {str(e)} (Screenshot saved to {screenshot_path})"
            }

if __name__ == "__main__":
    test_res = publish_newsletter_via_browser(
        title="TEST AUTOMATION - CARS NEVER DIE",
        subtitle="Daily collector car auction intelligence",
        publish_now=False
    )
    print("Result:", test_res)
