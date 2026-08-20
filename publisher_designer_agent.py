import os
import re
import markdown
from datetime import datetime
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext


# --- Deterministic HTML Template Builder ---

# Inline CSS styles for email client compatibility (Gmail, Outlook, Apple Mail)
INLINE_STYLES = {
    "h2": 'style="font-family: \'Playfair Display\', Georgia, serif; font-size: 22px; font-weight: 800; color: #1a1a1a; margin: 32px 0 14px 0; border-bottom: 2px solid #1a1a1a; padding-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;"',
    "h3": 'style="font-family: \'Playfair Display\', Georgia, serif; font-size: 18px; font-weight: 700; color: #1a1a1a; margin: 20px 0 10px 0;"',
    "p": 'style="font-family: \'Merriweather\', Georgia, serif; font-size: 17px; line-height: 1.7; color: #222222; margin: 0 0 16px 0;"',
    "a": 'style="color: #8b0000; font-weight: 700; text-decoration: underline;"',
    "ul": 'style="font-family: \'Merriweather\', Georgia, serif; font-size: 17px; line-height: 1.7; color: #222222; padding-left: 20px; margin: 12px 0 16px 0;"',
    "li": 'style="font-family: \'Merriweather\', Georgia, serif; font-size: 17px; line-height: 1.7; color: #222222; margin-bottom: 8px;"',
    "table": 'style="width: 100%; max-width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #1a1a1a; font-size: 14px; word-break: break-word;"',
    "th": 'style="background-color: #1a1a1a; color: #f6f1e7; font-family: \'Playfair Display\', Georgia, serif; font-size: 12.5px; font-weight: 700; padding: 10px 8px; text-transform: uppercase; letter-spacing: 0.5px; text-align: left;"',
    "td": 'style="font-family: \'Merriweather\', Georgia, serif; font-size: 14px; padding: 10px 8px; border-bottom: 1px solid #d4cebe; color: #222222; word-break: break-word;"',
    "img": 'style="max-width: 100%; width: 100%; height: auto; border: 2px solid #1a1a1a; margin: 18px auto; display: block;"',
    "hr": 'style="border: none; border-top: 1px solid #c4bda8; margin: 28px 0;"',
    "strong": 'style="font-weight: 700;"',
    "blockquote": 'style="background-color: #ede7da; border: 1px solid #1a1a1a; border-left: 5px solid #8b0000; padding: 16px 20px; margin: 24px 0;"',
}


def inject_inline_styles(html_content: str) -> str:
    """Injects inline CSS styles into every HTML tag for email client compatibility."""
    
    for tag, style_attr in INLINE_STYLES.items():
        # Handle self-closing tags like <img> and <hr>
        if tag in ("img", "hr"):
            # Replace <tag ...> keeping existing attributes, adding our styles
            html_content = re.sub(
                rf'<{tag}([^>]*?)(/?)>',
                lambda m: f'<{tag}{m.group(1)} {style_attr}{m.group(2)}>',
                html_content,
                flags=re.IGNORECASE
            )
        else:
            # Replace opening tags: <tag> or <tag class="..."> etc.
            html_content = re.sub(
                rf'<{tag}(\s[^>]*)?>',
                lambda m, t=tag, s=style_attr: f'<{t}{m.group(1) if m.group(1) else ""} {s}>',
                html_content,
                flags=re.IGNORECASE
            )
    
    # Remove duplicate style attributes (keep only the last one injected)
    html_content = re.sub(r'style="[^"]*"\s*style="', 'style="', html_content)
    
    return html_content


EMOJI_REGEX = re.compile(r'[\U00010000-\U0010FFFF\u2600-\u27FF\u2300-\u23FF\u2B00-\u2BFF\u200D\uFE0F]')

def _strip_header_emoji(match: re.Match) -> str:
    prefix = match.group(1)
    title = match.group(2)
    cleaned = EMOJI_REGEX.sub('', title).strip()
    return f"{prefix}{cleaned}"


