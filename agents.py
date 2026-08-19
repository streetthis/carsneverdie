import os
import requests
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents import SequentialAgent
from google.adk.tools.tool_context import ToolContext

# Load your local .env file containing your AUCTION_API_KEY
load_dotenv()

from data_analyst_agent import data_analyst
from editorial_agent import editorial_agent
from publisher_designer_agent import publisher_agent
from beehiiv_publisher_agent import beehiiv_publisher_agent

# --- 3. Orchestrate the Workflow ---

# Sequential Pipeline: Analyst -> Editor -> Publisher Designer -> beehiiv Publisher
newsletter_team = SequentialAgent(
    name="newsletter_pipeline",
    sub_agents=[data_analyst, editorial_agent, publisher_agent, beehiiv_publisher_agent]
)

import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

async def main():
    session_service = InMemorySessionService()
    runner = Runner(
        agent=newsletter_team,
        session_service=session_service,
        app_name="editorial_app"
    )
    
    session = await session_service.create_session(
        app_name="editorial_app",
        user_id="drew_user"
    )
    
    from datetime import datetime, timedelta
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Running daily automated pipeline for date: {yesterday_str}...")

    user_msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=f"Run the daily sync for {yesterday_str} and publish today's newsletter issue.")]
    )
    
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("Starting newsletter generation pipeline...\n")
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