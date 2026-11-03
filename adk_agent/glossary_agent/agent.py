"""第3回 発展(a): Google ADK 版の学習支援エージェント。"""

from google.adk.agents import Agent

from app import tools
from app.agent import INSTRUCTIONS


root_agent = Agent(
    model="gemini-3.5-flash-lite",
    name="glossary_agent",
    instruction=INSTRUCTIONS,
    tools=[tools.search_glossary, tools.get_lecture_summary],
)
