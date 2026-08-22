import os
import re
import json
import markdown
from datetime import datetime
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext


# --- Deterministic HTML Template Builder ---

# Inline CSS styles for email client compatibility (Gmail, Outlook, Apple Mail)
INLINE_STYLES = {
    "h1": 'style="font-family: \'Oswald\', Montserrat, \'Lucida Sans Unicode\', sans-serif; font-weight: 600; font-size: 38px; color: #283642; line-height: 1.1; margin: 16px 0 6px 0;"',
    "h2": 'style="font-family: \'Oswald\', Montserrat, \'Lucida Sans Unicode\', sans-serif; font-weight: 700; font-size: 28px; color: #283642; line-height: 1.1; margin: 16px 0 6px 0; text-transform: uppercase;"',
    "h3": 'style="font-family: \'Oswald\', Montserrat, \'Lucida Sans Unicode\', sans-serif; font-weight: 700; font-size: 20px; color: #283642; line-height: 1.1; margin: 14px 0 4px 0; text-transform: uppercase;"',
    "h4": 'style="font-family: \'Oswald\', Montserrat, \'Lucida Sans Unicode\', sans-serif; font-weight: 700; font-size: 17px; color: #283642; line-height: 1.15; margin: 12px 0 4px 0;"',
    "h5": 'style="font-family: \'Helvetica\', Arial, sans-serif; font-weight: 600; font-size: 14px; color: #4A5B6A; text-transform: uppercase; letter-spacing: 0.5px; margin: 12px 0 2px 0;"',
    "p": 'style="font-family: \'Helvetica\', Arial, sans-serif; font-weight: 400; color: #4A5B6A; font-size: 16px; line-height: 1.5; margin: 0 0 12px 0;"',
    "a": 'style="color: #D65A43 !important; font-weight: 700; text-decoration: underline; font-style: italic;"',
    "ul": 'style="font-family: \'Helvetica\', Arial, sans-serif; font-size: 16px; line-height: 1.5; color: #4A5B6A; padding-left: 22px; margin: 12px 0;"',
    "li": 'style="font-family: \'Helvetica\', Arial, sans-serif; font-size: 16px; line-height: 1.5; color: #4A5B6A; margin-bottom: 8px;"',
    "table": 'style="width: 100%; max-width: 100%; border-collapse: collapse; margin: 16px 0; border: 1px solid #C0C0C0; font-size: 14px; word-break: break-word;"',
    "th": 'style="background-color: #F1F1F1; color: #283642; font-family: \'Trebuchet MS\', \'Lucida Grande\', Tahoma, sans-serif; font-size: 13px; font-weight: 700; padding: 8px; border: 1px solid #C0C0C0; text-align: left;"',
    "td": 'style="font-family: \'Helvetica\', Arial, sans-serif; font-size: 14px; padding: 8px; border: 1px solid #C0C0C0; color: #283642; word-break: break-word;"',
    "img": 'style="max-width: 100%; width: 100%; height: auto; margin: 12px auto; display: block;"',
    "hr": 'style="border: none; border-top: 1px solid #283642; margin: 24px 0;"',
    "strong": 'style="font-weight: 700; color: #283642;"',
    "blockquote": 'style="background-color: #F3F1EE; border-top: 1px solid #283642; border-bottom: 1px solid #283642; padding: 16px 20px; margin: 20px 0;"',
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
    """Deterministic template builder: converts editorial Markdown to inline-styled 
    Beehiiv Studio HTML matching your exact Beehiiv template design.
    """
    output_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_newsletter.html")
    output_whatsapp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_whatsapp.txt")
    
    # --- Step 1: Strip redundant top title banner if present ---
    editorial_markdown = re.sub(r'^\s*#?\s*\*?\s*(?:🏎️\s*)?CARS NEVER DIE\*?\s*\n+(?:\*?by dRew\*?\s*\n+)?(?:---\s*\n+)?', '', editorial_markdown, flags=re.IGNORECASE)

    # --- Step 2: Strip all emojis from headers ---
    editorial_markdown = re.sub(
        r'^(#{1,6}\s+)(.+)$',
        _strip_header_emoji,
        editorial_markdown,
        flags=re.MULTILINE
    )

    # --- Step 3: Convert editorial Markdown to raw HTML ---
    body_html = markdown.markdown(
        editorial_markdown,
        extensions=["tables", "fenced_code", "nl2br"]
    )
    
    # --- Step 4: Inject inline CSS styles into every tag for email client compatibility ---
    styled_body_html = inject_inline_styles(body_html)
    
    # --- Step 5: Format sections into #F3F1EE cards & 2-column layouts matching Beehiiv template ---
    def _wrap_section_1(match):
        h2_tag = match.group(1)
        content = match.group(2)
        paras = re.findall(r'<p[^>]*>.*?</p>', content, re.DOTALL)
        if len(paras) >= 2:
            left_col = f"{h2_tag}\n" + "\n".join(paras[:1])
            right_col = "\n".join(paras[1:])
            return f'''<table role="none" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin:20px 0;">
  <tr>
    <td bgcolor="#F3F1EE" style="background-color:#F3F1EE;border-top:1px solid #283642;border-bottom:1px solid #283642;padding:20px 12px;box-sizing:border-box;">
      <table role="none" width="100%" border="0" cellspacing="0" cellpadding="0">
        <tr>
          <td width="50%" valign="top" style="vertical-align:top;padding:0 10px;">
            {left_col}
          </td>
          <td width="50%" valign="top" style="vertical-align:top;padding:0 10px;">
            {right_col}
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>'''
        else:
            return f'''<table role="none" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin:20px 0;">
  <tr>
    <td bgcolor="#F3F1EE" style="background-color:#F3F1EE;border-top:1px solid #283642;border-bottom:1px solid #283642;padding:20px 16px;box-sizing:border-box;">
      {h2_tag}
      {content}
    </td>
  </tr>
</table>'''

    styled_body_html = re.sub(
        r'(<h2[^>]*>\s*(?:<b>)?\s*WHY I DID NOT SLEEP LAST NIGHT\??\s*(?:</b>)?\s*</h2>)(.*?)(?=<h[1-6]|<table|\Z)',
        _wrap_section_1,
        styled_body_html,
        flags=re.IGNORECASE | re.DOTALL
    )

    def _wrap_section_3(match):
        h5_tag = match.group(1) if match.group(1) else ""
        h2_tag = match.group(2)
        content = match.group(3)
        return f'''<table role="none" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin:20px 0;">
  <tr>
    <td bgcolor="#F3F1EE" style="background-color:#F3F1EE;border-top:1px solid #283642;border-bottom:1px solid #283642;padding:20px 16px;box-sizing:border-box;">
      {h5_tag}
      {h2_tag}
      {content}
    </td>
  </tr>
</table>'''

    styled_body_html = re.sub(
        r'(<h5[^>]*>\s*The Leader Board\s*</h5>\s*)?(<h2[^>]*>\s*(?:<b>)?\s*Auction House Roundup.*?\s*(?:</b>)?\s*</h2>)(.*?)(?=<h[1-6]|\Z)',
        _wrap_section_3,
        styled_body_html,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Look for top lead feature image (non-chart photo) in styled_body_html
    hero_image_html = ""
    lead_img_match = re.search(r'(<p[^>]*>\s*)?(<img[^>]+src=["\']([^"\']+)["\'][^>]*>)\s*(</p>)?', styled_body_html)
    if lead_img_match:
        img_src = lead_img_match.group(3)
        if not any(chart_name in img_src.lower() for chart_name in ["chart", "trend", "combo", "price_band", "histogram"]):
            hero_image_html = f'''<table role="none" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin:0 0 20px 0;">
  <tr>
    <td align="center" style="padding:0;">
      <img src="{img_src}" alt="Cars Never Die Lead Feature" style="max-width:100%;width:100%;height:auto;display:block;border-radius:0px;border:none;" />
    </td>
  </tr>
</table>'''
            styled_body_html = styled_body_html.replace(lead_img_match.group(0), "", 1)

    # Add top CARS NEVER DIE Oswald title banner + Top Hero Image
    top_banner = f'''<table role="none" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin:0 0 16px 0;">
  <tr>
    <td align="center" style="text-align:center;padding:16px 0 8px 0;">
      <h1 style="font-family:'Oswald',Montserrat,'Lucida Sans Unicode',sans-serif;font-weight:600;font-size:38px;color:#283642;margin:0;letter-spacing:1.5px;text-align:center;"><b>CARS NEVER DIE</b></h1>
    </td>
  </tr>
</table>
{hero_image_html}'''

    final_beehiiv_html = top_banner + "\n" + styled_body_html

    # --- Step 6: Write output_newsletter.html, output_body_content.html AND timestamped archive to disk ---
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(final_beehiiv_html)
        
    body_content_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_body_content.html")
    with open(body_content_path, "w", encoding="utf-8") as f:
        f.write(final_beehiiv_html)
        
    archives_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "archives")
    os.makedirs(archives_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    archive_path = os.path.join(archives_dir, f"newsletter_{timestamp}.html")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(final_beehiiv_html)
    
    # --- Step 7: Generate WhatsApp/Telegram text version ---
    whatsapp_text = generate_whatsapp_text(editorial_markdown)
    with open(output_whatsapp_path, "w", encoding="utf-8") as f:
        f.write(whatsapp_text)
    
    # --- Step 8: Auto-update daily editorial memory on disk ---
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

        # Extract main headline title from Section 1
        title_match = re.search(r'##\s*(.*?)(?:\n|\Z)', editorial_markdown)
        main_title = title_match.group(1).strip() if title_match else "Daily Cars Never Die Edition"

        # Extract Spotlight car name from Section 2
        spotlight_match = re.search(r'#####\s*Vehicle Spotlight\s*\n+##\s*(.*?)(?:\n|\Z)', editorial_markdown, re.IGNORECASE)
        if not spotlight_match:
            spotlight_match = re.search(r'##\s*Vehicle Spotlight[^\n]*\n+.*?\[(.*?)\]', editorial_markdown, re.IGNORECASE | re.DOTALL)
        
        spotlight_car = spotlight_match.group(1).strip() if spotlight_match else "Spotlight Car"

        # Extract top movers list from Markdown table
        top_movers = re.findall(r'\|.*?\[(.*?)\]\(.*?\).*?\|', editorial_markdown)
        clean_movers = [m.strip() for m in top_movers if m.strip() and not m.startswith("Vehicle") and not m.startswith("Rank")]

        # Extract real sub-heading themes (filter out generic section titles)
        all_subheadings = re.findall(r'###\s*(.+)', editorial_markdown)
        generic_titles = {"vehicle spotlight", "the leaderboard", "the leader board", "data corner", "top movers", "what's coming up this week", "what to watch"}
        clean_themes = [t.strip() for t in all_subheadings if t.strip().lower() not in generic_titles]
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        entry = {
            "date": today_str,
            "title": main_title,
            "spotlight_car": spotlight_car,
            "top_movers": clean_movers[:10],
            "themes": clean_themes[:5] if clean_themes else [main_title]
        }
        
        updated = False
        for i, h in enumerate(history):
            if h.get("date") == today_str:
                history[i]["title"] = main_title
                if spotlight_car != "Spotlight Car":
                    history[i]["spotlight_car"] = spotlight_car
                if clean_movers:
                    history[i]["top_movers"] = clean_movers[:10]
                if clean_themes:
                    history[i]["themes"] = clean_themes[:5]
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
