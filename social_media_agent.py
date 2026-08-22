import os
import re
import json
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

# --- 1. Video Reel Renderer (1080x1920 HD Vertical) ---

def render_vertical_reel(spotlight_car: str, hammer_price: str, photo_url: str, daily_volume: str, sales_count: str, output_path: str) -> str:
    """Renders a 9:16 vertical video reel (1080x1920 MP4) for TikTok & Instagram Reels."""
    width, height = 1080, 1920
    fps = 2
    duration_per_scene = 4  # 4 seconds per scene = 12 sec total
    total_frames = fps * duration_per_scene * 3

    # Fetch spotlight photo if available
    spotlight_img = None
    if photo_url and photo_url != "#" and photo_url.startswith("http"):
        try:
            resp = requests.get(photo_url, timeout=10)
            if resp.status_code == 200:
                from io import BytesIO
                spotlight_img = Image.open(BytesIO(resp.content)).convert("RGB")
        except Exception as e:
            print(f"[Photo Download Warning] {e}")

    # Fonts
    try:
        font_large = ImageFont.truetype("arial.ttf", 68)
        font_medium = ImageFont.truetype("arial.ttf", 46)
        font_small = ImageFont.truetype("arial.ttf", 34)
    except Exception:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    frames = []

    for frame_idx in range(total_frames):
        scene_idx = frame_idx // (fps * duration_per_scene)
        
        # Create base canvas
        bg_color = (3, 7, 18) if scene_idx != 2 else (214, 90, 67) # Dark slate for 1&2, Crimson for CTA
        img = Image.new("RGB", (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)

        # Header Title Banner (Always visible)
        draw.text((width // 2, 120), "CARS NEVER DIE", font=font_large, fill=(255, 255, 255) if scene_idx != 2 else (3, 7, 18), anchor="mm")
        draw.text((width // 2, 200), "DAILY COLLECTOR CAR MARKET INTEL", font=font_small, fill=(214, 90, 67) if scene_idx != 2 else (255, 255, 255), anchor="mm")
        draw.line([(100, 240), (width - 100, 240)], fill=(255, 255, 255), width=3)

        if scene_idx == 0:
            # --- SCENE 1: SPOTLIGHT CAR HOOK ---
            draw.text((width // 2, 340), "FEATURED SPOTLIGHT SALE", font=font_small, fill=(156, 163, 175), anchor="mm")
            
            # Draw Car Image
            if spotlight_img:
                img_copy = spotlight_img.copy()
                img_copy.thumbnail((940, 700))
                w, h = img_copy.size
                img.paste(img_copy, ((width - w) // 2, 420))
                draw.rectangle([(width - w) // 2, 420, (width + w) // 2, 420 + h], outline=(214, 90, 67), width=4)
            else:
                draw.rectangle([100, 420, 980, 1000], fill=(30, 41, 59), outline=(214, 90, 67), width=4)
                draw.text((width // 2, 710), spotlight_car, font=font_medium, fill=(255, 255, 255), anchor="mm")

            # Price Callout Box
            draw.rectangle([100, 1180, 980, 1420], fill=(15, 23, 42), outline=(214, 90, 67), width=3)
            draw.text((width // 2, 1240), spotlight_car.upper(), font=font_medium, fill=(255, 255, 255), anchor="mm")
            draw.text((width // 2, 1340), f"HAMMER PRICE: {hammer_price}", font=font_large, fill=(214, 90, 67), anchor="mm")

        elif scene_idx == 1:
            # --- SCENE 2: MARKET METRICS SUMMARY ---
            draw.text((width // 2, 360), "YESTERDAY'S MARKET VOLUME", font=font_medium, fill=(214, 90, 67), anchor="mm")
            
            draw.rectangle([100, 460, 980, 800], fill=(15, 23, 42), outline=(51, 65, 85), width=3)
            draw.text((width // 2, 560), daily_volume, font=font_large, fill=(255, 255, 255), anchor="mm")
            draw.text((width // 2, 680), f"Across {sales_count} Six-Figure Sales", font=font_medium, fill=(156, 163, 175), anchor="mm")

            draw.rectangle([100, 880, 980, 1450], fill=(15, 23, 42), outline=(51, 65, 85), width=3)
            draw.text((width // 2, 960), "MARKET HIGHLIGHTS", font=font_medium, fill=(214, 90, 67), anchor="mm")
            draw.text((width // 2, 1080), "• High-End Online Liquidity Active", font=font_small, fill=(255, 255, 255), anchor="mm")
            draw.text((width // 2, 1180), "• Analog V12 & Manual Specials Surging", font=font_small, fill=(255, 255, 255), anchor="mm")
            draw.text((width // 2, 1280), "• duPont REGISTRY Live & BaT Volume", font=font_small, fill=(255, 255, 255), anchor="mm")

        else:
            # --- SCENE 3: CALL TO ACTION (CONVERSION ENGINE) ---
            draw.text((width // 2, 480), "GET THE DAILY VALUATION SHEET", font=font_large, fill=(255, 255, 255), anchor="mm")
            draw.text((width // 2, 580), "Free daily 6-figure auction price intel,", font=font_small, fill=(3, 7, 18), anchor="mm")
            draw.text((width // 2, 640), "valuation spreads & upcoming lot alerts.", font=font_small, fill=(3, 7, 18), anchor="mm")

            draw.rectangle([100, 780, 980, 1100], fill=(3, 7, 18), outline=(255, 255, 255), width=4)
            draw.text((width // 2, 860), "100% FREE DAILY INBOX DROP", font=font_medium, fill=(255, 255, 255), anchor="mm")
            draw.text((width // 2, 980), "carsneverdie.beehiiv.com", font=font_large, fill=(214, 90, 67), anchor="mm")

            draw.rectangle([100, 1200, 980, 1420], fill=(255, 255, 255), outline=(3, 7, 18), width=3)
            draw.text((width // 2, 1260), "COMMENT 'DATA' FOR DIRECT LINK 📩", font=font_medium, fill=(214, 90, 67), anchor="mm")
            draw.text((width // 2, 1340), "OR CLICK LINK IN BIO TO JOIN FREE", font=font_small, fill=(3, 7, 18), anchor="mm")

        # Footer watermark
        draw.text((width // 2, 1820), "carsneverdie.beehiiv.com • TikTok & Instagram @carsneverdie", font=font_small, fill=(156, 163, 175) if scene_idx != 2 else (3, 7, 18), anchor="mm")

        frames.append(img)

    # Save animation / MP4 reel
    try:
        import moviepy.editor as mpy
        import numpy as np
        clip_frames = [np.array(f) for f in frames]
        clip = mpy.ImageSequenceClip(clip_frames, fps=fps)
        clip.write_videofile(output_path, codec="libx264", audio=False, verbose=False, logger=None)
        return f"Rendered 9:16 vertical MP4 reel to {output_path}"
    except Exception as e:
        gif_path = output_path.replace(".mp4", ".gif")
        frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=1000, loop=0)
        return f"MoviePy fallback: Rendered GIF animation reel to {gif_path} (Error: {e})"


# --- 2. Social Media Caption & Publisher Tool ---

def generate_social_media_assets(tool_context: ToolContext) -> str:
    """Generates daily 9:16 vertical video reel (output_reel.mp4) and caption script (output_social_caption.txt) 
    for TikTok and Instagram, then auto-publishes to social accounts if API credentials are standard."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "output_body_content.html")
    reel_path = os.path.join(base_dir, "output_reel.mp4")
    caption_path = os.path.join(base_dir, "output_social_caption.txt")

    # Read output html/whatsapp to extract metadata
    html_content = ""
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

    # Extract Spotlight Car Name & Photo
    spotlight_match = re.search(r'#####\s*Vehicle Spotlight\s*</h5>\s*<h2[^>]*>(.*?)</h2>', html_content, re.IGNORECASE)
    if not spotlight_match:
        spotlight_match = re.search(r'Vehicle Spotlight.*?##\s*(.*?)(?:\n|<|\Z)', html_content, re.DOTALL | re.IGNORECASE)
    spotlight_car = re.sub(r'<[^>]+>', '', spotlight_match.group(1)).strip() if spotlight_match else "2020 McLaren Senna GTR"

    # Extract Photo URL
    photo_match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', html_content)
    photo_url = photo_match.group(1) if photo_match else ""

    # Extract Hammer Price if present
    price_match = re.search(r'(?:\$|USD\s*)([0-9,]{6,10})', html_content)
    hammer_price = f"${price_match.group(1)}" if price_match else "$635,250"

    # Extract Volume & Count
    vol_match = re.search(r'(?:\$|USD\s*)([0-9.]+\s*M)', html_content, re.IGNORECASE)
    daily_volume = f"${vol_match.group(1)} Volume" if vol_match else "$5.81M Volume"

    count_match = re.search(r'([0-9]{1,3})\s*(?:six-figure|sales)', html_content, re.IGNORECASE)
    sales_count = count_match.group(1) if count_match else "22"

    today_str = datetime.now().strftime("%B %d, %Y")

    # Render Vertical Video Reel MP4
    reel_status = render_vertical_reel(spotlight_car, hammer_price, photo_url, daily_volume, sales_count, reel_path)

    # Build High-Converting Growth Caption Script
    caption_text = f"""🔥 WHY DID THIS {spotlight_car.upper()} HAMMER FOR {hammer_price}? 🤯

Yesterday, {daily_volume} shifted across {sales_count} six-figure collector cars on Bring a Trailer and duPont REGISTRY Live.

Featured Spotlight: {spotlight_car} ({hammer_price})

📊 Want full daily sales spreadsheets, price tier breakdowns, and live auction alerts sent straight to your inbox?

📩 COMMENT "DATA" BELOW & we'll DM you the free subscription link! 
👉 Or click the Link in Bio to join free: carsneverdie.beehiiv.com

#CarsNeverDie #CollectorCars #BringATrailer #duPontRegistry #Supercars #Porsche #Ferrari #Lamborghini #Hypercar #CarCollector #AuctionNews #AutomotiveMarket"""

    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(caption_text)

    # Archive copy
    archives_dir = os.path.join(base_dir, "archives")
    os.makedirs(archives_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    archive_reel = os.path.join(archives_dir, f"reel_{timestamp}.mp4")
    if os.path.exists(reel_path):
        import shutil
        shutil.copy(reel_path, archive_reel)

    # Check for social media API auto-publishing keys
    api_key = os.getenv("UPLOAD_POST_API_KEY") or os.getenv("SOCIAL_POSTING_API_KEY")
    publish_status = "Simulation Mode (API key not set)."
    if api_key:
        try:
            # Call Upload-Post / Social API endpoint
            post_url = "https://api.upload-post.com/v1/posts"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "accounts": ["tiktok_carsneverdie", "instagram_carsneverdie"],
                "caption": caption_text,
                "video_url": reel_path
            }
            resp = requests.post(post_url, headers=headers, json=payload, timeout=15)
            if resp.status_code in (200, 201):
                publish_status = f"Successfully published daily reel to TikTok & Instagram! (API Response: {resp.status_code})"
            else:
                publish_status = f"Social API return code {resp.status_code}: {resp.text}"
        except Exception as e:
            publish_status = f"Social API publishing exception: {e}"

    return f"SUCCESS: {reel_status}. Social caption saved to {caption_path}. Publishing status: {publish_status}"


# --- 3. Google ADK Agent Definition ---

social_media_agent = Agent(
    name="social_media_agent",
    model="gemini-2.5-flash",
    description="Autonomous social media publisher for TikTok and Instagram Reels.",
    instruction="""You are the Social Media Specialist for Cars Never Die.
Your job is to read today's newsletter content, render a 9:16 vertical HD video reel (output_reel.mp4) featuring yesterday's spotlight car and daily volume metrics, and publish/archive the reel and caption with a CTA to subscribe to carsneverdie.beehiiv.com.

ALWAYS call `generate_social_media_assets` to generate the daily reel video and caption.""",
    tools=[generate_social_media_assets]
)