def build_newsletter_html(tool_context: ToolContext, editorial_markdown: str) -> str:
    """Deterministic template builder: converts editorial Markdown to inline-styled HTML 
    and inserts it into email_template.html at the DYNAMIC_NEWSLETTER_HTML placeholder.
    
    Args:
        editorial_markdown: The full newsletter markdown content from dRew (Editor-in-Chief).
    
    Returns:
        Confirmation message with the path to the generated output_newsletter.html file.
    """
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "email_template.html")
    output_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_newsletter.html")
    output_whatsapp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_whatsapp.txt")
    
    # --- Step 1: Read the email template from disk ---
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_html = f.read()
    except FileNotFoundError:
        return f"ERROR: email_template.html not found at {template_path}"
    
    # --- Step 1.5: Strip redundant top title banner if present (template masthead already has it) ---
    editorial_markdown = re.sub(r'^\s*#?\s*\*?\s*(?:🏎️\s*)?CARS NEVER DIE\*?\s*\n+(?:\*?by dRew\*?\s*\n+)?(?:---\s*\n+)?', '', editorial_markdown, flags=re.IGNORECASE)

    # --- Step 1.6: Strip all emojis from headers ---
    editorial_markdown = re.sub(
        r'^(#{1,6}\s+)(.+)$',
        _strip_header_emoji,
        editorial_markdown,
        flags=re.MULTILINE
    )

    # --- Step 2: Convert editorial Markdown to raw HTML ---
    body_html = markdown.markdown(
        editorial_markdown,
        extensions=["tables", "fenced_code", "nl2br"]
    )
    
    # --- Step 3: Inject inline CSS styles into every tag for email client compatibility ---
    styled_body_html = inject_inline_styles(body_html)
    
    # --- Step 4: Substitute into the template placeholder ---
    if "<!-- DYNAMIC_NEWSLETTER_HTML -->" not in template_html:
        return "ERROR: email_template.html is missing the <!-- DYNAMIC_NEWSLETTER_HTML --> placeholder."
    
    final_html = template_html.replace("<!-- DYNAMIC_NEWSLETTER_HTML -->", styled_body_html)
    
    # --- Step 5: Write output_newsletter.html AND timestamped archive to disk ---
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    archives_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "archives")
    os.makedirs(archives_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    archive_path = os.path.join(archives_dir, f"newsletter_{timestamp}.html")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(final_html)
    
    # --- Step 6: Generate WhatsApp/Telegram text version ---
    whatsapp_text = generate_whatsapp_text(editorial_markdown)
    with open(output_whatsapp_path, "w", encoding="utf-8") as f:
        f.write(whatsapp_text)
    
    # --- Step 7: Auto-update daily editorial memory on disk ---
    _auto_update_memory(editorial_markdown)
    
    return f"SUCCESS: Newsletter HTML written to {output_html_path}, archived locally at {archive_path}, and WhatsApp text written to {output_whatsapp_path}."


def _auto_update_memory(editorial_markdown: str) -> None:
    """Fallback memory recorder: parses generated editorial markdown and ensures editorial_memory.json is updated."""
    try:
        memory_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editorial_memory.json")
        history = []
        if os.path.exists(memory_file):
            try:
                with open(memory_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        # Extract Spotlight car name from Section 2
        spotlight_match = re.search(r'##\s*2\.\s*Vehicle Spotlight[^\n]*\n+.*?\[(.*?)\]', editorial_markdown, re.DOTALL)
        spotlight_car = spotlight_match.group(1).strip() if spotlight_match else "Spotlight Car"

        # Extract sub-heading themes
        themes = re.findall(r'###\s*(.+)', editorial_markdown)
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        entry = {
            "date": today_str,
            "title": f"Daily Cars Never Die Edition - {today_str}",
            "spotlight_car": spotlight_car,
            "top_movers": [],
            "themes": [t.strip() for t in themes[:5]] if themes else ["Market Analysis"]
        }
        
        updated = False
        for i, h in enumerate(history):
            if h.get("date") == today_str:
                if spotlight_car != "Spotlight Car":
                    history[i]["spotlight_car"] = spotlight_car
                if themes:
                    history[i]["themes"] = [t.strip() for t in themes[:5]]
                updated = True
                break
        if not updated:
            history.append(entry)
            
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"[Memory Auto-Update Exception] {e}")


def generate_whatsapp_text(markdown_content: str) -> str:
    """Converts editorial markdown into a clean WhatsApp/Telegram-friendly text format."""
    text = re.sub(r'^\s*#?\s*\*?\s*(?:🏎️\s*)?CARS NEVER DIE\*?\s*\n+(?:\*?by dRew\*?\s*\n+)?(?:---\s*\n+)?', '', markdown_content, flags=re.IGNORECASE)
    
    # Strip emojis from headers
    text = re.sub(
        r'^(#{1,6}\s+)(.+)$',
        _strip_header_emoji,
        text,
        flags=re.MULTILINE
    )
    
    # Convert markdown headers to bold WhatsApp format
    text = re.sub(r'^#{1,3}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)
    
    # Convert markdown links [text](url) to WhatsApp format: text (url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)
    
    # Convert markdown bold **text** to WhatsApp bold *text*
    text = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', text)
    
    # Convert markdown images to just their alt text
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'[Chart: \1]', text)
    
    # Convert HTML img tags to alt text
    text = re.sub(r'<img[^>]*alt="([^"]*)"[^>]*/?>', r'[Chart: \1]', text)
    
    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


# --- Publisher Agent Definition ---
# This agent's ONLY job is to call build_newsletter_html with the editorial markdown.

PUBLISHER_INSTRUCTION = """You are a newsletter formatting agent. Your ONLY job:

1. Take the full editorial Markdown content from dRew (the previous agent's output).
2. Call `build_newsletter_html` with the COMPLETE editorial markdown as the `editorial_markdown` argument.
3. Return the result. Do NOT modify the markdown. Do NOT write your own HTML. Just pass it through.

CRITICAL: Pass the ENTIRE editorial markdown text exactly as received. Do not truncate, summarize, or reformat it."""

publisher_agent = Agent(
    name="publisher_designer",
    model="gemini-3.5-flash",
    instruction=PUBLISHER_INSTRUCTION,
    tools=[build_newsletter_html]
)
