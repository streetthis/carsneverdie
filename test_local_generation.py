import os
import asyncio
from dotenv import load_dotenv
from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()
if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

from data_analyst_agent import data_analyst
from editorial_agent import editorial_agent
from publisher_designer_agent import publisher_agent
from social_media_agent import social_media_agent

# Local pipeline: Data Analyst -> Editorial Agent -> Publisher Designer -> Social Media Agent
local_pipeline = SequentialAgent(
    name="local_newsletter_pipeline",
    sub_agents=[data_analyst, editorial_agent, publisher_agent, social_media_agent]
)

import json

def load_memory_context():
    memory_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editorial_memory.json")
    if not os.path.exists(memory_path):
        return ""
    try:
        with open(memory_path, "r", encoding="utf-8") as f:
            history = json.load(f)
            recent = history[-7:]
            if not recent:
                return ""
            spotlights = [h.get("spotlight_car") for h in recent if h.get("spotlight_car") and h.get("spotlight_car") != "Spotlight Car"]
            titles = [h.get("title") for h in recent if h.get("title")]
            themes = []
            for h in recent:
                themes.extend(h.get("themes", []))
            return f"\n\n[EDITORIAL MEMORY - PAST 7 DAYS COVERAGE]\n- DO NOT REPEAT RECENT SPOTLIGHT CARS: {list(set(spotlights))}\n- DO NOT REPEAT RECENT HEADLINES: {list(set(titles))}\n- RECENTLY COVERED THEMES (ROTATE AWAY): {list(set(themes))}\nChoose a fresh brand, spotlight vehicle, dynamic daily headline hook, and unique narrative angle today."
    except Exception as e:
        print(f"[Memory Load Warning] {e}")
        return ""

async def main():
    session_service = InMemorySessionService()
    runner = Runner(
        agent=local_pipeline,
        session_service=session_service,
        app_name="local_editorial_app"
    )
    
    session = await session_service.create_session(
        app_name="local_editorial_app",
        user_id="drew_user"
    )
    
    from datetime import datetime, timedelta
    today_date_str = datetime.now().strftime('%B %d, %Y')
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    memory_context = load_memory_context()
    print(f"Running local generation for date: {yesterday_str} (Publication date: {today_date_str})...")

    prompt_text = f"Today's publication date is {today_date_str}. Run the daily sync analyzing yesterday's completed sales ({yesterday_str}) and generate today's newsletter issue.{memory_context}"

    user_msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt_text)]
    )
    
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    async for event in runner.run_async(
        session_id=session.id,
        user_id="drew_user",
        new_message=user_msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    print(part.text, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
